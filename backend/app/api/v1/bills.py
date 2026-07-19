import json
import logging
import uuid
from collections.abc import AsyncIterator
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import JSONResponse, StreamingResponse

from app.agents.graph import (
    clear_transaction_session,
    get_compiled_graph,
    prepare_transaction_config,
)
from app.agents.guardian import guardian_node
from app.agents.state import new_transaction_state
from app.api.deps import CurrentUser, DBSession, RedisClient
from app.api.rate_limit import require_rate_limits
from app.api.v1.sse import publish_user_event
from app.models import LedgerRole, LedgerType
from app.config import get_settings
from app.core.rate_limit import RateLimitRule
from app.schemas.bill import (
    BillConfirmRequest,
    BillListParams,
    BillListResponse,
    BillOut,
    BillUpdate,
    TranscribeRequest,
)
from app.services.bill_service import (
    can_manage_bill,
    create_bill_from_parsed,
    delete_bill,
    get_accessible_ledger,
    get_bill_by_confirmation_session,
    get_bill_with_access,
    get_bills_paginated,
    lock_user_for_billing,
    update_bill,
)
from app.services.ledger_service import get_ledger_member_ids

router = APIRouter()
logger = logging.getLogger(__name__)
settings = get_settings()


def _sse_message(event: str, data: dict[str, Any]) -> str:
    payload = json.dumps(data, ensure_ascii=False, default=str)
    return f"event: {event}\ndata: {payload}\n\n"


async def _require_ledger(db: DBSession, ledger_id: int, user_id: int):
    try:
        return await get_accessible_ledger(db, ledger_id, user_id)
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="账本不存在或无权访问",
        ) from exc


@router.post("/transcribe")
async def transcribe_bill(
    request: TranscribeRequest,
    user: CurrentUser,
    db: DBSession,
    redis: RedisClient,
) -> StreamingResponse:
    await require_rate_limits(
        redis,
        f"user:{user.id}:ai-transcribe",
        RateLimitRule("minute", settings.AI_TRANSCRIBE_LIMIT_PER_MINUTE, 60),
        RateLimitRule("day", settings.AI_TRANSCRIBE_LIMIT_PER_DAY, 86400),
    )
    ledger, _ = await _require_ledger(db, request.ledger_id, user.id)
    try:
        graph = get_compiled_graph()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI 记账服务尚未完成依赖配置",
        ) from exc

    session_id = request.session_id or uuid.uuid4().hex[:12]
    config = prepare_transaction_config(
        graph,
        user.id,
        request.ledger_id,
        session_id,
    )
    checkpoint = graph.get_state(config)
    existing_state = dict(checkpoint.values) if checkpoint.values else None
    state = existing_state or new_transaction_state(
        raw_input=request.text,
        user_id=user.id,
        ledger_id=request.ledger_id,
        session_id=session_id,
    )
    state.update(
        {
            "raw_input": request.text,
            "user_id": user.id,
            "ledger_id": request.ledger_id,
            "session_id": session_id,
            "is_shared_ledger": ledger.type == LedgerType.SHARED,
            "error": None,
        }
    )

    async def event_stream() -> AsyncIterator[str]:
        parsed_ready = False
        async for event in graph.astream(state, config):
            for node_name, node_state in event.items():
                if node_name != "parser":
                    continue
                if node_state.get("parsed"):
                    parsed_ready = not node_state.get("missing_fields")
                    yield _sse_message(
                        "parsed",
                        {
                            "parsed": node_state["parsed"],
                            "session_id": session_id,
                        },
                    )
                if node_state.get("clarification_question"):
                    yield _sse_message(
                        "clarify",
                        {
                            "question": node_state["clarification_question"],
                            "session_id": session_id,
                            "round": node_state.get("clarification_round", 1),
                        },
                    )
                    return
                if node_state.get("error"):
                    yield _sse_message(
                        "error",
                        {"message": node_state["error"]},
                    )
                    await clear_transaction_session(user.id, request.ledger_id, session_id)
                    return

        if parsed_ready:
            yield _sse_message(
                "awaiting_confirmation",
                {"session_id": session_id},
            )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/confirm", response_model=BillOut)
async def confirm_bill(
    request: BillConfirmRequest,
    user: CurrentUser,
    db: DBSession,
    redis: RedisClient,
) -> BillOut | JSONResponse:
    ledger, _ = await _require_ledger(db, request.ledger_id, user.id)
    await lock_user_for_billing(db, user.id)
    existing = await get_bill_by_confirmation_session(
        db,
        user.id,
        request.ledger_id,
        request.session_id,
    )
    if existing is not None:
        await clear_transaction_session(user.id, request.ledger_id, request.session_id)
        return BillOut.model_validate(existing)
    parsed = request.parsed.model_dump(mode="json")
    if request.share_user_ids:
        if ledger.type != LedgerType.SHARED:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "只有共享账本可以使用 AA 分摊",
            )
        if request.parsed.type != "expense":
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "收入记录不能使用 AA 分摊",
            )
        member_ids = await get_ledger_member_ids(db, request.ledger_id)
        invalid_ids = set(request.share_user_ids) - member_ids
        if invalid_ids:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "AA 参与人中包含非账本成员",
            )
    state = new_transaction_state(
        raw_input=request.raw_input,
        user_id=user.id,
        ledger_id=request.ledger_id,
        session_id=request.session_id,
    )
    state.update(
        {
            "parsed": parsed,
            "missing_fields": [],
            "is_shared_ledger": ledger.type == LedgerType.SHARED,
        }
    )
    state = await guardian_node(state, db=db)
    risk_level = state.get("risk_level", "safe")
    budget_check = state.get("budget_check")

    if risk_level in {"warning", "blocked"} and not request.force:
        event_data = budget_check or {"risk_level": risk_level}
        try:
            await publish_user_event(redis, user.id, risk_level, event_data)
        except Exception:
            logger.warning("预算提醒推送失败", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "status": risk_level,
                "budget_check": event_data,
                "message": "请确认是否仍然记账",
            },
        )

    bill = await create_bill_from_parsed(
        db,
        redis,
        user.id,
        request.ledger_id,
        parsed,
        request.raw_input,
        confirmation_session_id=request.session_id,
        share_user_ids=request.share_user_ids,
    )
    await db.commit()
    await clear_transaction_session(user.id, request.ledger_id, request.session_id)

    loaded = await get_bill_with_access(db, bill.id, user.id)
    if loaded is None:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "账单保存后读取失败")
    bill_out = BillOut.model_validate(loaded[0])
    try:
        await publish_user_event(
            redis,
            user.id,
            "completed",
            {"bill": bill_out.model_dump(mode="json")},
        )
    except Exception:
        logger.warning("账单已保存，但实时通知推送失败", exc_info=True)
    return bill_out


@router.get("", response_model=BillListResponse)
async def list_bills(
    params: Annotated[BillListParams, Depends()],
    user: CurrentUser,
    db: DBSession,
) -> BillListResponse:
    await _require_ledger(db, params.ledger_id, user.id)
    bills, total = await get_bills_paginated(
        db,
        params.ledger_id,
        page=params.page,
        page_size=params.page_size,
        year=params.year,
        month=params.month,
        category=params.category,
    )
    return BillListResponse(
        items=[BillOut.model_validate(bill) for bill in bills],
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


@router.get("/{bill_id}", response_model=BillOut)
async def get_bill(bill_id: int, user: CurrentUser, db: DBSession) -> BillOut:
    loaded = await get_bill_with_access(db, bill_id, user.id)
    if loaded is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "账单不存在或无权访问")
    return BillOut.model_validate(loaded[0])


@router.put("/{bill_id}", response_model=BillOut)
async def edit_bill(
    bill_id: int,
    payload: BillUpdate,
    user: CurrentUser,
    db: DBSession,
    redis: RedisClient,
) -> BillOut:
    loaded = await get_bill_with_access(db, bill_id, user.id, for_update=True)
    if loaded is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "账单不存在或无权访问")
    bill, member = loaded
    if not can_manage_bill(bill, member, user.id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "只有创建者或管理员可以修改")

    try:
        await update_bill(db, redis, bill, payload)
    except ValueError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    await db.commit()
    refreshed = await get_bill_with_access(db, bill_id, user.id)
    if refreshed is None:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "账单更新后读取失败")
    return BillOut.model_validate(refreshed[0])


@router.delete("/{bill_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_bill(
    bill_id: int,
    user: CurrentUser,
    db: DBSession,
    redis: RedisClient,
) -> Response:
    loaded = await get_bill_with_access(db, bill_id, user.id, for_update=True)
    if loaded is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "账单不存在或无权访问")
    bill, member = loaded
    if not can_manage_bill(bill, member, user.id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "只有创建者或管理员可以删除")

    await delete_bill(db, redis, bill)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

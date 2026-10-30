import json
import logging
import uuid
from collections.abc import AsyncIterator
from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.exc import SQLAlchemyError

from app.agents.graph import (
    clear_transaction_session,
    get_compiled_graph,
    prepare_transaction_config,
)
from app.agents.guardian import guardian_budget_node, stricter_risk
from app.agents.orchestrator import looks_like_advice_request
from app.agents.state import new_transaction_state, parsed_items_from_state
from app.api.deps import CurrentUser, DBSession, RedisClient, require_ledger_access
from app.api.rate_limit import require_rate_limits
from app.api.v1.sse import publish_user_event
from app.models import LedgerRole, LedgerType
from app.config import get_settings
from app.core.redis import ledger_write_lock
from app.core.rate_limit import RateLimitRule
from app.schemas.bill import (
    BillConfirmRequest,
    BillCreateRequest,
    BillImportRequest,
    BillImportResponse,
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
    get_bill_by_confirmation_session,
    get_bill_with_access,
    get_bills_paginated,
    lock_user_for_billing,
    update_bill,
)
from app.services.bill_import_service import prepare_bill_import, update_import_budget_cache
from app.services.ledger_service import get_ledger_member_ids
from app.services.category_service import list_categories
from app.services.stats_service import get_category_stats, get_overview

router = APIRouter()
logger = logging.getLogger(__name__)
settings = get_settings()


def _sse_message(event: str, data: dict[str, Any]) -> str:
    payload = json.dumps(data, ensure_ascii=False, default=str)
    return f"event: {event}\ndata: {payload}\n\n"


@router.post("/transcribe")
async def transcribe_bill(
    request: TranscribeRequest,
    user: CurrentUser,
    db: DBSession,
    redis: RedisClient,
) -> StreamingResponse:
    if not settings.AI_FEATURES_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI 记账功能暂不可用",
        )
    await require_rate_limits(
        redis,
        f"user:{user.id}:ai-transcribe",
        RateLimitRule("minute", settings.AI_TRANSCRIBE_LIMIT_PER_MINUTE, 60),
        RateLimitRule("day", settings.AI_TRANSCRIBE_LIMIT_PER_DAY, 86400),
    )
    ledger, _ = await require_ledger_access(db, request.ledger_id, user.id)
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
    try:
        categories = await list_categories(db, user.id, request.ledger_id)
    except SQLAlchemyError:
        logger.warning("自定义分类加载失败，AI 解析将使用默认分类", exc_info=True)
        categories = []
    state["available_categories"] = [
        {
            "type": category.type.value,
            "category": category.parent_name or category.name,
            "subcategory": category.name if category.parent_name else "",
        }
        for category in categories
    ]
    if looks_like_advice_request(request.text):
        try:
            today = date.today()
            overview = await get_overview(
                db,
                user_id=user.id,
                ledger_id=request.ledger_id,
                year=today.year,
                month=today.month,
            )
            category_rows, _ = await get_category_stats(
                db,
                ledger_id=request.ledger_id,
                year=today.year,
                month=today.month,
            )
            state["context_memory"] = {
                "financial_snapshot": {
                    "period": f"{today.year:04d}-{today.month:02d}",
                    "income": overview.income,
                    "expense": overview.expense,
                    "balance": overview.balance,
                    "budget_used_percentage": overview.budget_used_percentage,
                    "top_categories": [item.model_dump() for item in category_rows[:5]],
                }
            }
        except Exception:
            logger.warning("咨询统计快照加载失败，Advisor 将使用无数据降级建议", exc_info=True)
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
        transaction_advice: dict[str, Any] | None = None
        latest_items: list[dict[str, Any]] = []
        latest_checks: list[dict[str, Any]] = []
        async for event in graph.astream(state, config):
            for node_name, node_state in event.items():
                if node_name == "advisor":
                    recommendation = node_state.get("advisor_recommendation") or {}
                    advice_payload = {
                        "summary": recommendation.get("summary", "暂时无法生成分析建议"),
                        "actions": recommendation.get("actions", []),
                        "session_id": session_id,
                    }
                    if node_state.get("intent") == "advice":
                        yield _sse_message("advice", advice_payload)
                        await clear_transaction_session(user.id, request.ledger_id, session_id)
                        return
                    transaction_advice = advice_payload
                if node_name == "guardian":
                    latest_checks = list(node_state.get("budget_checks") or [])
                    continue
                if node_name != "parser":
                    continue
                if node_state.get("parsed"):
                    items = parsed_items_from_state(node_state)
                    latest_items = items
                    parsed_ready = not node_state.get("missing_fields")
                    yield _sse_message(
                        "parsed",
                        {
                            "parsed": node_state["parsed"],
                            "items": items,
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
                {
                    "session_id": session_id,
                    "items": latest_items,
                    "budget_checks": latest_checks,
                    "advice": transaction_advice,
                },
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


@router.post("", response_model=BillOut)
async def create_bill(
    request: BillCreateRequest,
    user: CurrentUser,
    db: DBSession,
    redis: RedisClient,
) -> BillOut:
    await require_ledger_access(db, request.ledger_id, user.id)
    await lock_user_for_billing(db, user.id)
    async with ledger_write_lock(redis, request.ledger_id):
        if request.import_key:
            existing = await get_bill_by_confirmation_session(db, user.id, request.ledger_id, request.import_key)
            if existing is not None:
                return BillOut.model_validate(existing)
        parsed = {
            "type": request.type,
            "amount": request.amount,
            "category": request.category,
            "subcategory": request.subcategory,
            "account": request.account,
            "note": request.note,
            "bill_date": request.bill_date.isoformat(),
        }
        bill = await create_bill_from_parsed(
            db,
            redis,
            user.id,
            request.ledger_id,
            parsed,
            raw_input="",
            confirmation_session_id=request.import_key,
        )
        bill.ai_parsed = False
        await db.commit()
        loaded = await get_bill_with_access(db, bill.id, user.id)
        if loaded is None:
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "账单保存后读取失败")
        return BillOut.model_validate(loaded[0])


@router.post("/import", response_model=BillImportResponse)
async def import_bills(
    request: BillImportRequest,
    user: CurrentUser,
    db: DBSession,
    redis: RedisClient,
) -> BillImportResponse:
    await require_ledger_access(db, request.ledger_id, user.id)
    await lock_user_for_billing(db, user.id)
    async with ledger_write_lock(redis, request.ledger_id):
        try:
            items, budget_deltas = await prepare_bill_import(
                db, user_id=user.id, ledger_id=request.ledger_id, items=request.items
            )
        except ValueError as exc:
            raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
        # A failed batch never changes the cache or partially changes account balances.
        await db.commit()
        await update_import_budget_cache(
            redis, user_id=user.id, ledger_id=request.ledger_id, deltas=budget_deltas
        )
        return BillImportResponse(items=items)


@router.post("/confirm", response_model=BillOut)
async def confirm_bill(
    request: BillConfirmRequest,
    user: CurrentUser,
    db: DBSession,
    redis: RedisClient,
) -> BillOut | JSONResponse:
    ledger, _ = await require_ledger_access(db, request.ledger_id, user.id)
    await lock_user_for_billing(db, user.id)
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
    # AA 成员校验必须在账本锁内做：否则校验通过后成员可能被并发移除。
    # 一把锁覆盖幂等检查、AI/预算和创建；重试不需要额外加锁，
    # 也不会在拿到已创建账单前重复调用 AI。
    # 锁内包含 AI/guardian，重复确认可能等待更久；给它更长的有限重试预算，
    # 以便最终走到幂等检查并返回已创建账单，而不是过早 409。
    async with ledger_write_lock(
        redis, request.ledger_id, retry_attempts=30
    ):
        return await _confirm_bill_locked(
            request, user, db, redis, ledger, parsed
        )


async def _confirm_bill_locked(
    request: BillConfirmRequest,
    user: CurrentUser,
    db: DBSession,
    redis: RedisClient,
    ledger,
    parsed: dict,
) -> BillOut | JSONResponse:
    existing = await get_bill_by_confirmation_session(
        db,
        user.id,
        request.ledger_id,
        request.session_id,
    )
    if existing is not None:
        await clear_transaction_session(
            user.id, request.ledger_id, request.session_id
        )
        return BillOut.model_validate(existing)

    if request.share_user_ids:
        member_ids = await get_ledger_member_ids(db, request.ledger_id)
        invalid_ids = set(request.share_user_ids) - member_ids
        if invalid_ids:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "AA 参与人中包含非账本成员",
            )

    # 批量逐笔确认时，不能继承整批的 AI 风险，否则一笔超支会连坐其他笔。
    # 批量标记由客户端显式传入，不用 session_id 的冒号来猜。
    is_batch_item = request.is_batch_item
    state = new_transaction_state(
        raw_input=request.raw_input,
        user_id=user.id,
        ledger_id=request.ledger_id,
        session_id=request.session_id,
    )
    try:
        graph = get_compiled_graph()
        config = prepare_transaction_config(
            graph,
            user.id,
            request.ledger_id,
            request.session_id,
        )
        checkpoint = graph.get_state(config)
        checkpoint_state = dict(checkpoint.values) if checkpoint.values else {}
        if checkpoint_state.get("route_mode") in {"quick", "standard", "deep"}:
            state["route_mode"] = checkpoint_state["route_mode"]
        if (
            not is_batch_item
            and checkpoint_state.get("ai_risk_level") in {"safe", "warning", "blocked"}
        ):
            state["ai_risk_level"] = checkpoint_state["ai_risk_level"]
        state["guardian_opinion"] = checkpoint_state.get("guardian_opinion")
        state["route_reason"] = checkpoint_state.get("route_reason")
        state["agent_messages"] = list(checkpoint_state.get("agent_messages") or [])[-20:]
        state["context_memory"] = {
            key: str(value)[:120]
            for key, value in (checkpoint_state.get("context_memory") or {}).items()
            if key in {"last_category", "last_account"}
        }
    except Exception:
        logger.warning("未能恢复 Agent 会话上下文，继续使用标准确认流程", exc_info=True)
    state.update(
        {
            "parsed": parsed,
            "missing_fields": [],
            "is_shared_ledger": ledger.type == LedgerType.SHARED,
        }
    )
    state = await guardian_budget_node(state, db=db)
    rule_risk_level = state.get("risk_level", "safe")
    ai_risk_level = state.get("ai_risk_level", "safe")
    risk_level = stricter_risk(rule_risk_level, ai_risk_level)
    state["rule_risk_level"] = rule_risk_level
    state["risk_level"] = risk_level
    budget_check = state.get("budget_check")
    if budget_check is not None:
        budget_check.update(
            {
                "rule_risk_level": rule_risk_level,
                "ai_risk_level": ai_risk_level,
                "risk_level": risk_level,
            }
        )

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
    await require_ledger_access(db, params.ledger_id, user.id)
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

    async with ledger_write_lock(redis, bill.ledger_id):
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

    async with ledger_write_lock(redis, bill.ledger_id):
        await delete_bill(db, redis, bill)
        await db.commit()
        return Response(status_code=status.HTTP_204_NO_CONTENT)

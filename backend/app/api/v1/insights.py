from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentUser, DBSession, RedisClient
from app.api.rate_limit import require_rate_limits
from app.config import get_settings
from app.core.rate_limit import RateLimitRule
from app.models import ReportType
from app.schemas.insight import (
    InsightGenerateRequest,
    InsightGenerateResponse,
    InsightListResponse,
    InsightOut,
)
from app.services.bill_service import get_accessible_ledger
from app.services.insight_service import (
    InsightQueueFull,
    get_insight,
    list_insights,
    queue_insight_generation,
)

router = APIRouter()
settings = get_settings()


@router.post(
    "/generate",
    response_model=InsightGenerateResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def generate_insight(
    payload: InsightGenerateRequest,
    user: CurrentUser,
    db: DBSession,
    redis: RedisClient,
) -> InsightGenerateResponse:
    if not settings.AI_FEATURES_ENABLED:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "洞察功能暂不可用",
        )
    await require_rate_limits(
        redis,
        f"user:{user.id}:ai-insight",
        RateLimitRule("hour", settings.AI_INSIGHT_LIMIT_PER_HOUR, 3600),
        RateLimitRule("day", settings.AI_INSIGHT_LIMIT_PER_DAY, 86400),
    )
    try:
        await get_accessible_ledger(db, payload.ledger_id, user.id)
    except PermissionError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "账本不存在或无权访问") from exc
    report_type = ReportType(payload.report_type)
    try:
        await queue_insight_generation(
            redis,
            user_id=user.id,
            ledger_id=payload.ledger_id,
            report_type=report_type,
        )
    except InsightQueueFull as exc:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "洞察任务较多，请稍后再试",
            headers={"Retry-After": "60"},
        ) from exc
    return InsightGenerateResponse(
        ledger_id=payload.ledger_id,
        report_type=payload.report_type,
    )


@router.get("", response_model=InsightListResponse)
async def read_insights(
    user: CurrentUser,
    db: DBSession,
    ledger_id: int | None = Query(default=None, gt=0),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> InsightListResponse:
    if ledger_id is not None:
        try:
            await get_accessible_ledger(db, ledger_id, user.id)
        except PermissionError as exc:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                "账本不存在或无权访问",
            ) from exc
    items, total = await list_insights(
        db,
        user.id,
        ledger_id=ledger_id,
        page=page,
        page_size=page_size,
    )
    return InsightListResponse(
        items=[InsightOut.model_validate(item) for item in items],
        total=total,
    )


@router.get("/{insight_id}", response_model=InsightOut)
async def read_insight(
    insight_id: int,
    user: CurrentUser,
    db: DBSession,
) -> InsightOut:
    insight = await get_insight(db, insight_id, user.id)
    if insight is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "洞察报告不存在")
    return InsightOut.model_validate(insight)

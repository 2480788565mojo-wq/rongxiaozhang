from datetime import date

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentUser, DBSession
from app.schemas.stats import CategoryStatsResponse, StatsOverview, TrendResponse
from app.services.bill_service import get_accessible_ledger
from app.services.stats_service import get_category_stats, get_overview, get_trend

router = APIRouter()


async def _require_access(db: DBSession, ledger_id: int, user_id: int) -> None:
    try:
        await get_accessible_ledger(db, ledger_id, user_id)
    except PermissionError as exc:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "账本不存在或无权访问",
        ) from exc


@router.get("/overview", response_model=StatsOverview)
async def overview(
    user: CurrentUser,
    db: DBSession,
    ledger_id: int = Query(default=1, gt=0),
    year: int = Query(default_factory=lambda: date.today().year, ge=2000, le=2100),
    month: int = Query(default_factory=lambda: date.today().month, ge=1, le=12),
) -> StatsOverview:
    await _require_access(db, ledger_id, user.id)
    return await get_overview(
        db,
        user_id=user.id,
        ledger_id=ledger_id,
        year=year,
        month=month,
    )


@router.get("/trend", response_model=TrendResponse)
async def trend(
    user: CurrentUser,
    db: DBSession,
    ledger_id: int = Query(default=1, gt=0),
    months: int = Query(default=12, ge=1, le=24),
) -> TrendResponse:
    await _require_access(db, ledger_id, user.id)
    today = date.today()
    items = await get_trend(
        db,
        ledger_id=ledger_id,
        months=months,
        end_year=today.year,
        end_month=today.month,
    )
    return TrendResponse(ledger_id=ledger_id, items=items)


@router.get("/category", response_model=CategoryStatsResponse)
async def category_stats(
    user: CurrentUser,
    db: DBSession,
    ledger_id: int = Query(default=1, gt=0),
    year: int = Query(default_factory=lambda: date.today().year, ge=2000, le=2100),
    month: int = Query(default_factory=lambda: date.today().month, ge=1, le=12),
) -> CategoryStatsResponse:
    await _require_access(db, ledger_id, user.id)
    items, total = await get_category_stats(
        db,
        ledger_id=ledger_id,
        year=year,
        month=month,
    )
    return CategoryStatsResponse(
        ledger_id=ledger_id,
        year=year,
        month=month,
        total=total,
        items=items,
    )

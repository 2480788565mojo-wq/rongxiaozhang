from datetime import date

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentUser, DBSession, RedisClient
from app.schemas.budget import (
    BudgetOut,
    BudgetSet,
    BudgetStatusResponse,
)
from app.services.bill_service import get_accessible_ledger
from app.services.budget_service import get_budget, get_budget_statuses, set_budget

router = APIRouter()


async def _require_access(db: DBSession, ledger_id: int, user_id: int) -> None:
    try:
        await get_accessible_ledger(db, ledger_id, user_id)
    except PermissionError as exc:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "账本不存在或无权访问",
        ) from exc


@router.get("", response_model=BudgetOut | None)
async def read_budget(
    user: CurrentUser,
    db: DBSession,
    ledger_id: int = Query(default=1, gt=0),
    year: int = Query(default_factory=lambda: date.today().year, ge=2000, le=2100),
    month: int = Query(default_factory=lambda: date.today().month, ge=1, le=12),
) -> BudgetOut | None:
    await _require_access(db, ledger_id, user.id)
    budget = await get_budget(db, user.id, ledger_id, year, month)
    return BudgetOut.model_validate(budget) if budget is not None else None


@router.put("", response_model=BudgetOut)
async def save_budget(
    payload: BudgetSet,
    user: CurrentUser,
    db: DBSession,
    redis: RedisClient,
) -> BudgetOut:
    await _require_access(db, payload.ledger_id, user.id)
    budget = await set_budget(db, redis, user.id, payload)
    await db.commit()
    return BudgetOut.model_validate(budget)


@router.get("/status", response_model=BudgetStatusResponse)
async def read_budget_status(
    user: CurrentUser,
    db: DBSession,
    redis: RedisClient,
    ledger_id: int = Query(default=1, gt=0),
    year: int = Query(default_factory=lambda: date.today().year, ge=2000, le=2100),
    month: int = Query(default_factory=lambda: date.today().month, ge=1, le=12),
) -> BudgetStatusResponse:
    await _require_access(db, ledger_id, user.id)
    statuses = await get_budget_statuses(
        db,
        redis,
        user.id,
        ledger_id,
        year,
        month,
    )
    return BudgetStatusResponse(
        ledger_id=ledger_id,
        year=year,
        month=month,
        statuses=statuses,
    )

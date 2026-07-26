from datetime import date

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DBSession, RedisClient, require_ledger_access
from app.schemas.budget import (
    BudgetOut,
    BudgetSet,
    BudgetStatusResponse,
)
from app.services.budget_service import get_budget, get_budget_statuses, set_budget

router = APIRouter()


@router.get("", response_model=BudgetOut | None)
async def read_budget(
    user: CurrentUser,
    db: DBSession,
    ledger_id: int = Query(default=1, gt=0),
    year: int = Query(default_factory=lambda: date.today().year, ge=2000, le=2100),
    month: int = Query(default_factory=lambda: date.today().month, ge=1, le=12),
) -> BudgetOut | None:
    await require_ledger_access(db, ledger_id, user.id)
    budget = await get_budget(db, user.id, ledger_id, year, month)
    return BudgetOut.model_validate(budget) if budget is not None else None


@router.put("", response_model=BudgetOut)
async def save_budget(
    payload: BudgetSet,
    user: CurrentUser,
    db: DBSession,
    redis: RedisClient,
) -> BudgetOut:
    await require_ledger_access(db, payload.ledger_id, user.id)
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
    await require_ledger_access(db, ledger_id, user.id)
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

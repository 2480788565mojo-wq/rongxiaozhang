from datetime import date
from decimal import Decimal, ROUND_DOWN
import logging

from redis.asyncio import Redis
from sqlalchemy import extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.redis import incr_budget_spent
from app.models import Bill, BillShare, BillType, Ledger, LedgerMember, LedgerRole, User
from app.schemas.bill import BillUpdate
from app.services.account_service import adjust_account_balance


logger = logging.getLogger(__name__)


async def _update_budget_cache(redis: Redis, *args) -> None:
    try:
        await incr_budget_spent(redis, *args)
    except Exception:
        logger.warning("预算缓存更新失败，数据库账单仍为准账", exc_info=True)


async def get_accessible_ledger(
    db: AsyncSession,
    ledger_id: int,
    user_id: int,
) -> tuple[Ledger, LedgerMember]:
    result = await db.execute(
        select(Ledger, LedgerMember)
        .join(LedgerMember, LedgerMember.ledger_id == Ledger.id)
        .where(
            Ledger.id == ledger_id,
            LedgerMember.user_id == user_id,
        )
    )
    row = result.one_or_none()
    if row is None:
        raise PermissionError("无权访问该账本")
    return row[0], row[1]


async def create_bill_from_parsed(
    db: AsyncSession,
    redis: Redis,
    user_id: int,
    ledger_id: int,
    parsed: dict,
    raw_input: str,
    confirmation_session_id: str | None = None,
    share_user_ids: list[int] | None = None,
) -> Bill:
    bill_date = parsed.get("bill_date")
    if isinstance(bill_date, str):
        bill_date = date.fromisoformat(bill_date)
    if bill_date is None:
        bill_date = date.today()

    bill = Bill(
        ledger_id=ledger_id,
        creator_id=user_id,
        type=BillType(parsed["type"]),
        amount=Decimal(str(parsed["amount"])),
        category=parsed["category"],
        subcategory=parsed.get("subcategory"),
        account=parsed.get("account"),
        note=parsed.get("note"),
        bill_date=bill_date,
        raw_input=raw_input,
        ai_parsed=True,
        confirmation_session_id=confirmation_session_id,
    )
    db.add(bill)
    await db.flush()

    if share_user_ids:
        _add_equal_shares(db, bill, share_user_ids)
        await db.flush()

    await adjust_account_balance(
        db,
        user_id=user_id,
        ledger_id=ledger_id,
        account_name=bill.account,
        bill_type=bill.type,
        amount=bill.amount,
    )

    if bill.type == BillType.EXPENSE:
        await _update_budget_cache(
            redis,
            user_id,
            ledger_id,
            bill.bill_date.year,
            bill.bill_date.month,
            bill.category,
            float(bill.amount),
        )
    return bill


async def lock_user_for_billing(db: AsyncSession, user_id: int) -> None:
    await db.execute(select(User.id).where(User.id == user_id).with_for_update())


async def get_bill_by_confirmation_session(
    db: AsyncSession,
    user_id: int,
    ledger_id: int,
    session_id: str,
) -> Bill | None:
    result = await db.execute(
        select(Bill)
        .options(selectinload(Bill.shares))
        .where(
            Bill.creator_id == user_id,
            Bill.ledger_id == ledger_id,
            Bill.confirmation_session_id == session_id,
        )
    )
    return result.scalar_one_or_none()


def _equal_share_amounts(amount: Decimal, count: int) -> list[Decimal]:
    cent = Decimal("0.01")
    base = (amount / count).quantize(cent, rounding=ROUND_DOWN)
    amounts = [base for _ in range(count)]
    amounts[-1] = amount - base * (count - 1)
    return amounts


def _add_equal_shares(
    db: AsyncSession,
    bill: Bill,
    user_ids: list[int],
) -> None:
    amounts = _equal_share_amounts(bill.amount, len(user_ids))
    for user_id, amount in zip(user_ids, amounts, strict=True):
        db.add(
            BillShare(
                bill_id=bill.id,
                user_id=user_id,
                share_amount=amount,
                settled=False,
            )
        )


async def get_bills_paginated(
    db: AsyncSession,
    ledger_id: int,
    *,
    page: int = 1,
    page_size: int = 20,
    year: int | None = None,
    month: int | None = None,
    category: str | None = None,
) -> tuple[list[Bill], int]:
    conditions = [Bill.ledger_id == ledger_id]
    if year is not None:
        conditions.append(extract("year", Bill.bill_date) == year)
    if month is not None:
        conditions.append(extract("month", Bill.bill_date) == month)
    if category:
        conditions.append(Bill.category == category)

    total = (
        await db.execute(select(func.count(Bill.id)).where(*conditions))
    ).scalar_one()
    result = await db.execute(
        select(Bill)
        .options(selectinload(Bill.shares))
        .where(*conditions)
        .order_by(Bill.bill_date.desc(), Bill.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(result.scalars().all()), total


async def get_bill_with_access(
    db: AsyncSession,
    bill_id: int,
    user_id: int,
    *,
    for_update: bool = False,
) -> tuple[Bill, LedgerMember] | None:
    statement = (
        select(Bill, LedgerMember)
        .join(
            LedgerMember,
            LedgerMember.ledger_id == Bill.ledger_id,
        )
        .options(selectinload(Bill.shares))
        .where(
            Bill.id == bill_id,
            LedgerMember.user_id == user_id,
        )
    )
    if for_update:
        statement = statement.with_for_update()
    result = await db.execute(statement)
    row = result.one_or_none()
    return (row[0], row[1]) if row is not None else None


def can_manage_bill(bill: Bill, member: LedgerMember, user_id: int) -> bool:
    if member.user_id != user_id:
        return False
    return bill.creator_id == user_id or member.role in {
        LedgerRole.OWNER,
        LedgerRole.ADMIN,
    }


async def update_bill(
    db: AsyncSession,
    redis: Redis,
    bill: Bill,
    payload: BillUpdate,
) -> Bill:
    old_type = bill.type
    old_amount = float(bill.amount)
    old_category = bill.category
    old_date = bill.bill_date
    old_account = bill.account

    changes = payload.model_dump(exclude_unset=True)
    if bill.shares and changes.get("type") == "income":
        raise ValueError("AA 账单不能修改为收入")
    if "amount" in changes and bill.shares and any(
        share.settled for share in bill.shares
    ):
        raise ValueError("已结算的 AA 账单不能修改金额")

    for field, value in changes.items():
        if field == "type" and value is not None:
            value = BillType(value)
        if field == "amount" and value is not None:
            value = Decimal(str(value))
        setattr(bill, field, value)

    if "amount" in changes and bill.shares:
        amounts = _equal_share_amounts(bill.amount, len(bill.shares))
        for share, amount in zip(bill.shares, amounts, strict=True):
            share.share_amount = amount
    await db.flush()

    await adjust_account_balance(
        db,
        user_id=bill.creator_id,
        ledger_id=bill.ledger_id,
        account_name=old_account,
        bill_type=old_type,
        amount=Decimal(str(old_amount)),
        reverse=True,
    )
    await adjust_account_balance(
        db,
        user_id=bill.creator_id,
        ledger_id=bill.ledger_id,
        account_name=bill.account,
        bill_type=bill.type,
        amount=bill.amount,
    )

    if old_type == BillType.EXPENSE:
        await _update_budget_cache(
            redis,
            bill.creator_id,
            bill.ledger_id,
            old_date.year,
            old_date.month,
            old_category,
            -old_amount,
        )
    if bill.type == BillType.EXPENSE:
        await _update_budget_cache(
            redis,
            bill.creator_id,
            bill.ledger_id,
            bill.bill_date.year,
            bill.bill_date.month,
            bill.category,
            float(bill.amount),
        )
    return bill


async def delete_bill(db: AsyncSession, redis: Redis, bill: Bill) -> None:
    await adjust_account_balance(
        db,
        user_id=bill.creator_id,
        ledger_id=bill.ledger_id,
        account_name=bill.account,
        bill_type=bill.type,
        amount=bill.amount,
        reverse=True,
    )
    if bill.type == BillType.EXPENSE:
        await _update_budget_cache(
            redis,
            bill.creator_id,
            bill.ledger_id,
            bill.bill_date.year,
            bill.bill_date.month,
            bill.category,
            -float(bill.amount),
        )
    await db.delete(bill)
    await db.flush()

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Account
from app.models.bill import BillType
from app.schemas.account import AccountCreate, AccountUpdate


async def list_accounts(
    db: AsyncSession,
    user_id: int,
    ledger_id: int,
) -> list[Account]:
    result = await db.execute(
        select(Account)
        .where(Account.user_id == user_id, Account.ledger_id == ledger_id)
        .order_by(Account.created_at.asc())
    )
    return list(result.scalars().all())


async def create_account(
    db: AsyncSession,
    user_id: int,
    payload: AccountCreate,
) -> Account:
    exists = await db.scalar(
        select(Account.id).where(
            Account.user_id == user_id,
            Account.ledger_id == payload.ledger_id,
            Account.name == payload.name,
        )
    )
    if exists is not None:
        raise ValueError("同名账户已存在")
    account = Account(
        user_id=user_id,
        ledger_id=payload.ledger_id,
        name=payload.name.strip(),
        type=payload.type.strip(),
        icon=payload.icon,
        balance=Decimal(str(payload.balance)),
    )
    db.add(account)
    await db.flush()
    return account


async def get_account(
    db: AsyncSession,
    account_id: int,
    user_id: int,
) -> Account | None:
    result = await db.execute(
        select(Account).where(Account.id == account_id, Account.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def update_account(
    db: AsyncSession,
    account: Account,
    payload: AccountUpdate,
) -> Account:
    for field, value in payload.model_dump(exclude_unset=True).items():
        if field == "balance" and value is not None:
            value = Decimal(str(value))
        if isinstance(value, str):
            value = value.strip()
        setattr(account, field, value)
    await db.flush()
    return account


async def delete_account(db: AsyncSession, account: Account) -> None:
    await db.delete(account)
    await db.flush()


def account_balance_delta(bill_type: BillType, amount: Decimal) -> Decimal:
    """Return the signed balance change caused by one bill."""
    return amount if bill_type == BillType.INCOME else -amount


async def adjust_account_balance(
    db: AsyncSession,
    *,
    user_id: int,
    ledger_id: int,
    account_name: str | None,
    bill_type: BillType,
    amount: Decimal,
    reverse: bool = False,
) -> Account | None:
    """Apply or reverse a bill's effect on its creator's named account.

    Bills keep the account name instead of an account id for compatibility
    with imported v1 data. A missing or deleted account is therefore treated
    as "no linked account" instead of failing the whole bookkeeping request.
    """
    cleaned_name = account_name.strip() if account_name else ""
    if not cleaned_name:
        return None

    result = await db.execute(
        select(Account)
        .where(
            Account.user_id == user_id,
            Account.ledger_id == ledger_id,
            Account.name == cleaned_name,
        )
        .with_for_update()
    )
    account = result.scalar_one_or_none()
    if account is None:
        return None

    delta = account_balance_delta(bill_type, Decimal(amount))
    account.balance += -delta if reverse else delta
    await db.flush()
    return account

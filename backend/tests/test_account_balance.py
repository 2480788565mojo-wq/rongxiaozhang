from decimal import Decimal

import pytest

from app.models import Account, BillType
from app.services.account_service import adjust_account_balance


@pytest.mark.asyncio
async def test_expense_and_reverse_update_account_balance(db_session):
    account = Account(
        user_id=1,
        ledger_id=1,
        name="微信钱包",
        type="电子钱包",
        balance=Decimal("100.00"),
    )
    db_session.add(account)
    await db_session.flush()

    await adjust_account_balance(
        db_session,
        user_id=1,
        ledger_id=1,
        account_name="微信钱包",
        bill_type=BillType.EXPENSE,
        amount=Decimal("18.50"),
    )
    assert account.balance == Decimal("81.50")

    await adjust_account_balance(
        db_session,
        user_id=1,
        ledger_id=1,
        account_name="微信钱包",
        bill_type=BillType.EXPENSE,
        amount=Decimal("18.50"),
        reverse=True,
    )
    assert account.balance == Decimal("100.00")


@pytest.mark.asyncio
async def test_income_increases_account_balance(db_session):
    account = Account(
        user_id=1,
        ledger_id=1,
        name="银行卡",
        type="银行卡",
        balance=Decimal("200.00"),
    )
    db_session.add(account)
    await db_session.flush()

    await adjust_account_balance(
        db_session,
        user_id=1,
        ledger_id=1,
        account_name="银行卡",
        bill_type=BillType.INCOME,
        amount=Decimal("500.00"),
    )
    assert account.balance == Decimal("700.00")


@pytest.mark.asyncio
async def test_unknown_account_does_not_fail(db_session):
    result = await adjust_account_balance(
        db_session,
        user_id=1,
        ledger_id=1,
        account_name="已删除账户",
        bill_type=BillType.EXPENSE,
        amount=Decimal("10.00"),
    )
    assert result is None

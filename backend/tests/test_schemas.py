from pydantic import ValidationError
import pytest

from app.schemas.bill import BillConfirmRequest, BillUpdate, ParsedBillInput, TranscribeRequest
from app.schemas.budget import BudgetSet
from app.schemas.account import AccountCreate, AccountUpdate
from app.schemas.category import CategoryCreate
from app.schemas.ledger import LedgerCreate


def confirm_payload(**overrides) -> dict:
    payload = {
        "session_id": "session-1",
        "raw_input": "五个人聚餐300元",
        "parsed": {
            "type": "expense",
            "amount": 300,
            "category": "餐饮美食",
            "bill_date": "2026-07-15",
        },
        "share_user_ids": [1, 2, 3, 4, 5],
    }
    payload.update(overrides)
    return payload


def test_transcribe_rejects_empty_text():
    with pytest.raises(ValidationError):
        TranscribeRequest(text="")


def test_budget_rejects_invalid_month_and_negative_value():
    with pytest.raises(ValidationError):
        BudgetSet(year=2026, month=13, category_budgets={"餐饮": -1})


def test_confirm_rejects_duplicate_share_members():
    with pytest.raises(ValidationError, match="不能重复"):
        BillConfirmRequest.model_validate(confirm_payload(share_user_ids=[1, 1]))


def test_confirm_requires_at_least_two_share_members():
    with pytest.raises(ValidationError, match="至少需要 2"):
        BillConfirmRequest.model_validate(confirm_payload(share_user_ids=[1]))


def test_bill_update_cannot_clear_required_fields():
    with pytest.raises(ValidationError, match="不能设置为空"):
        BillUpdate(amount=None)


def test_account_update_cannot_clear_balance():
    with pytest.raises(ValidationError, match="不能设置为空"):
        AccountUpdate(balance=None)


def test_category_requires_valid_type():
    with pytest.raises(ValidationError):
        CategoryCreate(ledger_id=1, type="other", name="测试")


def test_extreme_numeric_values_are_rejected():
    with pytest.raises(ValidationError):
        ParsedBillInput(type="expense", amount=float("inf"), category="餐饮", bill_date="2026-07-15")
    with pytest.raises(ValidationError):
        BudgetSet(year=2026, month=7, category_budgets={"餐饮": float("nan")})


def test_blank_names_and_oversized_share_lists_are_rejected():
    with pytest.raises(ValidationError):
        AccountCreate(ledger_id=1, name="   ", type="电子钱包")
    with pytest.raises(ValidationError):
        CategoryCreate(ledger_id=1, type="expense", name="   ")
    with pytest.raises(ValidationError):
        LedgerCreate(name="   ")
    with pytest.raises(ValidationError):
        BillConfirmRequest.model_validate(confirm_payload(share_user_ids=list(range(1, 52))))

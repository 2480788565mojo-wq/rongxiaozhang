from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
import app.api.v1.bills as api
from app.schemas.bill import BillCreateRequest


def test_single_bill_import_key_accepts_rows_after_the_first_thousand():
    request = BillCreateRequest.model_validate(dict(
        ledger_id=1, type="expense", amount=20, category="餐饮",
        bill_date="2026-09-22", import_key="excel:" + "a" * 32 + ":5000",
    ))
    assert request.import_key.endswith(":5000")

@pytest.mark.asyncio
async def test_retry_import_returns_existing_bill_without_changing_balance(monkeypatch):
    bill = SimpleNamespace(id=7, ledger_id=1, creator_id=1, type="expense", amount=20,
        category="餐饮", subcategory=None, account=None, note=None, bill_date=date(2026,9,22),
        raw_input="", ai_parsed=False, created_at=datetime(2026,9,22), shares=[])
    monkeypatch.setattr(api, "require_ledger_access", AsyncMock())
    monkeypatch.setattr(api, "lock_user_for_billing", AsyncMock())
    monkeypatch.setattr(api, "get_bill_by_confirmation_session", AsyncMock(return_value=bill))
    create = AsyncMock(return_value=bill)
    monkeypatch.setattr(api, "create_bill_from_parsed", create)
    monkeypatch.setattr(api, "get_bill_with_access", AsyncMock(return_value=(bill,None)))
    request = BillCreateRequest.model_validate(dict(ledger_id=1, type="expense", amount=20,
        category="餐饮", bill_date="2026-09-22", import_key="excel:" + "a" * 32 + ":2"))
    result = await api.create_bill(request, SimpleNamespace(id=1), AsyncMock(), AsyncMock())
    assert result.id == 7
    create.assert_not_called()

@pytest.mark.asyncio
async def test_new_import_stores_retry_key_and_marks_as_manual(monkeypatch):
    bill = SimpleNamespace(id=7, ledger_id=1, creator_id=1, type="expense", amount=20,
        category="餐饮", subcategory=None, account=None, note=None, bill_date=date(2026,9,22),
        raw_input="", ai_parsed=True, created_at=datetime(2026,9,22), shares=[])
    monkeypatch.setattr(api, "require_ledger_access", AsyncMock())
    monkeypatch.setattr(api, "lock_user_for_billing", AsyncMock())
    monkeypatch.setattr(api, "get_bill_by_confirmation_session", AsyncMock(return_value=None))
    create = AsyncMock(return_value=bill)
    monkeypatch.setattr(api, "create_bill_from_parsed", create)
    monkeypatch.setattr(api, "get_bill_with_access", AsyncMock(return_value=(bill,None)))
    request = BillCreateRequest.model_validate(dict(ledger_id=1,type="expense",amount=20,
        category="餐饮",bill_date="2026-09-22", import_key="excel:" + "a" * 32 + ":2"))
    result = await api.create_bill(request,SimpleNamespace(id=1),AsyncMock(),AsyncMock())
    assert create.call_args.kwargs['confirmation_session_id'] == request.import_key
    assert result.ai_parsed is False

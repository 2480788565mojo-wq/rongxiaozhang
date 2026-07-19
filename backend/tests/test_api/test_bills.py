import json
from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

import app.api.v1.bills as bills_api
from app.models import LedgerType
from app.schemas.bill import BillConfirmRequest, BillUpdate, TranscribeRequest


def confirm_request() -> BillConfirmRequest:
    return BillConfirmRequest.model_validate(
        {
            "ledger_id": 1,
            "session_id": "session-1",
            "raw_input": "午饭68块",
            "parsed": {
                "type": "expense",
                "amount": 68,
                "category": "餐饮美食",
                "bill_date": "2026-07-15",
            },
        }
    )


def bill_record(bill_id: int = 1):
    return SimpleNamespace(
        id=bill_id,
        ledger_id=1,
        creator_id=1,
        type="expense",
        amount=68,
        category="餐饮美食",
        subcategory=None,
        account=None,
        note=None,
        bill_date=date(2026, 7, 15),
        raw_input="午饭68块",
        ai_parsed=True,
        confirmation_session_id="session-1",
        created_at=datetime(2026, 7, 15, 12, 0),
        shares=[],
    )


class FakeGraph:
    def get_state(self, _config):
        return SimpleNamespace(values={})

    async def astream(self, _state, _config):
        yield {
            "parser": {
                "parsed": {
                    "type": "expense",
                    "amount": 68,
                    "category": "餐饮美食",
                    "bill_date": "2026-07-15",
                },
                "missing_fields": [],
                "clarification_question": None,
                "error": None,
            }
        }


@pytest.mark.asyncio
async def test_transcribe_waits_for_confirmation(monkeypatch):
    monkeypatch.setattr(
        bills_api,
        "_require_ledger",
        AsyncMock(return_value=(SimpleNamespace(type=LedgerType.PERSONAL), None)),
    )
    monkeypatch.setattr(bills_api, "get_compiled_graph", lambda: FakeGraph())
    monkeypatch.setattr(bills_api, "require_rate_limits", AsyncMock())

    response = await bills_api.transcribe_bill(
        TranscribeRequest(text="午饭68块", ledger_id=1),
        SimpleNamespace(id=1),
        AsyncMock(),
        AsyncMock(),
    )
    chunks = []
    async for chunk in response.body_iterator:
        chunks.append(chunk.decode() if isinstance(chunk, bytes) else chunk)
    body = "".join(chunks)

    assert "event: parsed" in body
    assert "event: awaiting_confirmation" in body
    assert "event: completed" not in body


@pytest.mark.asyncio
async def test_confirm_returns_conflict_before_warning_is_forced(monkeypatch):
    monkeypatch.setattr(
        bills_api,
        "_require_ledger",
        AsyncMock(return_value=(SimpleNamespace(type=LedgerType.PERSONAL), None)),
    )

    async def warning_guardian(state, db=None):
        state["risk_level"] = "warning"
        state["budget_check"] = {"percentage": 85, "remaining": 150}
        return state

    create_bill = AsyncMock()
    monkeypatch.setattr(bills_api, "guardian_node", warning_guardian)
    monkeypatch.setattr(bills_api, "lock_user_for_billing", AsyncMock())
    monkeypatch.setattr(
        bills_api,
        "get_bill_by_confirmation_session",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(bills_api, "create_bill_from_parsed", create_bill)
    monkeypatch.setattr(bills_api, "publish_user_event", AsyncMock())

    response = await bills_api.confirm_bill(
        confirm_request(),
        SimpleNamespace(id=1),
        AsyncMock(),
        AsyncMock(),
    )

    assert response.status_code == 409
    assert json.loads(response.body)["status"] == "warning"
    create_bill.assert_not_awaited()


@pytest.mark.asyncio
async def test_repeated_confirmation_returns_existing_bill(monkeypatch):
    existing = bill_record()
    monkeypatch.setattr(
        bills_api,
        "_require_ledger",
        AsyncMock(return_value=(SimpleNamespace(type=LedgerType.PERSONAL), None)),
    )
    lock = AsyncMock()
    monkeypatch.setattr(bills_api, "lock_user_for_billing", lock)
    monkeypatch.setattr(
        bills_api,
        "get_bill_by_confirmation_session",
        AsyncMock(return_value=existing),
    )
    create_bill = AsyncMock()
    monkeypatch.setattr(bills_api, "create_bill_from_parsed", create_bill)

    response = await bills_api.confirm_bill(
        confirm_request(),
        SimpleNamespace(id=1),
        AsyncMock(),
        AsyncMock(),
    )

    assert response.id == existing.id
    lock.assert_awaited_once()
    create_bill.assert_not_awaited()


@pytest.mark.asyncio
async def test_notification_failure_does_not_turn_saved_bill_into_failure(monkeypatch):
    saved = bill_record(2)
    monkeypatch.setattr(
        bills_api,
        "_require_ledger",
        AsyncMock(return_value=(SimpleNamespace(type=LedgerType.PERSONAL), None)),
    )
    monkeypatch.setattr(bills_api, "lock_user_for_billing", AsyncMock())
    monkeypatch.setattr(
        bills_api,
        "get_bill_by_confirmation_session",
        AsyncMock(return_value=None),
    )

    async def safe_guardian(state, db=None):
        state["risk_level"] = "safe"
        return state

    create_bill = AsyncMock(return_value=saved)
    monkeypatch.setattr(bills_api, "guardian_node", safe_guardian)
    monkeypatch.setattr(bills_api, "create_bill_from_parsed", create_bill)
    monkeypatch.setattr(
        bills_api,
        "get_bill_with_access",
        AsyncMock(return_value=(saved, None)),
    )
    monkeypatch.setattr(
        bills_api,
        "publish_user_event",
        AsyncMock(side_effect=RuntimeError("redis unavailable")),
    )

    response = await bills_api.confirm_bill(
        confirm_request(),
        SimpleNamespace(id=1),
        AsyncMock(),
        AsyncMock(),
    )

    assert response.id == 2
    assert create_bill.await_args.kwargs["confirmation_session_id"] == "session-1"


@pytest.mark.asyncio
async def test_edit_and_delete_lock_bill_before_changing_balances(monkeypatch):
    bill = bill_record()
    member = SimpleNamespace(user_id=1)
    get_bill = AsyncMock(return_value=(bill, member))
    monkeypatch.setattr(bills_api, "get_bill_with_access", get_bill)
    monkeypatch.setattr(bills_api, "can_manage_bill", lambda *_: True)
    monkeypatch.setattr(bills_api, "update_bill", AsyncMock())
    monkeypatch.setattr(bills_api, "delete_bill", AsyncMock())
    db = AsyncMock()

    await bills_api.edit_bill(1, BillUpdate(note="更新"), SimpleNamespace(id=1), db, AsyncMock())
    assert get_bill.await_args_list[0].kwargs["for_update"] is True

    get_bill.reset_mock()
    await bills_api.remove_bill(1, SimpleNamespace(id=1), db, AsyncMock())
    assert get_bill.await_args.kwargs["for_update"] is True

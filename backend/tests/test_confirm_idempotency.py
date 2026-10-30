"""Bug I5: confirm must check idempotency before AI/guardian and again under the write lock."""

from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.exc import MultipleResultsFound

import app.api.v1.bills as bills_api
from app.api.v1.bills import confirm_bill
from app.models import BillType
from app.models.bill import Bill
from app.schemas.bill import BillConfirmRequest
from app.services.bill_service import get_bill_by_confirmation_session
from fake_redis import FakeRedis

LEDGER_ID = 1
SESSION_ID = "session-1"
LOCK_KEY = f"lock:ledger:{LEDGER_ID}:write"


def confirm_request() -> BillConfirmRequest:
    return BillConfirmRequest.model_validate(
        {
            "ledger_id": LEDGER_ID,
            "session_id": SESSION_ID,
            "raw_input": "午饭20块",
            "parsed": {
                "type": "expense",
                "amount": 20,
                "category": "餐饮",
                "bill_date": "2026-09-22",
            },
        }
    )


def existing_bill_record(bill_id: int = 7) -> SimpleNamespace:
    return SimpleNamespace(
        id=bill_id,
        ledger_id=LEDGER_ID,
        creator_id=1,
        type="expense",
        amount=20,
        category="餐饮",
        subcategory=None,
        account=None,
        note=None,
        bill_date=date(2026, 9, 22),
        raw_input="午饭20块",
        ai_parsed=True,
        confirmation_session_id=SESSION_ID,
        created_at=datetime(2026, 9, 22, 12, 0),
        shares=[],
    )


def patch_common(monkeypatch) -> None:
    monkeypatch.setattr(
        bills_api,
        "require_ledger_access",
        AsyncMock(return_value=(SimpleNamespace(type=SimpleNamespace(value="personal")), None)),
    )
    monkeypatch.setattr(bills_api, "lock_user_for_billing", AsyncMock())


@pytest.mark.asyncio
async def test_existing_bill_returned_without_guardian_or_create_and_lookup_under_lock(
    db_session, monkeypatch
):
    redis = FakeRedis()
    stored = Bill(
        ledger_id=LEDGER_ID,
        creator_id=1,
        type=BillType.EXPENSE,
        amount=Decimal("20.00"),
        category="餐饮",
        bill_date=date(2026, 9, 22),
        raw_input="午饭20块",
        ai_parsed=True,
        confirmation_session_id=SESSION_ID,
    )
    db_session.add(stored)
    await db_session.commit()
    await db_session.refresh(stored)

    lock_held_during_lookup: list[bool] = []

    async def lookup(db, user_id, ledger_id, session_id):
        lock_held_during_lookup.append(bool(redis.values.get(LOCK_KEY)))
        return await get_bill_by_confirmation_session(db, user_id, ledger_id, session_id)

    guardian = AsyncMock()
    create = AsyncMock()
    graph = AsyncMock()
    clear = AsyncMock()
    monkeypatch.setattr(bills_api, "get_bill_by_confirmation_session", lookup)
    monkeypatch.setattr(bills_api, "guardian_budget_node", guardian)
    monkeypatch.setattr(bills_api, "create_bill_from_parsed", create)
    monkeypatch.setattr(bills_api, "get_compiled_graph", graph)
    monkeypatch.setattr(bills_api, "clear_transaction_session", clear)
    patch_common(monkeypatch)

    result = await confirm_bill(
        confirm_request(), SimpleNamespace(id=1), db_session, redis
    )

    assert result.id == stored.id
    assert result.category == "餐饮"
    # The lookup that returned the existing bill saw the ledger lock held.
    assert lock_held_during_lookup == [True]
    guardian.assert_not_awaited()
    create.assert_not_awaited()
    graph.assert_not_called()
    clear.assert_awaited_once_with(1, LEDGER_ID, SESSION_ID)
    # Early return: exactly one acquisition, released afterwards.
    assert len(redis.acquire_calls()) == 1
    assert len(redis.eval_calls()) == 1
    assert LOCK_KEY not in redis.values


@pytest.mark.asyncio
async def test_idempotent_retry_returns_existing_with_single_lock(monkeypatch):
    redis = FakeRedis()
    existing = existing_bill_record()

    calls: list[int] = []

    async def wrapped_lookup(*_args, **_kwargs):
        calls.append(1)
        return existing

    async def guardian(state, db=None):
        state["risk_level"] = "safe"
        return state

    create = AsyncMock()
    publish = AsyncMock()
    clear = AsyncMock()
    monkeypatch.setattr(bills_api, "get_bill_by_confirmation_session", wrapped_lookup)
    monkeypatch.setattr(bills_api, "guardian_budget_node", guardian)
    monkeypatch.setattr(bills_api, "create_bill_from_parsed", create)
    monkeypatch.setattr(bills_api, "publish_user_event", publish)
    monkeypatch.setattr(bills_api, "clear_transaction_session", clear)
    monkeypatch.setattr(
        bills_api, "get_compiled_graph", lambda: (_ for _ in ()).throw(RuntimeError("no graph"))
    )
    patch_common(monkeypatch)

    result = await confirm_bill(
        confirm_request(), SimpleNamespace(id=1), AsyncMock(), redis
    )

    assert result.id == existing.id
    assert len(calls) == 1, "single lock checks idempotency once"
    create.assert_not_awaited()
    publish.assert_not_awaited()
    clear.assert_awaited_once_with(1, LEDGER_ID, SESSION_ID)
    assert len(redis.acquire_calls()) == 1
    assert len(redis.eval_calls()) == 1
    assert LOCK_KEY not in redis.values


class DuplicateRowsResult:
    """Result shape of a legacy duplicate idempotency key."""

    def __init__(self, rows):
        self.rows = rows
        self.first_calls = 0
        self.scalar_one_or_none_calls = 0

    def scalars(self):
        return self

    def first(self):
        self.first_calls += 1
        return self.rows[0]

    def scalar_one_or_none(self):
        self.scalar_one_or_none_calls += 1
        raise MultipleResultsFound("Multiple rows were found when one or none was required")


@pytest.mark.asyncio
async def test_historical_duplicate_rows_do_not_raise_multiple_results_found(monkeypatch):
    winner = existing_bill_record(7)
    duplicate = existing_bill_record(8)
    result = DuplicateRowsResult([winner, duplicate])

    async def fake_execute(*_args, **_kwargs):
        return result

    db = AsyncMock()
    db.execute = fake_execute

    returned = await get_bill_by_confirmation_session(db, 1, LEDGER_ID, SESSION_ID)

    assert returned is winner
    assert result.first_calls == 1
    # The regression was scalar_one_or_none() raising on two legacy rows.
    assert result.scalar_one_or_none_calls == 0
    with pytest.raises(MultipleResultsFound):
        result.scalar_one_or_none()

"""Tests for the shared-ledger write lock and every bill write route."""

import asyncio
from contextlib import asynccontextmanager
from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from redis.exceptions import RedisError

import app.api.v1.bills as bills_api
import app.api.v1.ledgers as ledgers_api
import app.core.redis as redis_module
from app.api.v1.bills import (
    confirm_bill,
    create_bill,
    edit_bill,
    import_bills,
    remove_bill,
)
from app.core.database import get_db
from app.core.redis import (
    LedgerLockBusy,
    LedgerLockUnavailable,
    acquire_ledger_lock,
    get_redis,
    ledger_write_lock,
    release_ledger_lock,
    renew_ledger_lock,
)
from app.core.security import get_current_user
from app.main import create_app
from app.models import LedgerType
from app.schemas.bill import (
    BillConfirmRequest,
    BillCreateRequest,
    BillImportRequest,
    BillUpdate,
)
from app.schemas.ledger import SettlementConfirm
from fake_redis import FakeRedis


LEDGER_ID = 1
LOCK_KEY = f"lock:ledger:{LEDGER_ID}:write"


def bill_record(bill_id: int = 1) -> SimpleNamespace:
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
        raw_input="",
        ai_parsed=False,
        confirmation_session_id=None,
        created_at=datetime(2026, 9, 22, 12, 0),
        shares=[],
    )


def create_request() -> BillCreateRequest:
    return BillCreateRequest(
        ledger_id=LEDGER_ID,
        type="expense",
        amount=20,
        category="餐饮",
        bill_date=date(2026, 9, 22),
    )


def import_request() -> BillImportRequest:
    return BillImportRequest.model_validate(
        {
            "ledger_id": LEDGER_ID,
            "items": [
                {
                    "import_key": "excel:" + "a" * 32 + ":0",
                    "type": "expense",
                    "amount": 20,
                    "category": "餐饮",
                    "bill_date": "2026-09-22",
                }
            ],
        }
    )


def confirm_request() -> BillConfirmRequest:
    return BillConfirmRequest.model_validate(
        {
            "ledger_id": LEDGER_ID,
            "session_id": "session-1",
            "raw_input": "午饭20块",
            "parsed": {
                "type": "expense",
                "amount": 20,
                "category": "餐饮",
                "bill_date": "2026-09-22",
            },
        }
    )


def assert_lock_held_during_write(redis: FakeRedis) -> None:
    assert redis.values.get(LOCK_KEY), "write ran without holding the ledger lock"


async def safe_guardian(state, db=None):
    state["risk_level"] = "safe"
    return state


# Each runner invokes a real route handler and probes the lock inside the
# service call that performs the write.
async def run_create(patch, redis):
    patch.setattr(
        bills_api,
        "require_ledger_access",
        AsyncMock(return_value=(SimpleNamespace(type=LedgerType.PERSONAL), None)),
    )
    patch.setattr(bills_api, "lock_user_for_billing", AsyncMock())
    patch.setattr(
        bills_api, "get_bill_by_confirmation_session", AsyncMock(return_value=None)
    )

    async def create(*_args, **_kwargs):
        assert_lock_held_during_write(redis)
        return bill_record()

    patch.setattr(bills_api, "create_bill_from_parsed", create)
    patch.setattr(
        bills_api, "get_bill_with_access", AsyncMock(return_value=(bill_record(), None))
    )
    await create_bill(create_request(), SimpleNamespace(id=1), AsyncMock(), redis)


async def run_import(patch, redis):
    patch.setattr(
        bills_api,
        "require_ledger_access",
        AsyncMock(return_value=(SimpleNamespace(type=LedgerType.PERSONAL), None)),
    )
    patch.setattr(bills_api, "lock_user_for_billing", AsyncMock())

    async def prepare(*_args, **_kwargs):
        assert_lock_held_during_write(redis)
        return [], {}

    patch.setattr(bills_api, "prepare_bill_import", prepare)
    patch.setattr(bills_api, "update_import_budget_cache", AsyncMock())
    response = await import_bills(
        import_request(), SimpleNamespace(id=1), AsyncMock(), redis
    )
    assert response.items == []


async def run_confirm(patch, redis):
    patch.setattr(
        bills_api,
        "require_ledger_access",
        AsyncMock(return_value=(SimpleNamespace(type=LedgerType.PERSONAL), None)),
    )
    patch.setattr(bills_api, "lock_user_for_billing", AsyncMock())
    patch.setattr(
        bills_api, "get_bill_by_confirmation_session", AsyncMock(return_value=None)
    )

    def no_graph():
        raise RuntimeError("graph unavailable in test")

    patch.setattr(bills_api, "get_compiled_graph", no_graph)
    patch.setattr(bills_api, "guardian_budget_node", safe_guardian)

    async def create(*_args, **_kwargs):
        assert_lock_held_during_write(redis)
        return bill_record()

    patch.setattr(bills_api, "create_bill_from_parsed", create)
    patch.setattr(bills_api, "clear_transaction_session", AsyncMock())
    patch.setattr(
        bills_api, "get_bill_with_access", AsyncMock(return_value=(bill_record(), None))
    )
    patch.setattr(bills_api, "publish_user_event", AsyncMock())
    result = await confirm_bill(
        confirm_request(), SimpleNamespace(id=1), AsyncMock(), redis
    )
    assert result.id == 1


async def run_edit(patch, redis):
    patch.setattr(
        bills_api,
        "get_bill_with_access",
        AsyncMock(return_value=(bill_record(), SimpleNamespace(user_id=1))),
    )
    patch.setattr(bills_api, "can_manage_bill", lambda *_: True)

    async def update(*_args, **_kwargs):
        assert_lock_held_during_write(redis)

    patch.setattr(bills_api, "update_bill", update)
    await edit_bill(1, BillUpdate(note="备注"), SimpleNamespace(id=1), AsyncMock(), redis)


async def run_delete(patch, redis):
    patch.setattr(
        bills_api,
        "get_bill_with_access",
        AsyncMock(return_value=(bill_record(), SimpleNamespace(user_id=1))),
    )
    patch.setattr(bills_api, "can_manage_bill", lambda *_: True)

    async def delete(*_args, **_kwargs):
        assert_lock_held_during_write(redis)

    patch.setattr(bills_api, "delete_bill", delete)
    response = await remove_bill(1, SimpleNamespace(id=1), AsyncMock(), redis)
    assert response.status_code == 204


WRITE_ROUTES = [
    (run_create, 1),
    (run_import, 1),
    # Confirm keeps one lock across idempotency check, AI/guardian and create.
    (run_confirm, 1),
    (run_edit, 1),
    (run_delete, 1),
]


@pytest.mark.asyncio
async def test_acquire_is_exclusive_and_sets_ttl():
    redis = FakeRedis()

    assert await acquire_ledger_lock(redis, LEDGER_ID, "first", ttl=5) is True
    assert redis.values[LOCK_KEY] == "first"
    assert 0 < await redis.ttl(LOCK_KEY) <= 5

    assert await acquire_ledger_lock(redis, LEDGER_ID, "second") is False
    assert redis.values[LOCK_KEY] == "first"


@pytest.mark.asyncio
async def test_release_only_deletes_matching_token():
    redis = FakeRedis()
    assert await acquire_ledger_lock(redis, LEDGER_ID, "owner") is True

    assert await release_ledger_lock(redis, LEDGER_ID, "intruder") is False
    assert redis.values[LOCK_KEY] == "owner"

    assert await release_ledger_lock(redis, LEDGER_ID, "owner") is True
    assert LOCK_KEY not in redis.values
    # A double release must not claim ownership a second time.
    assert await release_ledger_lock(redis, LEDGER_ID, "owner") is False


@pytest.mark.asyncio
async def test_context_manager_acquires_then_releases():
    redis = FakeRedis()
    async with ledger_write_lock(redis, LEDGER_ID):
        assert redis.values[LOCK_KEY]

    assert LOCK_KEY not in redis.values
    assert len(redis.acquire_calls()) == 1
    assert len(redis.eval_calls()) == 1


@pytest.mark.asyncio
async def test_context_manager_releases_when_body_raises():
    redis = FakeRedis()
    with pytest.raises(ValueError, match="write failed"):
        async with ledger_write_lock(redis, LEDGER_ID):
            raise ValueError("write failed")

    assert LOCK_KEY not in redis.values
    assert len(redis.eval_calls()) == 1


@pytest.mark.asyncio
async def test_busy_lock_raises_without_stealing_the_owner_lock():
    redis = FakeRedis()
    assert await acquire_ledger_lock(redis, LEDGER_ID, "other-request") is True

    with pytest.raises(LedgerLockBusy):
        async with ledger_write_lock(redis, LEDGER_ID):
            pytest.fail("lock body must not run while another request holds it")

    assert redis.values[LOCK_KEY] == "other-request"
    assert redis.eval_calls() == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("runner", "expected_acquires"),
    WRITE_ROUTES,
    ids=[fn.__name__ for fn, _ in WRITE_ROUTES],
)
async def test_write_routes_acquire_and_release_lock(
    runner, expected_acquires, monkeypatch
):
    redis = FakeRedis()
    with monkeypatch.context() as patch:
        await runner(patch, redis)

    assert len(redis.acquire_calls()) == expected_acquires
    assert len(redis.eval_calls()) == expected_acquires
    assert LOCK_KEY not in redis.values


@pytest.mark.asyncio
async def test_busy_lock_returns_409_via_global_handler(monkeypatch):
    redis = FakeRedis()
    assert await acquire_ledger_lock(redis, LEDGER_ID, "other-request") is True

    monkeypatch.setattr(
        bills_api,
        "require_ledger_access",
        AsyncMock(return_value=(SimpleNamespace(type=LedgerType.PERSONAL), None)),
    )
    monkeypatch.setattr(bills_api, "lock_user_for_billing", AsyncMock())
    create = AsyncMock()
    monkeypatch.setattr(bills_api, "create_bill_from_parsed", create)

    application = create_app()
    application.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1)
    application.dependency_overrides[get_db] = lambda: AsyncMock()
    application.dependency_overrides[get_redis] = lambda: redis
    transport = httpx.ASGITransport(app=application, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/bills",
            json={
                "ledger_id": LEDGER_ID,
                "type": "expense",
                "amount": 20,
                "category": "餐饮",
                "bill_date": "2026-09-22",
            },
        )

    assert response.status_code == 409, response.text
    assert response.headers["Retry-After"] == "1"
    assert response.json()["detail"] == "账本正在被其他请求修改，请稍后重试"
    create.assert_not_awaited()
    assert redis.values[LOCK_KEY] == "other-request"


@pytest.mark.asyncio
async def test_settlement_confirmation_runs_under_ledger_lock(monkeypatch):
    entered: list[int] = []

    @asynccontextmanager
    async def fake_lock(_redis, ledger_id, **_kwargs):
        entered.append(ledger_id)
        yield

    monkeypatch.setattr(ledgers_api, "ledger_write_lock", fake_lock)
    monkeypatch.setattr(ledgers_api, "require_ledger_access", AsyncMock())
    service = AsyncMock(return_value=[])
    monkeypatch.setattr(ledgers_api, "confirm_settlement", service)
    db = AsyncMock()

    response = await ledgers_api.confirm_shared_settlement(
        LEDGER_ID,
        SettlementConfirm(from_user_id=1, to_user_id=2, share_ids=[1]),
        SimpleNamespace(id=1),
        db,
        object(),
    )

    assert entered == [LEDGER_ID]
    assert response.ledger_id == LEDGER_ID
    assert response.settlements == []
    service.assert_awaited_once()
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_busy_lock_returns_409_for_settlement_confirmation(monkeypatch):
    redis = FakeRedis()
    assert await acquire_ledger_lock(redis, LEDGER_ID, "other-request") is True

    # The stale-plan risk: while another writer holds the ledger lock, the
    # settlement confirmation must be rejected before any share is marked.
    service = AsyncMock()
    monkeypatch.setattr(ledgers_api, "confirm_settlement", service)
    monkeypatch.setattr(ledgers_api, "require_ledger_access", AsyncMock())

    application = create_app()
    application.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1)
    application.dependency_overrides[get_db] = lambda: AsyncMock()
    application.dependency_overrides[get_redis] = lambda: redis
    transport = httpx.ASGITransport(app=application, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/ledgers/{LEDGER_ID}/settle/confirm",
            json={"from_user_id": 1, "to_user_id": 2, "share_ids": [1]},
        )

    assert response.status_code == 409, response.text
    assert response.headers["Retry-After"] == "1"
    assert response.json()["detail"] == "账本正在被其他请求修改，请稍后重试"
    service.assert_not_awaited()
    assert redis.values[LOCK_KEY] == "other-request"
    assert redis.eval_calls() == []


@pytest.mark.asyncio
async def test_confirm_idempotency_lookup_runs_under_lock(monkeypatch):
    held = False

    @asynccontextmanager
    async def fake_lock(_redis, _ledger_id, **_kwargs):
        nonlocal held
        held = True
        try:
            yield
        finally:
            held = False

    async def existing_bill(*_args, **_kwargs):
        assert held, "idempotency lookup ran outside the ledger lock"
        return bill_record()

    monkeypatch.setattr(bills_api, "ledger_write_lock", fake_lock)
    monkeypatch.setattr(
        bills_api,
        "require_ledger_access",
        AsyncMock(return_value=(SimpleNamespace(type=LedgerType.PERSONAL), None)),
    )
    monkeypatch.setattr(bills_api, "lock_user_for_billing", AsyncMock())
    monkeypatch.setattr(
        bills_api, "get_bill_by_confirmation_session", existing_bill
    )
    monkeypatch.setattr(bills_api, "clear_transaction_session", AsyncMock())

    result = await confirm_bill(
        confirm_request(), SimpleNamespace(id=1), AsyncMock(), object()
    )

    assert result.id == 1


@pytest.mark.asyncio
async def test_ledger_lock_retries_transient_busy(monkeypatch):
    calls: list[int] = []

    async def fake_acquire(_redis, ledger_id, _request_id, ttl=30):
        calls.append(ledger_id)
        return len(calls) >= 3

    async def fake_release(_redis, _ledger_id, _request_id):
        return True

    monkeypatch.setattr("app.core.redis.acquire_ledger_lock", fake_acquire)
    monkeypatch.setattr("app.core.redis.release_ledger_lock", fake_release)

    async with ledger_write_lock(object(), LEDGER_ID):
        pass

    assert calls == [LEDGER_ID, LEDGER_ID, LEDGER_ID]


@pytest.mark.asyncio
async def test_ledger_lock_uses_long_enough_ttl(monkeypatch):
    captured: dict[str, int] = {}

    async def fake_acquire(_redis, _ledger_id, _request_id, ttl=30):
        captured["ttl"] = ttl
        return True

    async def fake_release(_redis, _ledger_id, _request_id):
        return True

    monkeypatch.setattr("app.core.redis.acquire_ledger_lock", fake_acquire)
    monkeypatch.setattr("app.core.redis.release_ledger_lock", fake_release)

    async with ledger_write_lock(object(), LEDGER_ID):
        pass

    assert captured["ttl"] >= 30


@pytest.mark.asyncio
async def test_ledger_lock_maps_redis_failure_to_unavailable():
    class BrokenRedis:
        async def set(self, *args, **kwargs):
            raise RedisError("connection refused")

    with pytest.raises(LedgerLockUnavailable):
        async with ledger_write_lock(BrokenRedis(), LEDGER_ID):
            pass


@pytest.mark.asyncio
async def test_redis_failure_on_write_route_returns_503_without_service_call(monkeypatch):
    class BrokenLockRedis:
        """Redis is down for the lock acquisition itself, not just the cache."""

        def __init__(self):
            self.set_attempts: list[tuple] = []

        async def set(self, key, value, **kwargs):
            self.set_attempts.append((key, str(value), kwargs.get("ex")))
            raise RedisError("connection refused")

    redis = BrokenLockRedis()
    monkeypatch.setattr(
        bills_api,
        "require_ledger_access",
        AsyncMock(return_value=(SimpleNamespace(type=LedgerType.PERSONAL), None)),
    )
    monkeypatch.setattr(bills_api, "lock_user_for_billing", AsyncMock())
    create = AsyncMock(return_value=bill_record())
    monkeypatch.setattr(bills_api, "create_bill_from_parsed", create)

    application = create_app()
    application.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1)
    application.dependency_overrides[get_db] = lambda: AsyncMock()
    application.dependency_overrides[get_redis] = lambda: redis
    transport = httpx.ASGITransport(app=application, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/bills",
            json={
                "ledger_id": LEDGER_ID,
                "type": "expense",
                "amount": 20,
                "category": "餐饮",
                "bill_date": "2026-09-22",
            },
        )

    assert response.status_code == 503, response.text
    assert response.headers["Retry-After"] == "2"
    assert response.json()["detail"] == "账本锁服务暂时不可用，请稍后重试"
    create.assert_not_awaited()
    # A RedisError aborts immediately instead of burning all retry attempts.
    assert len(redis.set_attempts) == 1
    assert redis.set_attempts[0][2] == 30


@pytest.mark.asyncio
async def test_busy_lock_retry_eventually_writes_through_asgi(monkeypatch):
    class FlakyBusyRedis(FakeRedis):
        """Fail the first acquires as if another writer held the lock."""

        def __init__(self, busy_attempts: int):
            super().__init__()
            self.busy_attempts = busy_attempts
            self.set_attempts: list[tuple] = []

        async def set(self, key, value, *, nx=False, ex=None, **kwargs):
            self.set_attempts.append((key, str(value), nx, ex))
            if nx and self.busy_attempts > 0:
                self.busy_attempts -= 1
                self.calls.append(("set", key, str(value), nx, ex))
                return None
            return await super().set(key, value, nx=nx, ex=ex, **kwargs)

    redis = FlakyBusyRedis(busy_attempts=2)
    monkeypatch.setattr(
        bills_api,
        "require_ledger_access",
        AsyncMock(return_value=(SimpleNamespace(type=LedgerType.PERSONAL), None)),
    )
    monkeypatch.setattr(bills_api, "lock_user_for_billing", AsyncMock())
    create = AsyncMock(return_value=bill_record())
    monkeypatch.setattr(bills_api, "create_bill_from_parsed", create)
    monkeypatch.setattr(
        bills_api, "get_bill_with_access", AsyncMock(return_value=(bill_record(), None))
    )

    application = create_app()
    application.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1)
    application.dependency_overrides[get_db] = lambda: AsyncMock()
    application.dependency_overrides[get_redis] = lambda: redis
    transport = httpx.ASGITransport(app=application, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/bills",
            json={
                "ledger_id": LEDGER_ID,
                "type": "expense",
                "amount": 20,
                "category": "餐饮",
                "bill_date": "2026-09-22",
            },
        )

    assert response.status_code == 200, response.text
    assert response.json()["id"] == 1
    create.assert_awaited_once()
    # Two busy replies, then the third acquire wins; every attempt carries the
    # 30s TTL, and the winner is released after the write.
    assert [call[2] for call in redis.set_attempts] == [True, True, True]
    assert {call[3] for call in redis.set_attempts} == {30}
    assert len(redis.acquire_calls()) == 3
    assert len(redis.eval_calls()) == 1
    assert LOCK_KEY not in redis.values


@pytest.mark.asyncio
async def test_renew_extends_only_the_owner_token():
    redis = FakeRedis()
    assert await acquire_ledger_lock(redis, LEDGER_ID, "owner", ttl=1) is True

    assert await renew_ledger_lock(redis, LEDGER_ID, "other", 30) is False
    assert await renew_ledger_lock(redis, LEDGER_ID, "owner", 30) is True
    assert await redis.ttl(LOCK_KEY) > 5


@pytest.mark.asyncio
async def test_extended_retry_waits_for_short_contention():
    redis = FakeRedis()
    assert await acquire_ledger_lock(redis, LEDGER_ID, "owner") is True

    async def release_soon():
        await asyncio.sleep(0.7)
        await release_ledger_lock(redis, LEDGER_ID, "owner")

    releaser = asyncio.create_task(release_soon())
    async with ledger_write_lock(redis, LEDGER_ID, retry_attempts=30):
        assert LOCK_KEY in redis.values
    await releaser
    assert LOCK_KEY not in redis.values


@pytest.mark.asyncio
async def test_lost_lock_cancels_owner_before_write(monkeypatch):
    redis = FakeRedis()

    async def lost_renewal(*_args, **_kwargs):
        return False

    monkeypatch.setattr(redis_module, "renew_ledger_lock", lost_renewal)

    with pytest.raises(asyncio.CancelledError):
        async with ledger_write_lock(redis, LEDGER_ID, ttl=1):
            await asyncio.sleep(1.0)

    assert LOCK_KEY not in redis.values


@pytest.mark.asyncio
async def test_lock_is_reusable_by_the_next_request(monkeypatch):
    redis = FakeRedis()
    with monkeypatch.context() as patch:
        await run_import(patch, redis)
    assert LOCK_KEY not in redis.values

    # A second request acquires the same lock again instead of deadlocking.
    with monkeypatch.context() as patch:
        await run_import(patch, redis)
    assert LOCK_KEY not in redis.values
    assert len(redis.acquire_calls()) == 2
    assert len(redis.eval_calls()) == 2

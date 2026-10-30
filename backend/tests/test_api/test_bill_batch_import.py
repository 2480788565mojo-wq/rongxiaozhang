from decimal import Decimal
from datetime import datetime, timezone
from types import SimpleNamespace

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import MetaData, Select, String, event, func, select

from app.api.v1.bills import router
from app.core.database import get_db
from app.core.redis import get_redis
from app.core.security import get_current_user
from app.models import Account, Bill, Ledger, LedgerMember, LedgerRole, User
from fake_redis import FakeRedis


class BudgetCache(FakeRedis):
    """Redis-free test boundary; expose counters to check retry side effects.

    Inherits ``set(nx/ex)`` and the compare-and-delete ``eval`` script so the
    ledger write lock behaves like Redis instead of blowing up the route.
    """

    def __init__(self):
        # Pin the clock to the fixture bill date so month-scoped budget keys
        # stay alive. These tests assert idempotency, not calendar expiry.
        super().__init__(
            clock=lambda: datetime(2026, 9, 22, 12, tzinfo=timezone.utc).timestamp()
        )
        self.unavailable = False

    async def incrbyfloat(self, key, value):
        if self.unavailable:
            raise RuntimeError("redis unavailable")
        return await super().incrbyfloat(key, value)


@pytest.fixture
async def import_context(db_session):
    def use_case_insensitive_account_names(connection):
        # Production MySQL can match names case-insensitively. Exercise that
        # database rule in the isolated in-memory SQLite schema, not in Python.
        metadata = MetaData()
        User.__table__.to_metadata(metadata)
        Ledger.__table__.to_metadata(metadata)
        account_table = Account.__table__.to_metadata(metadata)
        account_table.c.name.type = String(64, collation="NOCASE")
        Account.__table__.drop(connection)
        account_table.create(connection)

    connection = await db_session.connection()
    await connection.run_sync(use_case_insensitive_account_names)
    db_session.add_all([
        User(id=1, openid="batch-owner"),
        User(id=2, openid="batch-other"),
        Ledger(id=1, name="我的账本", owner_id=1),
        Ledger(id=2, name="他人账本", owner_id=2),
        LedgerMember(ledger_id=1, user_id=1, role=LedgerRole.OWNER),
        LedgerMember(ledger_id=2, user_id=2, role=LedgerRole.OWNER),
        Account(id=1, user_id=1, ledger_id=1, name="钱包", type="cash", balance=Decimal("100.00")),
        Account(id=2, user_id=2, ledger_id=2, name="钱包", type="cash", balance=Decimal("300.00")),
    ])
    await db_session.commit()
    cache = BudgetCache()

    async def database():
        try:
            yield db_session
            await db_session.commit()
        except Exception:
            await db_session.rollback()
            raise

    app = FastAPI()
    app.include_router(router, prefix="/bills")
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1)
    app.dependency_overrides[get_db] = database
    app.dependency_overrides[get_redis] = lambda: cache
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield SimpleNamespace(client=client, db=db_session, cache=cache)


def item(index=0, **changes):
    return {
        "import_key": f"excel:{index:032x}:0",
        "type": "expense",
        "amount": 20,
        "category": "餐饮",
        "account": "钱包",
        "bill_date": "2026-09-22",
        **changes,
    }


async def bill_count(context):
    return await context.db.scalar(select(func.count()).select_from(Bill))


async def balance(context, account_id=1):
    return await context.db.scalar(select(Account.balance).where(Account.id == account_id))


def assert_cached_spending(cache, expected):
    """分类键和总预算键都必须累计同一笔支出，不能只校验其中一个。"""
    # FakeRedis stores payloads as strings, matching decode_responses=True.
    category_spent = sum(
        float(value) for key, value in cache.values.items() if key.startswith("budget:")
    )
    total_spent = sum(
        float(value)
        for key, value in cache.values.items()
        if key.startswith("budget_total_spent:")
    )
    assert category_spent == expected
    assert total_spent == expected


@pytest.mark.asyncio
async def test_import_retries_do_not_duplicate_bills_balances_or_budget(import_context):
    context = import_context
    payload = {"ledger_id": 1, "items": [item(), item(1, type="income", amount=50)]}
    first = await context.client.post("/bills/import", json=payload)
    assert first.status_code == 200, first.text
    assert [row["created"] for row in first.json()["items"]] == [True, True]
    assert await bill_count(context) == 2
    assert await balance(context) == Decimal("130.00")
    assert await balance(context, 2) == Decimal("300.00")
    assert_cached_spending(context.cache, 20)

    retry = await context.client.post("/bills/import", json=payload)
    assert retry.status_code == 200, retry.text
    assert [row["created"] for row in retry.json()["items"]] == [False, False]
    assert [row["bill_id"] for row in retry.json()["items"]] == [row["bill_id"] for row in first.json()["items"]]
    assert await bill_count(context) == 2
    assert await balance(context) == Decimal("130.00")
    assert_cached_spending(context.cache, 20)
    bills = (await context.db.execute(select(Bill))).scalars().all()
    assert all(not bill.ai_parsed for bill in bills)


@pytest.mark.asyncio
async def test_batch_mixes_existing_and_new_rows_in_request_order(import_context):
    context = import_context
    first = await context.client.post("/bills/import", json={"ledger_id": 1, "items": [item()]})
    assert first.status_code == 200, first.text
    response = await context.client.post("/bills/import", json={"ledger_id": 1, "items": [item(2, amount=3), item()]})
    assert response.status_code == 200, response.text
    assert [row["import_key"] for row in response.json()["items"]] == [item(2)["import_key"], item()["import_key"]]
    assert [row["created"] for row in response.json()["items"]] == [True, False]
    assert await balance(context) == Decimal("77.00")
    assert_cached_spending(context.cache, 23)


@pytest.mark.asyncio
@pytest.mark.parametrize("items", [[], [item()] * 2, [item(index) for index in range(101)], [item(), item(1, amount=-2)], [item(import_key=None)], [item(amount=0.001)]])
async def test_invalid_batch_is_rejected_without_saving_any_rows(import_context, items):
    context = import_context
    response = await context.client.post("/bills/import", json={"ledger_id": 1, "items": items})
    assert response.status_code == 422, response.text
    assert await bill_count(context) == 0
    assert await balance(context) == Decimal("100.00")
    assert context.cache.values == {}


@pytest.mark.asyncio
async def test_other_users_ledger_is_not_writable(import_context):
    context = import_context
    response = await context.client.post("/bills/import", json={"ledger_id": 2, "items": [item()]})
    assert response.status_code == 404, response.text
    assert await bill_count(context) == 0
    assert await balance(context, 2) == Decimal("300.00")


@pytest.mark.asyncio
async def test_reused_key_with_different_amount_rejects_entire_batch(import_context):
    context = import_context
    first = await context.client.post("/bills/import", json={"ledger_id": 1, "items": [item()]})
    assert first.status_code == 200, first.text
    response = await context.client.post("/bills/import", json={"ledger_id": 1, "items": [item(1), item(amount=21)]})
    assert response.status_code == 409, response.text
    assert await bill_count(context) == 1
    assert await balance(context) == Decimal("80.00")
    assert_cached_spending(context.cache, 20)


@pytest.mark.asyncio
async def test_failed_database_commit_does_not_change_budget_cache(import_context, monkeypatch):
    context = import_context

    async def fail_commit():
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(context.db, "commit", fail_commit)
    response = await context.client.post("/bills/import", json={"ledger_id": 1, "items": [item()]})
    assert response.status_code == 500
    assert await bill_count(context) == 0
    assert await balance(context) == Decimal("100.00")
    assert context.cache.values == {}


@pytest.mark.asyncio
async def test_budget_cache_failure_keeps_committed_batch_retryable(import_context):
    context = import_context
    context.cache.unavailable = True
    payload = {"ledger_id": 1, "items": [item()]}
    response = await context.client.post("/bills/import", json=payload)
    assert response.status_code == 200, response.text
    retry = await context.client.post("/bills/import", json=payload)
    assert retry.status_code == 200, retry.text
    assert retry.json()["items"][0]["created"] is False
    assert await bill_count(context) == 1
    assert await balance(context) == Decimal("80.00")


@pytest.mark.asyncio
async def test_one_hundred_rows_save_in_one_batch(import_context):
    context = import_context
    statements = []

    def track_query(_conn, _cursor, statement, _parameters, _query_context, _many):
        statements.append(statement)

    engine = context.db.bind.sync_engine
    event.listen(engine, "before_cursor_execute", track_query)
    response = await context.client.post("/bills/import", json={"ledger_id": 1, "items": [item(index, amount=0.01) for index in range(100)]})
    event.remove(engine, "before_cursor_execute", track_query)
    assert response.status_code == 200, response.text
    # Guard against accidentally restoring per-row selects/inserts/updates.
    assert len(statements) < 15
    assert len(response.json()["items"]) == 100
    assert await bill_count(context) == 100
    assert await balance(context) == Decimal("99.00")
    assert_cached_spending(context.cache, 1)


@pytest.mark.asyncio
async def test_five_thousand_rows_import_in_fifty_bounded_batches(import_context):
    context = import_context
    for batch in range(50):
        response = await context.client.post("/bills/import", json={
            "ledger_id": 1,
            "items": [item(index, amount=0.01) for index in range(batch * 100, (batch + 1) * 100)],
        })
        assert response.status_code == 200, response.text
        assert len(response.json()["items"]) == 100
    assert await bill_count(context) == 5000
    assert await balance(context) == Decimal("50.00")
    assert_cached_spending(context.cache, 50)


@pytest.mark.asyncio
async def test_missing_account_remains_unlinked_like_manual_bill(import_context):
    context = import_context
    response = await context.client.post("/bills/import", json={"ledger_id": 1, "items": [item(account="未创建的银行卡")]})
    assert response.status_code == 200, response.text
    assert await bill_count(context) == 1
    assert await balance(context) == Decimal("100.00")
    assert_cached_spending(context.cache, 20)


@pytest.mark.asyncio
async def test_account_aliases_follow_database_name_matching(import_context):
    context = import_context
    account = await context.db.get(Account, 1)
    account.name = "ICBC"
    await context.db.commit()
    response = await context.client.post("/bills/import", json={
        "ledger_id": 1,
        "items": [item(account="icbc"), item(1, account="IcBc", type="income", amount=5)],
    })
    assert response.status_code == 200, response.text
    assert await bill_count(context) == 2
    assert await balance(context) == Decimal("85.00")
    assert await balance(context, 2) == Decimal("300.00")


@pytest.mark.asyncio
async def test_retry_reuses_current_read_ids_when_snapshot_is_older(import_context, monkeypatch):
    context = import_context
    first = await context.client.post("/bills/import", json={"ledger_id": 1, "items": [item()]})
    assert first.status_code == 200, first.text
    existing_id = first.json()["items"][0]["bill_id"]
    execute = context.db.execute

    async def execute_with_old_snapshot(statement, *args, **kwargs):
        # SQLite has no InnoDB current-read/snapshot-read distinction. Model
        # only that database boundary: locking reads see the earlier commit;
        # ordinary reads retain an older snapshot but see this batch's writes.
        if (
            isinstance(statement, Select)
            and statement._for_update_arg is None
            and any(table is Bill.__table__ for table in statement.get_final_froms())
        ):
            statement = statement.where(Bill.id != existing_id)
        return await execute(statement, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(context.db, "execute", execute_with_old_snapshot)
        response = await context.client.post("/bills/import", json={
            "ledger_id": 1, "items": [item(), item(1, amount=3)],
        })
    assert response.status_code == 200, response.text
    assert response.json()["items"][0] == {
        "import_key": item()["import_key"], "bill_id": existing_id, "created": False,
    }
    assert response.json()["items"][1]["created"] is True
    assert await bill_count(context) == 2
    assert await balance(context) == Decimal("77.00")

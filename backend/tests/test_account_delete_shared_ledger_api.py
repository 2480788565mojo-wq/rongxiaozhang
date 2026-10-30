"""Bug I2 回归：通过真实 HTTP 路由验证删除账号不会毁掉共享账本。

`DELETE /auth/me` 必须拦截「共享账本创建者且仍有其他成员」的账号注销，
返回 400 且不产生任何级联删除；只有创建者的共享账本则可以正常注销并
级联清理。测试经 ASGI 传输层发起请求，覆盖路由、依赖注入与响应序列化。
"""

from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import event, func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.api.v1.auth as auth_api
from app.core.database import get_db
from app.core.redis import get_redis
from app.core.security import get_current_user
from app.models import (
    Account,
    Base,
    Bill,
    BillShare,
    BillType,
    Budget,
    Category,
    CategoryType,
    ChatHistory,
    ChatRole,
    Insight,
    Ledger,
    LedgerMember,
    LedgerRole,
    LedgerType,
    ReportType,
    User,
)

auth_api.require_rate_limits = AsyncMock()

BLOCKED_DETAIL = "你仍是共享账本创建者，请先转移所有权或移除其他成员后再删除账号"


@pytest.fixture
async def api():
    """真实 auth 路由 + 内存 SQLite（显式开启外键，等价生产级联语义）。"""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
    )

    @event.listens_for(engine.sync_engine, "connect")
    def _enable_foreign_keys(dbapi_connection, _record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session = async_sessionmaker(engine, expire_on_commit=False)()
    actor = SimpleNamespace(user=None)

    async def database():
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

    application = FastAPI()
    application.include_router(auth_api.router, prefix="/auth")
    application.dependency_overrides[get_db] = database
    application.dependency_overrides[get_current_user] = lambda: actor.user
    application.dependency_overrides[get_redis] = lambda: AsyncMock()

    transport = httpx.ASGITransport(app=application, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield SimpleNamespace(client=client, db=session, actor=actor)

    await session.close()
    await engine.dispose()


async def _user(db, name: str) -> User:
    user = User(openid=f"i2-{name}", nickname=name)
    db.add(user)
    await db.flush()
    return user


async def _ledger(
    db,
    owner: User,
    name: str,
    *,
    ledger_type: LedgerType = LedgerType.PERSONAL,
    members: tuple[User, ...] = (),
    invite_code: str | None = None,
) -> Ledger:
    ledger = Ledger(
        name=name,
        type=ledger_type,
        owner_id=owner.id,
        invite_code=invite_code,
    )
    db.add(ledger)
    await db.flush()
    db.add(LedgerMember(ledger_id=ledger.id, user_id=owner.id, role=LedgerRole.OWNER))
    for member in members:
        db.add(
            LedgerMember(ledger_id=ledger.id, user_id=member.id, role=LedgerRole.MEMBER)
        )
    await db.flush()
    return ledger


async def _bill(db, ledger: Ledger, creator: User, note: str) -> Bill:
    bill = Bill(
        ledger_id=ledger.id,
        creator_id=creator.id,
        type=BillType.EXPENSE,
        amount=10,
        category="餐饮美食",
        note=note,
        bill_date=date(2026, 10, 1),
    )
    db.add(bill)
    await db.flush()
    return bill


async def _account(db, user: User, ledger: Ledger, name: str) -> Account:
    account = Account(
        user_id=user.id, ledger_id=ledger.id, name=name, type="现金", balance=0
    )
    db.add(account)
    await db.flush()
    return account


async def _budget(db, user: User, ledger: Ledger) -> Budget:
    budget = Budget(
        user_id=user.id,
        ledger_id=ledger.id,
        year=2026,
        month=10,
        total_budget=1000,
        category_budgets={"餐饮美食": 300},
    )
    db.add(budget)
    await db.flush()
    return budget


async def _category(db, user: User, ledger: Ledger, name: str) -> Category:
    category = Category(
        user_id=user.id,
        ledger_id=ledger.id,
        type=CategoryType.EXPENSE,
        parent_name="餐饮美食",
        name=name,
    )
    db.add(category)
    await db.flush()
    return category


async def _insight(db, user: User, ledger: Ledger) -> Insight:
    insight = Insight(
        user_id=user.id,
        ledger_id=ledger.id,
        report_type=ReportType.MONTHLY,
        content="本月餐饮支出偏高",
    )
    db.add(insight)
    await db.flush()
    return insight


async def _chat(db, user: User, ledger: Ledger) -> ChatHistory:
    chat = ChatHistory(
        user_id=user.id,
        ledger_id=ledger.id,
        session_id=f"i2-session-{user.id}",
        role=ChatRole.USER,
        content="这个月花了多少？",
    )
    db.add(chat)
    await db.flush()
    return chat


async def _count(db, model) -> int:
    return (
        await db.execute(select(func.count()).select_from(model))
    ).scalar_one()


async def test_shared_ledger_owner_with_second_member_is_blocked_via_api(api):
    db = api.db
    alice = await _user(db, "alice")
    bob = await _user(db, "bob")
    alice.default_ledger_id = None

    personal = await _ledger(db, alice, "Alice 的账本")
    shared = await _ledger(
        db,
        alice,
        "Alice 创建的共享账本",
        ledger_type=LedgerType.SHARED,
        members=(bob,),
        invite_code="I2-INVITE",
    )
    alice.default_ledger_id = personal.id

    bills = [
        await _bill(db, personal, alice, "个人账单"),
        await _bill(db, shared, alice, "Alice 共享账单"),
        await _bill(db, shared, bob, "Bob 共享账单"),
    ]
    accounts = [
        await _account(db, alice, personal, "Alice 个人现金"),
        await _account(db, alice, shared, "Alice 共享现金"),
        await _account(db, bob, shared, "Bob 共享现金"),
    ]
    budgets = [
        await _budget(db, alice, personal),
        await _budget(db, alice, shared),
        await _budget(db, bob, shared),
    ]
    categories = [
        await _category(db, alice, personal, "个人午餐"),
        await _category(db, alice, shared, "Alice 共享午餐"),
        await _category(db, bob, shared, "Bob 共享晚餐"),
    ]
    insights = [
        await _insight(db, alice, personal),
        await _insight(db, bob, shared),
    ]
    chats = [
        await _chat(db, alice, personal),
        await _chat(db, bob, shared),
    ]
    shares = [
        BillShare(bill_id=bills[1].id, user_id=bob.id, share_amount=5),
        BillShare(bill_id=bills[2].id, user_id=alice.id, share_amount=5),
    ]
    db.add_all(shares)
    await db.commit()

    expected = {
        "user": {alice.id, bob.id},
        "ledger": {personal.id, shared.id},
        "bill": {row.id for row in bills},
        "account": {row.id for row in accounts},
        "budget": {row.id for row in budgets},
        "category": {row.id for row in categories},
        "insight": {row.id for row in insights},
        "chat": {row.id for row in chats},
    }
    alice_id, shared_id, personal_id = alice.id, shared.id, personal.id

    api.actor.user = alice
    response = await api.client.delete("/auth/me")

    assert response.status_code == 400, response.text
    assert response.json() == {"detail": BLOCKED_DETAIL}

    # 账号本身、共享账本与两名成员的全部数据均保持原样。
    alice_after = await db.get(User, alice_id)
    assert alice_after is not None
    assert alice_after.openid == "i2-alice"
    assert alice_after.default_ledger_id == personal_id
    assert await _count(db, User) == 2

    shared_after = await db.get(Ledger, shared_id)
    assert shared_after is not None
    assert shared_after.owner_id == alice_id
    assert shared_after.type == LedgerType.SHARED
    assert await _count(db, Ledger) == 2

    for bill_id in expected["bill"]:
        assert await db.get(Bill, bill_id) is not None
    for account_id in expected["account"]:
        assert await db.get(Account, account_id) is not None
    for budget_id in expected["budget"]:
        assert await db.get(Budget, budget_id) is not None
    for category_id in expected["category"]:
        assert await db.get(Category, category_id) is not None
    for insight_id in expected["insight"]:
        assert await db.get(Insight, insight_id) is not None
    for chat_id in expected["chat"]:
        assert await db.get(ChatHistory, chat_id) is not None
    assert await _count(db, Bill) == 3
    assert await _count(db, Account) == 3
    assert await _count(db, Budget) == 3
    assert await _count(db, Category) == 3
    assert await _count(db, Insight) == 2
    assert await _count(db, ChatHistory) == 2
    assert await _count(db, BillShare) == 2

    member_ids = set(
        (
            await db.execute(
                select(LedgerMember.user_id).where(LedgerMember.ledger_id == shared_id)
            )
        ).scalars().all()
    )
    assert member_ids == expected["user"]
    assert await _count(db, LedgerMember) == 3


async def test_shared_ledger_with_only_owner_deletes_204_and_cascades_clean(api):
    db = api.db
    alice = await _user(db, "alice")
    personal = await _ledger(db, alice, "Alice 的账本")
    shared = await _ledger(
        db,
        alice,
        "只有创建者的共享账本",
        ledger_type=LedgerType.SHARED,
        invite_code="I2-ONLY-OWNER",
    )
    alice.default_ledger_id = shared.id

    bills = [
        await _bill(db, personal, alice, "个人账单"),
        await _bill(db, shared, alice, "共享账单"),
    ]
    accounts = [
        await _account(db, alice, personal, "个人现金"),
        await _account(db, alice, shared, "共享现金"),
    ]
    budgets = [
        await _budget(db, alice, personal),
        await _budget(db, alice, shared),
    ]
    categories = [
        await _category(db, alice, personal, "个人午餐"),
        await _category(db, alice, shared, "共享午餐"),
    ]
    insights = [
        await _insight(db, alice, personal),
        await _insight(db, alice, shared),
    ]
    chats = [
        await _chat(db, alice, personal),
        await _chat(db, alice, shared),
    ]
    db.add(BillShare(bill_id=bills[1].id, user_id=alice.id, share_amount=5))
    await db.commit()

    alice_id = alice.id
    ledger_ids = {personal.id, shared.id}

    api.actor.user = alice
    response = await api.client.delete("/auth/me")

    assert response.status_code == 204, response.text
    assert response.content in (b"", None)

    assert await db.get(User, alice_id) is None
    for ledger_id in ledger_ids:
        assert await db.get(Ledger, ledger_id) is None
    for model in (
        Ledger,
        LedgerMember,
        Bill,
        BillShare,
        Account,
        Budget,
        Category,
        Insight,
        ChatHistory,
        User,
    ):
        assert await _count(db, model) == 0, model.__name__

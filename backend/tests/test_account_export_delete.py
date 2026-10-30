"""账号数据导出 / 永久删除账号回归测试。

测试使用 SQLite 内存库，并显式打开 ``PRAGMA foreign_keys=ON``，
以复现生产 MySQL 的外键级联语义（账本删除时级联账单、成员等）。
"""

from datetime import date
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from sqlalchemy import event, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.api.v1.auth as auth_api
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

_REDIS = AsyncMock()
auth_api.require_rate_limits = AsyncMock()


@pytest.fixture
async def fk_db_session():
    """内存 SQLite + 外键约束，等价于生产 MySQL 的级联行为。"""
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
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        assert (await session.execute(text("PRAGMA foreign_keys"))).scalar() == 1
        yield session
        await session.rollback()
    await engine.dispose()


async def _user(db, name: str) -> User:
    user = User(openid=f"openid-{name}", nickname=name)
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
            LedgerMember(
                ledger_id=ledger.id,
                user_id=member.id,
                role=LedgerRole.MEMBER,
            )
        )
    await db.flush()
    return ledger


async def _bill(
    db,
    ledger: Ledger,
    creator: User,
    *,
    amount: int = 10,
    note: str = "午饭",
) -> Bill:
    bill = Bill(
        ledger_id=ledger.id,
        creator_id=creator.id,
        type=BillType.EXPENSE,
        amount=amount,
        category="餐饮美食",
        note=note,
        bill_date=date(2026, 10, 1),
    )
    db.add(bill)
    await db.flush()
    return bill


async def _account(db, user: User, ledger: Ledger, name: str) -> Account:
    account = Account(
        user_id=user.id,
        ledger_id=ledger.id,
        name=name,
        type="现金",
        balance=0,
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
        session_id=f"session-{user.id}",
        role=ChatRole.USER,
        content="这个月花了多少？",
    )
    db.add(chat)
    await db.flush()
    return chat


async def _count(db, model, *conditions) -> int:
    await db.flush()
    query = select(model)
    for condition in conditions:
        query = query.where(condition)
    return len((await db.execute(query)).scalars().all())


async def test_export_contains_own_data_and_excludes_other_users_private_data(
    fk_db_session,
):
    db = fk_db_session
    alice = await _user(db, "alice")
    bob = await _user(db, "bob")

    alice_ledger = await _ledger(db, alice, "Alice 的账本")
    bob_ledger = await _ledger(db, bob, "Bob 的账本")
    alice_bill = await _bill(db, alice_ledger, alice, note="Alice 的午饭")
    bob_bill = await _bill(db, bob_ledger, bob, note="Bob 的午饭")
    alice_account = await _account(db, alice, alice_ledger, "Alice 现金")
    bob_account = await _account(db, bob, bob_ledger, "Bob 现金")
    alice_budget = await _budget(db, alice, alice_ledger)
    bob_budget = await _budget(db, bob, bob_ledger)
    alice_category = await _category(db, alice, alice_ledger, "午餐")
    bob_category = await _category(db, bob, bob_ledger, "午餐")
    alice_insight = await _insight(db, alice, alice_ledger)
    bob_insight = await _insight(db, bob, bob_ledger)
    alice_chat = await _chat(db, alice, alice_ledger)
    bob_chat = await _chat(db, bob, bob_ledger)

    payload = await auth_api.export_me(alice, db, _REDIS)

    assert set(payload) == {
        "exported_at",
        "truncated",
        "user",
        "ledgers",
        "bills",
        "accounts",
        "budgets",
        "categories",
        "insights",
        "chats",
    }
    assert payload["truncated"] is False
    assert payload["user"]["id"] == alice.id
    assert payload["user"]["nickname"] == "alice"
    assert [item["id"] for item in payload["ledgers"]] == [alice_ledger.id]
    assert [item["id"] for item in payload["bills"]] == [alice_bill.id]
    assert [item["id"] for item in payload["accounts"]] == [alice_account.id]
    assert [item["id"] for item in payload["budgets"]] == [alice_budget.id]
    assert [item["id"] for item in payload["categories"]] == [alice_category.id]
    assert [item["id"] for item in payload["insights"]] == [alice_insight.id]
    assert [item["id"] for item in payload["chats"]] == [alice_chat.id]

    exported_ids = {
        "ledgers": {item["id"] for item in payload["ledgers"]},
        "bills": {item["id"] for item in payload["bills"]},
        "accounts": {item["id"] for item in payload["accounts"]},
        "budgets": {item["id"] for item in payload["budgets"]},
        "categories": {item["id"] for item in payload["categories"]},
        "insights": {item["id"] for item in payload["insights"]},
        "chats": {item["id"] for item in payload["chats"]},
    }
    assert bob_ledger.id not in exported_ids["ledgers"]
    assert bob_bill.id not in exported_ids["bills"]
    assert bob_account.id not in exported_ids["accounts"]
    assert bob_budget.id not in exported_ids["budgets"]
    assert bob_category.id not in exported_ids["categories"]
    assert bob_insight.id not in exported_ids["insights"]
    assert bob_chat.id not in exported_ids["chats"]


async def test_export_caps_bills_and_marks_truncated(fk_db_session, monkeypatch):
    db = fk_db_session
    alice = await _user(db, "alice")
    ledger = await _ledger(db, alice, "Alice 的账本")
    await _bill(db, ledger, alice, amount=1, note="第一笔")
    await _bill(db, ledger, alice, amount=2, note="第二笔")
    await db.flush()
    monkeypatch.setattr(auth_api, "EXPORT_BILL_LIMIT", 1)

    payload = await auth_api.export_me(alice, db, _REDIS)

    assert payload["truncated"] is True
    assert len(payload["bills"]) == 1


async def test_delete_account_removes_own_data_and_returns_204(fk_db_session):
    db = fk_db_session
    alice = await _user(db, "alice")
    bob = await _user(db, "bob")
    alice_ledger = await _ledger(db, alice, "Alice 的账本")
    bob_ledger = await _ledger(db, bob, "Bob 的账本")
    alice_bill = await _bill(db, alice_ledger, alice)
    bob_bill = await _bill(db, bob_ledger, bob)
    alice_share = BillShare(
        bill_id=alice_bill.id, user_id=alice.id, share_amount=5, settled=True
    )
    bob_share = BillShare(
        bill_id=bob_bill.id, user_id=bob.id, share_amount=5, settled=True
    )
    db.add_all([alice_share, bob_share])
    alice_account = await _account(db, alice, alice_ledger, "Alice 现金")
    bob_account = await _account(db, bob, bob_ledger, "Bob 现金")
    alice_budget = await _budget(db, alice, alice_ledger)
    bob_budget = await _budget(db, bob, bob_ledger)
    alice_category = await _category(db, alice, alice_ledger, "午餐")
    bob_category = await _category(db, bob, bob_ledger, "午餐")
    alice_insight = await _insight(db, alice, alice_ledger)
    bob_insight = await _insight(db, bob, bob_ledger)
    alice_chat = await _chat(db, alice, alice_ledger)
    bob_chat = await _chat(db, bob, bob_ledger)
    await db.flush()

    alice_id = alice.id
    alice_ledger_id = alice_ledger.id
    alice_bill_id = alice_bill.id
    alice_account_id = alice_account.id
    alice_budget_id = alice_budget.id
    alice_category_id = alice_category.id
    alice_insight_id = alice_insight.id
    alice_chat_id = alice_chat.id

    response = await auth_api.delete_me(alice, db, _REDIS)

    assert response.status_code == 204
    assert response.body in (b"", None)
    assert await db.get(User, alice_id) is None
    assert await db.get(Ledger, alice_ledger_id) is None
    assert await db.get(Bill, alice_bill_id) is None
    assert await db.get(Account, alice_account_id) is None
    assert await db.get(Budget, alice_budget_id) is None
    assert await db.get(Category, alice_category_id) is None
    assert await db.get(Insight, alice_insight_id) is None
    assert await db.get(ChatHistory, alice_chat_id) is None
    assert await _count(db, LedgerMember, LedgerMember.user_id == alice_id) == 0
    assert await _count(db, BillShare, BillShare.user_id == alice_id) == 0

    # 另一个用户及其全部数据不受影响。
    assert await db.get(User, bob.id) is not None
    assert await db.get(Ledger, bob_ledger.id) is not None
    assert await db.get(Bill, bob_bill.id) is not None
    assert await db.get(Account, bob_account.id) is not None
    assert await db.get(Budget, bob_budget.id) is not None
    assert await db.get(Category, bob_category.id) is not None
    assert await db.get(Insight, bob_insight.id) is not None
    assert await db.get(ChatHistory, bob_chat.id) is not None
    assert await _count(db, BillShare, BillShare.user_id == bob.id) == 1
    assert await _count(db, LedgerMember, LedgerMember.user_id == bob.id) == 1


async def test_delete_account_blocked_by_unsettled_share(fk_db_session):
    db = fk_db_session
    alice = await _user(db, "alice")
    bob = await _user(db, "bob")
    shared = await _ledger(
        db,
        alice,
        "共享账本",
        ledger_type=LedgerType.SHARED,
        members=(bob,),
        invite_code="INVITE-DEBT",
    )
    bill = await _bill(db, shared, alice, amount=20)
    share = BillShare(
        bill_id=bill.id,
        user_id=bob.id,
        share_amount=10,
        settled=False,
    )
    db.add(share)
    await db.flush()
    bob_id = bob.id
    share_id = share.id

    with pytest.raises(HTTPException) as blocked:
        await auth_api.delete_me(bob, db, _REDIS)

    assert blocked.value.status_code == 400
    assert "未结算" in blocked.value.detail
    assert await db.get(User, bob_id) is not None
    assert await db.get(BillShare, share_id) is not None

    share.settled = True
    await db.flush()
    response = await auth_api.delete_me(bob, db, _REDIS)
    assert response.status_code == 204
    assert await db.get(User, bob_id) is None


async def test_member_deleted_from_shared_ledger_owner_and_ledger_remain(
    fk_db_session,
):
    db = fk_db_session
    alice = await _user(db, "alice")
    bob = await _user(db, "bob")
    shared = await _ledger(
        db,
        alice,
        "共享账本",
        ledger_type=LedgerType.SHARED,
        members=(bob,),
        invite_code="INVITE-ABC",
    )
    alice_bill = await _bill(db, shared, alice, note="Alice 的账单")
    bob_bill = await _bill(db, shared, bob, note="Bob 的账单")

    response = await auth_api.delete_me(bob, db, _REDIS)

    assert response.status_code == 204
    assert await db.get(User, bob.id) is None
    # 账本属于 Alice，不能被 B 的注销带走。
    assert await db.get(Ledger, shared.id) is not None
    assert await db.get(Bill, alice_bill.id) is not None
    assert await db.get(Bill, bob_bill.id) is None
    assert await _count(db, LedgerMember, LedgerMember.ledger_id == shared.id) == 1
    assert (
        await db.scalar(
            select(LedgerMember.user_id).where(
                LedgerMember.ledger_id == shared.id,
            )
        )
        == alice.id
    )


async def test_owner_deletion_of_shared_ledger_with_other_member_is_blocked(
    fk_db_session,
):
    db = fk_db_session
    alice = await _user(db, "alice")
    bob = await _user(db, "bob")
    shared = await _ledger(
        db,
        alice,
        "Alice 创建的共享账本",
        ledger_type=LedgerType.SHARED,
        members=(bob,),
        invite_code="INVITE-XYZ",
    )
    alice_bill = await _bill(db, shared, alice)
    bob_bill = await _bill(db, shared, bob)
    bob_account = await _account(db, bob, shared, "Bob 的共享账户")
    bob_budget = await _budget(db, bob, shared)
    bob_category = await _category(db, bob, shared, "晚餐")
    await db.flush()

    with pytest.raises(HTTPException) as blocked:
        await auth_api.delete_me(alice, db, _REDIS)

    assert blocked.value.status_code == 400
    assert "转移" in blocked.value.detail
    # 其他成员还在时，账号和账本数据都不能被级联删除。
    assert await db.get(User, alice.id) is not None
    assert await db.get(Ledger, shared.id) is not None
    assert await db.get(Bill, alice_bill.id) is not None
    assert await db.get(Bill, bob_bill.id) is not None
    assert await db.get(Account, bob_account.id) is not None
    assert await db.get(Budget, bob_budget.id) is not None
    assert await db.get(Category, bob_category.id) is not None
    assert await _count(db, LedgerMember, LedgerMember.ledger_id == shared.id) == 2


async def test_owner_deletion_of_shared_ledger_without_other_members_succeeds(
    fk_db_session,
):
    db = fk_db_session
    alice = await _user(db, "alice")
    shared = await _ledger(
        db,
        alice,
        "只有 Alice 的共享账本",
        ledger_type=LedgerType.SHARED,
        invite_code="INVITE-ONLY",
    )
    bill = await _bill(db, shared, alice)
    await db.flush()

    shared_id = shared.id
    bill_id = bill.id

    response = await auth_api.delete_me(alice, db, _REDIS)

    assert response.status_code == 204
    db.expire_all()
    assert await db.get(Ledger, shared_id) is None
    assert await db.get(Bill, bill_id) is None
    assert await _count(db, LedgerMember, LedgerMember.ledger_id == shared_id) == 0

"""账本成员管理回归测试。

覆盖移除成员与设置管理员的权限矩阵：
- 创建者：可移除普通成员/管理员、可调整角色，不能移除自己或修改创建者角色；
- 管理员：只能移除普通成员，不能移除管理员或调整角色；
- 普通成员/非成员：一律拒绝。
以及 API 层 403/400 映射与返回 LedgerOut 的形态。
"""

from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import select

import app.api.v1.ledgers as ledgers_api
from app.models import (
    Bill,
    BillShare,
    BillType,
    Ledger,
    LedgerMember,
    LedgerRole,
    LedgerType,
    User,
)
from app.schemas.ledger import MemberRoleUpdate
from app.services.ledger_service import remove_ledger_member, set_member_role


_REDIS = AsyncMock()


async def _users(db, *names: str) -> list[User]:
    users = [User(openid=f"member-{name}", nickname=name) for name in names]
    db.add_all(users)
    await db.flush()
    return users


async def _shared_ledger(
    db,
    owner: User,
    *members: tuple[User, LedgerRole],
) -> Ledger:
    ledger = Ledger(
        name="成员测试账本",
        type=LedgerType.SHARED,
        owner_id=owner.id,
        invite_code=f"members-{owner.id}",
    )
    db.add(ledger)
    await db.flush()
    db.add(
        LedgerMember(
            ledger_id=ledger.id,
            user_id=owner.id,
            role=LedgerRole.OWNER,
        )
    )
    for user, role in members:
        db.add(LedgerMember(ledger_id=ledger.id, user_id=user.id, role=role))
    await db.flush()
    return ledger


async def _role_of(db, ledger: Ledger, user: User) -> LedgerRole | None:
    await db.flush()
    return await db.scalar(
        select(LedgerMember.role).where(
            LedgerMember.ledger_id == ledger.id,
            LedgerMember.user_id == user.id,
        )
    )


async def _member_ids(db, ledger: Ledger) -> set[int]:
    await db.flush()
    rows = await db.scalars(
        select(LedgerMember.user_id).where(LedgerMember.ledger_id == ledger.id)
    )
    return set(rows.all())


def _user(user: User) -> SimpleNamespace:
    return SimpleNamespace(id=user.id)


async def test_member_who_created_unsettled_bill_cannot_be_removed(db_session):
    owner, member = await _users(db_session, "owner", "creditor")
    ledger = await _shared_ledger(db_session, owner, (member, LedgerRole.MEMBER))
    bill = Bill(
        ledger_id=ledger.id,
        creator_id=member.id,
        type=BillType.EXPENSE,
        amount=Decimal("20.00"),
        category="餐饮",
        bill_date=date(2026, 10, 29),
    )
    db_session.add(bill)
    await db_session.flush()
    db_session.add(
        BillShare(
            bill_id=bill.id,
            user_id=owner.id,
            share_amount=Decimal("10.00"),
            settled=False,
        )
    )
    await db_session.flush()

    # 成员是创建者，别人还欠他；移除后这笔债权会变成“非成员债权”。
    with pytest.raises(ValueError, match="未结算"):
        await remove_ledger_member(db_session, ledger.id, owner.id, member.id)

    assert await _role_of(db_session, ledger, member) == LedgerRole.MEMBER


async def test_member_with_unsettled_share_cannot_be_removed(db_session):
    owner, member = await _users(db_session, "owner", "debtor")
    ledger = await _shared_ledger(db_session, owner, (member, LedgerRole.MEMBER))
    bill = Bill(
        ledger_id=ledger.id,
        creator_id=owner.id,
        type=BillType.EXPENSE,
        amount=Decimal("20.00"),
        category="餐饮",
        bill_date=date(2026, 10, 29),
    )
    db_session.add(bill)
    await db_session.flush()
    share = BillShare(
        bill_id=bill.id,
        user_id=member.id,
        share_amount=Decimal("10.00"),
        settled=False,
    )
    db_session.add(share)
    await db_session.flush()

    with pytest.raises(ValueError, match="未结算"):
        await remove_ledger_member(db_session, ledger.id, owner.id, member.id)

    assert await _role_of(db_session, ledger, member) == LedgerRole.MEMBER

    # 结算后允许移除，避免把“有债务”误判成永久不可移除。
    share.settled = True
    await db_session.flush()
    await remove_ledger_member(db_session, ledger.id, owner.id, member.id)
    assert await _role_of(db_session, ledger, member) is None


async def test_owner_removes_plain_member_and_member_row_is_gone(db_session):
    owner, member, other = await _users(db_session, "owner", "member", "other")
    ledger = await _shared_ledger(
        db_session,
        owner,
        (member, LedgerRole.MEMBER),
        (other, LedgerRole.MEMBER),
    )

    await remove_ledger_member(db_session, ledger.id, owner.id, member.id)

    assert await _role_of(db_session, ledger, member) is None
    assert await _member_ids(db_session, ledger) == {owner.id, other.id}


async def test_owner_cannot_remove_self(db_session):
    owner, member = await _users(db_session, "owner", "member")
    ledger = await _shared_ledger(db_session, owner, (member, LedgerRole.MEMBER))

    with pytest.raises(ValueError, match="不能移除自己"):
        await remove_ledger_member(db_session, ledger.id, owner.id, owner.id)

    assert await _member_ids(db_session, ledger) == {owner.id, member.id}


async def test_owner_role_cannot_be_removed_even_by_admin(db_session):
    owner, admin, member = await _users(db_session, "owner", "admin", "member")
    ledger = await _shared_ledger(
        db_session,
        owner,
        (admin, LedgerRole.ADMIN),
        (member, LedgerRole.MEMBER),
    )

    with pytest.raises(ValueError, match="不能移除账本创建者"):
        await remove_ledger_member(db_session, ledger.id, admin.id, owner.id)

    assert await _role_of(db_session, ledger, owner) == LedgerRole.OWNER


async def test_admin_removes_plain_member_but_not_another_admin(db_session):
    owner, admin_a, admin_b, member = await _users(
        db_session, "owner", "admin-a", "admin-b", "member"
    )
    ledger = await _shared_ledger(
        db_session,
        owner,
        (admin_a, LedgerRole.ADMIN),
        (admin_b, LedgerRole.ADMIN),
        (member, LedgerRole.MEMBER),
    )

    await remove_ledger_member(db_session, ledger.id, admin_a.id, member.id)
    assert await _role_of(db_session, ledger, member) is None

    with pytest.raises(PermissionError, match="管理员不能移除其他管理员"):
        await remove_ledger_member(db_session, ledger.id, admin_a.id, admin_b.id)
    assert await _role_of(db_session, ledger, admin_b) == LedgerRole.ADMIN


async def test_admin_cannot_change_roles(db_session):
    owner, admin_a, admin_b, member = await _users(
        db_session, "owner", "admin-a", "admin-b", "member"
    )
    ledger = await _shared_ledger(
        db_session,
        owner,
        (admin_a, LedgerRole.ADMIN),
        (admin_b, LedgerRole.ADMIN),
        (member, LedgerRole.MEMBER),
    )

    with pytest.raises(PermissionError, match="只有账本创建者"):
        await set_member_role(db_session, ledger.id, admin_a.id, member.id, LedgerRole.ADMIN)
    with pytest.raises(PermissionError, match="只有账本创建者"):
        await set_member_role(db_session, ledger.id, admin_a.id, admin_b.id, LedgerRole.MEMBER)

    assert await _role_of(db_session, ledger, member) == LedgerRole.MEMBER
    assert await _role_of(db_session, ledger, admin_b) == LedgerRole.ADMIN


async def test_owner_promotes_member_and_demotes_admin(db_session):
    owner, member, admin = await _users(db_session, "owner", "member", "admin")
    ledger = await _shared_ledger(
        db_session,
        owner,
        (member, LedgerRole.MEMBER),
        (admin, LedgerRole.ADMIN),
    )

    await set_member_role(db_session, ledger.id, owner.id, member.id, LedgerRole.ADMIN)
    assert await _role_of(db_session, ledger, member) == LedgerRole.ADMIN

    await set_member_role(db_session, ledger.id, owner.id, admin.id, LedgerRole.MEMBER)
    assert await _role_of(db_session, ledger, admin) == LedgerRole.MEMBER


async def test_owner_cannot_change_own_role(db_session):
    owner, member = await _users(db_session, "owner", "member")
    ledger = await _shared_ledger(db_session, owner, (member, LedgerRole.MEMBER))

    with pytest.raises(ValueError, match="不能修改账本创建者的角色"):
        await set_member_role(db_session, ledger.id, owner.id, owner.id, LedgerRole.ADMIN)

    assert await _role_of(db_session, ledger, owner) == LedgerRole.OWNER


async def test_plain_member_and_outsider_cannot_remove_or_update(db_session):
    owner, actor, target, outsider = await _users(
        db_session, "owner", "actor", "target", "outsider"
    )
    ledger = await _shared_ledger(
        db_session,
        owner,
        (actor, LedgerRole.MEMBER),
        (target, LedgerRole.MEMBER),
    )

    for actor_id in (actor.id, outsider.id):
        with pytest.raises(PermissionError):
            await remove_ledger_member(db_session, ledger.id, actor_id, target.id)
        with pytest.raises(PermissionError):
            await set_member_role(db_session, ledger.id, actor_id, target.id, LedgerRole.ADMIN)

    assert await _member_ids(db_session, ledger) == {owner.id, actor.id, target.id}
    assert await _role_of(db_session, ledger, target) == LedgerRole.MEMBER


async def test_unknown_target_member_is_invalid(db_session):
    owner, stranger = await _users(db_session, "owner", "stranger")
    ledger = await _shared_ledger(db_session, owner)

    with pytest.raises(ValueError, match="不是账本成员"):
        await remove_ledger_member(db_session, ledger.id, owner.id, stranger.id)
    with pytest.raises(ValueError, match="不是账本成员"):
        await set_member_role(db_session, ledger.id, owner.id, stranger.id, LedgerRole.ADMIN)


async def test_api_remove_member_maps_permissions_and_returns_ledger_out(db_session):
    owner, member, outsider = await _users(db_session, "owner", "member", "outsider")
    ledger = await _shared_ledger(db_session, owner, (member, LedgerRole.MEMBER))

    output = await ledgers_api.remove_member(ledger.id, member.id, _user(owner), db_session, _REDIS)
    assert output.id == ledger.id
    assert output.member_count == 1
    assert [item.user_id for item in output.members] == [owner.id]
    # 创建者始终能拿到邀请码。
    assert output.invite_code == ledger.invite_code

    with pytest.raises(HTTPException) as forbidden:
        await ledgers_api.remove_member(ledger.id, owner.id, _user(outsider), db_session, _REDIS)
    assert forbidden.value.status_code == 403

    with pytest.raises(HTTPException) as invalid:
        await ledgers_api.remove_member(ledger.id, owner.id, _user(owner), db_session, _REDIS)
    assert invalid.value.status_code == 400
    assert "不能移除自己" in invalid.value.detail


async def test_api_remove_member_rejects_unsettled_share_until_settled(db_session):
    """API 层复现 Bug I1：未结算分摊必须先结算，否则 400 且成员保留。"""
    owner, member = await _users(db_session, "owner", "debtor")
    ledger = await _shared_ledger(db_session, owner, (member, LedgerRole.MEMBER))
    bill = Bill(
        ledger_id=ledger.id,
        creator_id=owner.id,
        type=BillType.EXPENSE,
        amount=Decimal("20.00"),
        category="餐饮",
        bill_date=date(2026, 10, 29),
    )
    db_session.add(bill)
    await db_session.flush()
    share = BillShare(
        bill_id=bill.id,
        user_id=member.id,
        share_amount=Decimal("10.00"),
        settled=False,
    )
    db_session.add(share)
    await db_session.flush()

    with pytest.raises(HTTPException) as blocked:
        await ledgers_api.remove_member(ledger.id, member.id, _user(owner), db_session, _REDIS)
    assert blocked.value.status_code == 400
    assert blocked.value.detail == "该成员还有未结算的分摊，请先完成结算再移除"
    # 拒绝时不能留下“成员已删、分摊未清”的坏状态。
    assert await _role_of(db_session, ledger, member) == LedgerRole.MEMBER

    share.settled = True
    share.settled_at = date(2026, 10, 29)
    await db_session.flush()

    output = await ledgers_api.remove_member(ledger.id, member.id, _user(owner), db_session, _REDIS)
    assert output.id == ledger.id
    assert output.member_count == 1
    assert [item.user_id for item in output.members] == [owner.id]
    assert await _role_of(db_session, ledger, member) is None


async def test_api_update_member_role_maps_permissions_and_updates_output(db_session):
    owner, admin, member, outsider = await _users(
        db_session, "owner", "admin", "member", "outsider"
    )
    ledger = await _shared_ledger(
        db_session,
        owner,
        (admin, LedgerRole.ADMIN),
        (member, LedgerRole.MEMBER),
    )

    with pytest.raises(HTTPException) as forbidden:
        await ledgers_api.update_member_role(
            ledger.id,
            member.id,
            MemberRoleUpdate(role="admin"),
            _user(admin),
            db_session,
            _REDIS,
        )
    assert forbidden.value.status_code == 403

    with pytest.raises(HTTPException) as invalid:
        await ledgers_api.update_member_role(
            ledger.id,
            owner.id,
            MemberRoleUpdate(role="admin"),
            _user(owner),
            db_session,
            _REDIS,
        )
    assert invalid.value.status_code == 400

    with pytest.raises(HTTPException) as outsider_error:
        await ledgers_api.update_member_role(
            ledger.id,
            member.id,
            MemberRoleUpdate(role="admin"),
            _user(outsider),
            db_session,
            _REDIS,
        )
    assert outsider_error.value.status_code == 403

    output = await ledgers_api.update_member_role(
        ledger.id,
        member.id,
        MemberRoleUpdate(role="admin"),
        _user(owner),
        db_session,
        _REDIS,
    )
    roles = {item.user_id: item.role for item in output.members}
    assert roles[member.id] == "admin"
    assert roles[owner.id] == "owner"


def test_member_role_update_schema_only_accepts_admin_or_member():
    assert MemberRoleUpdate(role="admin").role == "admin"
    assert MemberRoleUpdate(role="member").role == "member"
    with pytest.raises(ValidationError):
        MemberRoleUpdate(role="owner")
    with pytest.raises(ValidationError):
        MemberRoleUpdate(role="guest")

"""AA 结算确认回归测试。

覆盖“已结算”写入、结算计划清除、越权/伪造/过期请求拒绝，
以及链路抵消转账不能整笔标记的边界。
"""

from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

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
from app.schemas.ledger import SettlementConfirm, SettlementOut
from app.services.ledger_service import confirm_settlement, settle_ledger


async def _users(db, *names: str) -> list[User]:
    users = [User(openid=f"openid-{name}", nickname=name) for name in names]
    db.add_all(users)
    await db.flush()
    return users


async def _shared_ledger(db, owner: User, *members: User) -> Ledger:
    ledger = Ledger(
        name="旅行账本",
        type=LedgerType.SHARED,
        owner_id=owner.id,
        invite_code=f"code-{owner.id}",
    )
    db.add(ledger)
    await db.flush()
    for user in members:
        db.add(
            LedgerMember(
                ledger_id=ledger.id,
                user_id=user.id,
                role=(
                    LedgerRole.OWNER
                    if user.id == owner.id
                    else LedgerRole.MEMBER
                ),
            )
        )
    await db.flush()
    return ledger


async def _bill(
    db,
    ledger: Ledger,
    creator: User,
    shares: dict[User, float],
) -> tuple[Bill, list[BillShare]]:
    total = sum(shares.values())
    bill = Bill(
        ledger_id=ledger.id,
        creator_id=creator.id,
        type=BillType.EXPENSE,
        amount=Decimal(str(total)),
        category="餐饮",
        bill_date=date(2026, 10, 1),
    )
    db.add(bill)
    await db.flush()
    rows = []
    for user, amount in shares.items():
        row = BillShare(
            bill_id=bill.id,
            user_id=user.id,
            share_amount=Decimal(str(amount)),
        )
        db.add(row)
        rows.append(row)
    await db.flush()
    return bill, rows


async def test_direct_transfer_exposes_share_ids(db_session):
    a, b = await _users(db_session, "A", "B")
    ledger = await _shared_ledger(db_session, a, a, b)
    _, [share] = await _bill(db_session, ledger, a, {b: 60})

    transfers = await settle_ledger(db_session, ledger.id, a.id)

    assert len(transfers) == 1
    transfer = transfers[0]
    assert transfer["from_user_id"] == b.id
    assert transfer["to_user_id"] == a.id
    assert transfer["amount"] == pytest.approx(60.0)
    assert transfer["share_ids"] == [share.id]


async def test_payer_confirmation_marks_settled_and_clears_plan(db_session):
    a, b = await _users(db_session, "A", "B")
    ledger = await _shared_ledger(db_session, a, a, b)
    _, [share] = await _bill(db_session, ledger, a, {b: 60})

    remaining = await confirm_settlement(
        db_session,
        ledger.id,
        b.id,
        from_user_id=b.id,
        to_user_id=a.id,
        share_ids=[share.id],
    )

    assert remaining == []
    await db_session.refresh(share)
    assert share.settled is True
    assert share.settled_at == date.today()
    # 收款人 A 的视图也必须看不到这笔转账。
    assert await settle_ledger(db_session, ledger.id, a.id) == []


async def test_third_member_and_outsider_cannot_confirm(db_session):
    a, b, c, outsider = await _users(db_session, "A", "B", "C", "D")
    ledger = await _shared_ledger(db_session, a, a, b, c)
    _, [share] = await _bill(db_session, ledger, a, {b: 40})
    payload = dict(from_user_id=b.id, to_user_id=a.id, share_ids=[share.id])

    with pytest.raises(PermissionError):
        await confirm_settlement(db_session, ledger.id, c.id, **payload)
    with pytest.raises(PermissionError):
        await confirm_settlement(db_session, ledger.id, outsider.id, **payload)

    await db_session.refresh(share)
    assert share.settled is False
    assert share.settled_at is None


async def test_wrong_from_to_and_foreign_share_are_rejected(db_session):
    a, b, c = await _users(db_session, "A", "B", "C")
    ledger = await _shared_ledger(db_session, a, a, b, c)
    _, [share_b, share_c] = await _bill(db_session, ledger, a, {b: 30, c: 30})

    with pytest.raises(ValueError, match="不能相同"):
        await confirm_settlement(
            db_session,
            ledger.id,
            b.id,
            from_user_id=b.id,
            to_user_id=b.id,
            share_ids=[share_b.id],
        )
    # 反向 A→B 不存在，B 的分摊不能拿来确认。
    with pytest.raises(ValueError):
        await confirm_settlement(
            db_session,
            ledger.id,
            b.id,
            from_user_id=a.id,
            to_user_id=b.id,
            share_ids=[share_b.id],
        )
    # C 的分摊不属于“B 付给 A”这笔转账。
    with pytest.raises(ValueError, match="不存在或不属于"):
        await confirm_settlement(
            db_session,
            ledger.id,
            b.id,
            from_user_id=b.id,
            to_user_id=a.id,
            share_ids=[share_c.id],
        )

    for share in (share_b, share_c):
        await db_session.refresh(share)
        assert share.settled is False


async def test_already_settled_share_is_rejected(db_session):
    a, b = await _users(db_session, "A", "B")
    ledger = await _shared_ledger(db_session, a, a, b)
    _, [share] = await _bill(db_session, ledger, a, {b: 25})
    kwargs = dict(from_user_id=b.id, to_user_id=a.id, share_ids=[share.id])

    await confirm_settlement(db_session, ledger.id, b.id, **kwargs)
    with pytest.raises(ValueError, match="已经结算"):
        await confirm_settlement(db_session, ledger.id, b.id, **kwargs)


async def test_stale_amount_is_rejected_without_marking(db_session):
    a, b = await _users(db_session, "A", "B")
    ledger = await _shared_ledger(db_session, a, a, b)
    _, [share] = await _bill(db_session, ledger, a, {b: 60})
    # 结算方案生成后又新增一笔，旧 share_ids 对应的金额已过期。
    await _bill(db_session, ledger, a, {b: 40})

    with pytest.raises(ValueError, match="金额已变化"):
        await confirm_settlement(
            db_session,
            ledger.id,
            b.id,
            from_user_id=b.id,
            to_user_id=a.id,
            share_ids=[share.id],
        )

    await db_session.refresh(share)
    assert share.settled is False
    assert share.settled_at is None


async def test_partial_selection_of_multi_share_transfer_is_rejected(db_session):
    a, b = await _users(db_session, "A", "B")
    ledger = await _shared_ledger(db_session, a, a, b)
    _, [first] = await _bill(db_session, ledger, a, {b: 30})
    _, [second] = await _bill(db_session, ledger, a, {b: 20})

    transfers = await settle_ledger(db_session, ledger.id, a.id)
    assert transfers[0]["share_ids"] == [first.id, second.id]

    with pytest.raises(ValueError, match="金额已变化"):
        await confirm_settlement(
            db_session,
            ledger.id,
            b.id,
            from_user_id=b.id,
            to_user_id=a.id,
            share_ids=[first.id],
        )

    for share in (first, second):
        await db_session.refresh(share)
        assert share.settled is False


async def test_chain_transfer_has_empty_share_ids_and_cannot_be_marked(db_session):
    a, b, c = await _users(db_session, "A", "B", "C")
    ledger = await _shared_ledger(db_session, a, a, b, c)
    _, [share_b] = await _bill(db_session, ledger, a, {b: 50})
    _, [share_c] = await _bill(db_session, ledger, b, {c: 50})

    transfers = await settle_ledger(db_session, ledger.id, a.id)

    assert len(transfers) == 1
    assert transfers[0]["from_user_id"] == c.id
    assert transfers[0]["to_user_id"] == a.id
    assert transfers[0]["amount"] == pytest.approx(50.0)
    assert transfers[0]["share_ids"] == []

    # 服务层即使收到空列表也不能把链路转账标记掉。
    with pytest.raises(ValueError):
        await confirm_settlement(
            db_session,
            ledger.id,
            c.id,
            from_user_id=c.id,
            to_user_id=a.id,
            share_ids=[],
        )
    # 也不允许拿链路上任意真实分摊来冒充这笔转账。
    for share in (share_b, share_c):
        with pytest.raises(ValueError):
            await confirm_settlement(
                db_session,
                ledger.id,
                c.id,
                from_user_id=c.id,
                to_user_id=a.id,
                share_ids=[share.id],
            )

    for share in (share_b, share_c):
        await db_session.refresh(share)
        assert share.settled is False


def test_settlement_schemas_require_and_default_share_ids():
    with pytest.raises(ValidationError):
        SettlementConfirm(from_user_id=1, to_user_id=2, share_ids=[])
    output = SettlementOut(
        from_user_id=1,
        from_user_name="A",
        to_user_id=2,
        to_user_name="B",
        amount=1,
    )
    assert output.share_ids == []

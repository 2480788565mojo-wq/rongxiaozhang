from datetime import date
import secrets

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agents.social import minimize_debts
from app.models import (
    Bill,
    BillShare,
    Ledger,
    LedgerMember,
    LedgerRole,
    LedgerType,
    User,
)


async def list_user_ledgers(db: AsyncSession, user_id: int) -> list[Ledger]:
    result = await db.execute(
        select(Ledger)
        .join(LedgerMember, LedgerMember.ledger_id == Ledger.id)
        .options(
            selectinload(Ledger.members).selectinload(LedgerMember.user),
        )
        .where(LedgerMember.user_id == user_id)
        .order_by(Ledger.created_at.asc())
    )
    return list(result.scalars().unique().all())


async def get_ledger_detail(
    db: AsyncSession,
    ledger_id: int,
    user_id: int,
) -> Ledger | None:
    result = await db.execute(
        select(Ledger)
        .join(LedgerMember, LedgerMember.ledger_id == Ledger.id)
        .options(
            selectinload(Ledger.members).selectinload(LedgerMember.user),
        )
        .where(
            Ledger.id == ledger_id,
            LedgerMember.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def _new_invite_code(db: AsyncSession) -> str:
    for _ in range(5):
        code = secrets.token_urlsafe(6).replace("-", "").replace("_", "")[:8]
        exists = await db.scalar(select(Ledger.id).where(Ledger.invite_code == code))
        if exists is None:
            return code
    raise RuntimeError("暂时无法生成唯一邀请码")


async def create_ledger(
    db: AsyncSession,
    user: User,
    *,
    name: str,
    ledger_type: LedgerType,
) -> Ledger:
    invite_code = (
        await _new_invite_code(db) if ledger_type == LedgerType.SHARED else None
    )
    ledger = Ledger(
        name=name,
        type=ledger_type,
        owner_id=user.id,
        invite_code=invite_code,
    )
    db.add(ledger)
    await db.flush()
    member = LedgerMember(
        ledger_id=ledger.id,
        user_id=user.id,
        role=LedgerRole.OWNER,
    )
    db.add(member)
    await db.flush()
    return ledger


async def join_ledger(
    db: AsyncSession,
    ledger_id: int,
    user_id: int,
    invite_code: str,
) -> Ledger:
    result = await db.execute(
        select(Ledger).where(
            Ledger.id == ledger_id,
            Ledger.type == LedgerType.SHARED,
            Ledger.invite_code == invite_code,
        )
    )
    ledger = result.scalar_one_or_none()
    if ledger is None:
        raise ValueError("邀请码错误或账本不存在")

    existing = await db.get(LedgerMember, (ledger_id, user_id))
    if existing is None:
        db.add(
            LedgerMember(
                ledger_id=ledger_id,
                user_id=user_id,
                role=LedgerRole.MEMBER,
            )
        )
        await db.flush()
    return ledger


async def rotate_invite_code(
    db: AsyncSession,
    ledger_id: int,
    user_id: int,
) -> Ledger:
    result = await db.execute(
        select(Ledger)
        .join(LedgerMember, LedgerMember.ledger_id == Ledger.id)
        .where(
            Ledger.id == ledger_id,
            Ledger.type == LedgerType.SHARED,
            LedgerMember.user_id == user_id,
            LedgerMember.role.in_([LedgerRole.OWNER, LedgerRole.ADMIN]),
        )
        .with_for_update()
    )
    ledger = result.scalar_one_or_none()
    if ledger is None:
        raise PermissionError("只有账本所有者或管理员可以轮换邀请码")
    ledger.invite_code = await _new_invite_code(db)
    await db.flush()
    return ledger


async def settle_ledger(
    db: AsyncSession,
    ledger_id: int,
    user_id: int,
) -> list[dict]:
    ledger = await get_ledger_detail(db, ledger_id, user_id)
    if ledger is None:
        raise PermissionError("无权访问该账本")
    if ledger.type != LedgerType.SHARED:
        return []

    result = await db.execute(
        select(Bill)
        .options(selectinload(Bill.shares))
        .where(Bill.ledger_id == ledger_id)
    )
    bills = result.scalars().unique().all()
    balances = {member.user_id: 0.0 for member in ledger.members}

    for bill in bills:
        unsettled_shares = [share for share in bill.shares if not share.settled]
        share_total = sum(float(share.share_amount) for share in unsettled_shares)
        balances[bill.creator_id] = balances.get(bill.creator_id, 0.0) + share_total
        for share in unsettled_shares:
            balances[share.user_id] = (
                balances.get(share.user_id, 0.0) - float(share.share_amount)
            )

    names = {
        member.user_id: member.user.nickname or f"用户{member.user_id}"
        for member in ledger.members
    }
    settlements = minimize_debts(balances, names)
    for settlement in settlements:
        from_user_id = settlement["from_user_id"]
        to_user_id = settlement["to_user_id"]
        direct_shares = [
            share
            for bill in bills
            if bill.creator_id == to_user_id
            for share in bill.shares
            if share.user_id == from_user_id and not share.settled
        ]
        direct_total = sum(float(share.share_amount) for share in direct_shares)
        # 只有“直接欠款”刚好等于这笔净转账时，才能安全地整笔标记；
        # 链路抵消产生的转账留给账单详情逐笔处理。
        if abs(direct_total - float(settlement["amount"])) <= 0.01:
            settlement["share_ids"] = [share.id for share in direct_shares]
        else:
            settlement["share_ids"] = []
    return settlements


async def confirm_settlement(
    db: AsyncSession,
    ledger_id: int,
    user_id: int,
    *,
    from_user_id: int,
    to_user_id: int,
    share_ids: list[int],
) -> list[dict]:
    ledger = await get_ledger_detail(db, ledger_id, user_id)
    if ledger is None:
        raise PermissionError("无权访问该账本")
    if ledger.type != LedgerType.SHARED:
        raise ValueError("只有共享账本可以结算")
    if from_user_id == to_user_id:
        raise ValueError("付款人和收款人不能相同")
    if user_id not in {from_user_id, to_user_id}:
        raise PermissionError("只有结算双方可以确认这笔转账")
    member_ids = {member.user_id for member in ledger.members}
    if from_user_id not in member_ids or to_user_id not in member_ids:
        raise ValueError("结算双方必须是账本成员")

    result = await db.execute(
        select(Bill)
        .options(selectinload(Bill.shares))
        .where(Bill.ledger_id == ledger_id, Bill.id.in_(
            select(Bill.id).join(Bill.shares).where(
                Bill.ledger_id == ledger_id,
                Bill.creator_id == to_user_id,
            )
        ))
    )
    bills = result.scalars().unique().all()
    shares_by_id = {
        share.id: share
        for bill in bills
        for share in bill.shares
        if share.user_id == from_user_id
    }
    selected = []
    for share_id in set(share_ids):
        share = shares_by_id.get(share_id)
        if share is None:
            raise ValueError("结算分摊不存在或不属于这笔转账")
        if share.settled:
            raise ValueError("该分摊已经结算")
        selected.append(share)

    selected_total = sum(float(share.share_amount) for share in selected)
    current = await settle_ledger(db, ledger_id, user_id)
    matching = next(
        (
            item
            for item in current
            if item["from_user_id"] == from_user_id
            and item["to_user_id"] == to_user_id
        ),
        None,
    )
    if matching is None or abs(selected_total - float(matching["amount"])) > 0.01:
        raise ValueError("结算金额已变化，请重新计算后再确认")

    settled_at = date.today()
    for share in selected:
        share.settled = True
        share.settled_at = settled_at
    await db.flush()
    return await settle_ledger(db, ledger_id, user_id)


async def remove_ledger_member(
    db: AsyncSession,
    ledger_id: int,
    actor_id: int,
    target_user_id: int,
) -> Ledger:
    ledger = await get_ledger_detail(db, ledger_id, actor_id)
    if ledger is None:
        raise PermissionError("无权访问该账本")
    if ledger.type != LedgerType.SHARED:
        raise ValueError("个人账本没有其他成员")
    if actor_id == target_user_id:
        raise ValueError("不能移除自己")

    actor = next((m for m in ledger.members if m.user_id == actor_id), None)
    target = next((m for m in ledger.members if m.user_id == target_user_id), None)
    if target is None:
        raise ValueError("该用户不是账本成员")
    if target.role == LedgerRole.OWNER:
        raise ValueError("不能移除账本创建者")
    if actor is None or actor.role == LedgerRole.MEMBER:
        raise PermissionError("只有创建者或管理员可以移除成员")
    if actor.role == LedgerRole.ADMIN and target.role == LedgerRole.ADMIN:
        raise PermissionError("管理员不能移除其他管理员")

    # 移除成员前必须先结清其分摊，否则余额里会出现“非成员债务”，
    # 结算接口会拒绝确认，整本账永久卡住。
    unsettled_share = await db.scalar(
        select(BillShare.id)
        .join(Bill, Bill.id == BillShare.bill_id)
        .where(
            Bill.ledger_id == ledger_id,
            BillShare.settled.is_(False),
            or_(
                BillShare.user_id == target_user_id,
                Bill.creator_id == target_user_id,
            ),
        )
        .limit(1)
    )
    if unsettled_share is not None:
        raise ValueError("该成员还有未结算的分摊，请先完成结算再移除")

    await db.delete(target)
    await db.flush()
    await db.refresh(ledger, attribute_names=["members"])
    return ledger


async def set_member_role(
    db: AsyncSession,
    ledger_id: int,
    actor_id: int,
    target_user_id: int,
    role: LedgerRole,
) -> Ledger:
    ledger = await get_ledger_detail(db, ledger_id, actor_id)
    if ledger is None:
        raise PermissionError("无权访问该账本")
    if role not in {LedgerRole.ADMIN, LedgerRole.MEMBER}:
        raise ValueError("只能设置为管理员或普通成员")

    actor = next((m for m in ledger.members if m.user_id == actor_id), None)
    target = next((m for m in ledger.members if m.user_id == target_user_id), None)
    if actor is None or actor.role != LedgerRole.OWNER:
        raise PermissionError("只有账本创建者可以设置管理员")
    if target is None:
        raise ValueError("该用户不是账本成员")
    if target.role == LedgerRole.OWNER:
        raise ValueError("不能修改账本创建者的角色")

    target.role = role
    await db.flush()
    await db.refresh(ledger, attribute_names=["members"])
    return ledger


async def get_ledger_member_ids(
    db: AsyncSession,
    ledger_id: int,
) -> set[int]:
    result = await db.execute(
        select(LedgerMember.user_id).where(LedgerMember.ledger_id == ledger_id)
    )
    return set(result.scalars().all())

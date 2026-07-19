import secrets

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agents.social import minimize_debts
from app.models import (
    Bill,
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
    return minimize_debts(balances, names)


async def get_ledger_member_ids(
    db: AsyncSession,
    ledger_id: int,
) -> set[int]:
    result = await db.execute(
        select(LedgerMember.user_id).where(LedgerMember.ledger_id == ledger_id)
    )
    return set(result.scalars().all())

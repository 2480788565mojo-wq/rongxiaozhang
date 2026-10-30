from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DBSession, RedisClient, require_ledger_access
from app.core.redis import ledger_write_lock
from app.models import Ledger, LedgerRole, LedgerType
from app.schemas.ledger import (
    LedgerCreate,
    LedgerJoin,
    LedgerMemberOut,
    LedgerOut,
    LedgerSettlementResponse,
    MemberRoleUpdate,
    SettlementConfirm,
)
from app.services.ledger_service import (
    confirm_settlement,
    create_ledger,
    get_ledger_detail,
    join_ledger,
    list_user_ledgers,
    remove_ledger_member,
    rotate_invite_code,
    set_member_role,
    settle_ledger,
)

router = APIRouter()


def ledger_to_out(ledger: Ledger, viewer_id: int) -> LedgerOut:
    members = [
        LedgerMemberOut(
            user_id=member.user_id,
            role=member.role.value,
            nickname=member.user.nickname,
            avatar_url=member.user.avatar_url,
        )
        for member in ledger.members
    ]
    return LedgerOut(
        id=ledger.id,
        name=ledger.name,
        type=ledger.type.value,
        owner_id=ledger.owner_id,
        invite_code=(
            ledger.invite_code
            if any(
                member.user_id == viewer_id
                and member.role.value in {"owner", "admin"}
                for member in ledger.members
            )
            else None
        ),
        settle_strategy=ledger.settle_strategy,
        member_count=len(members),
        created_at=ledger.created_at,
        members=members,
    )


@router.get("", response_model=list[LedgerOut])
async def get_ledgers(user: CurrentUser, db: DBSession) -> list[LedgerOut]:
    ledgers = await list_user_ledgers(db, user.id)
    return [ledger_to_out(ledger, user.id) for ledger in ledgers]


@router.post("", response_model=LedgerOut, status_code=status.HTTP_201_CREATED)
async def add_ledger(
    payload: LedgerCreate,
    user: CurrentUser,
    db: DBSession,
) -> LedgerOut:
    ledger = await create_ledger(
        db,
        user,
        name=payload.name,
        ledger_type=LedgerType(payload.type),
    )
    await db.commit()
    loaded = await get_ledger_detail(db, ledger.id, user.id)
    if loaded is None:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "账本创建后读取失败")
    return ledger_to_out(loaded, user.id)


@router.get("/{ledger_id}", response_model=LedgerOut)
async def get_ledger(
    ledger_id: int,
    user: CurrentUser,
    db: DBSession,
) -> LedgerOut:
    ledger = await get_ledger_detail(db, ledger_id, user.id)
    if ledger is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "账本不存在或无权访问")
    return ledger_to_out(ledger, user.id)


@router.post("/{ledger_id}/invite/rotate", response_model=LedgerOut)
async def rotate_shared_invite(
    ledger_id: int,
    user: CurrentUser,
    db: DBSession,
) -> LedgerOut:
    try:
        ledger = await rotate_invite_code(db, ledger_id, user.id)
    except PermissionError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(exc)) from exc
    await db.commit()
    loaded = await get_ledger_detail(db, ledger.id, user.id)
    if loaded is None:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "邀请码轮换后读取失败")
    return ledger_to_out(loaded, user.id)


@router.post("/{ledger_id}/join", response_model=LedgerOut)
async def join_shared_ledger(
    ledger_id: int,
    payload: LedgerJoin,
    user: CurrentUser,
    db: DBSession,
) -> LedgerOut:
    try:
        await join_ledger(db, ledger_id, user.id, payload.invite_code)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    await db.commit()
    ledger = await get_ledger_detail(db, ledger_id, user.id)
    if ledger is None:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "加入账本后读取失败")
    return ledger_to_out(ledger, user.id)


@router.delete("/{ledger_id}/members/{member_user_id}", response_model=LedgerOut)
async def remove_member(
    ledger_id: int,
    member_user_id: int,
    user: CurrentUser,
    db: DBSession,
    redis: RedisClient,
) -> LedgerOut:
    async with ledger_write_lock(redis, ledger_id):
        try:
            ledger = await remove_ledger_member(
                db, ledger_id, user.id, member_user_id
            )
        except PermissionError as exc:
            raise HTTPException(status.HTTP_403_FORBIDDEN, str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
        await db.commit()
        loaded = await get_ledger_detail(db, ledger.id, user.id)
        if loaded is None:
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "移除成员后读取失败")
        return ledger_to_out(loaded, user.id)


@router.put("/{ledger_id}/members/{member_user_id}", response_model=LedgerOut)
async def update_member_role(
    ledger_id: int,
    member_user_id: int,
    payload: MemberRoleUpdate,
    user: CurrentUser,
    db: DBSession,
    redis: RedisClient,
) -> LedgerOut:
    async with ledger_write_lock(redis, ledger_id):
        try:
            ledger = await set_member_role(
                db,
                ledger_id,
                user.id,
                member_user_id,
                LedgerRole(payload.role),
            )
        except PermissionError as exc:
            raise HTTPException(status.HTTP_403_FORBIDDEN, str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
        await db.commit()
        loaded = await get_ledger_detail(db, ledger.id, user.id)
        if loaded is None:
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "更新成员后读取失败")
        return ledger_to_out(loaded, user.id)


@router.post("/{ledger_id}/settle", response_model=LedgerSettlementResponse)
async def settle_shared_ledger(
    ledger_id: int,
    user: CurrentUser,
    db: DBSession,
) -> LedgerSettlementResponse:
    try:
        settlements = await settle_ledger(db, ledger_id, user.id)
    except PermissionError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "账本不存在或无权访问") from exc
    return LedgerSettlementResponse(
        ledger_id=ledger_id,
        settlements=settlements,
    )


@router.post("/{ledger_id}/settle/confirm", response_model=LedgerSettlementResponse)
async def confirm_shared_settlement(
    ledger_id: int,
    payload: SettlementConfirm,
    user: CurrentUser,
    db: DBSession,
    redis: RedisClient,
) -> LedgerSettlementResponse:
    # 先确认成员身份，避免任意登录用户锁住别人的账本。
    await require_ledger_access(db, ledger_id, user.id)
    # 与账单写入共用同一把账本锁，避免“算完转账后有人新增/修改账单”的竞态。
    async with ledger_write_lock(redis, ledger_id):
        try:
            settlements = await confirm_settlement(
                db,
                ledger_id,
                user.id,
                from_user_id=payload.from_user_id,
                to_user_id=payload.to_user_id,
                share_ids=payload.share_ids,
            )
        except PermissionError as exc:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "账本不存在或无权访问") from exc
        except ValueError as exc:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
        await db.commit()
        return LedgerSettlementResponse(
            ledger_id=ledger_id,
            settlements=settlements,
        )

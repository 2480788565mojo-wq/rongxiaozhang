from contextlib import AsyncExitStack
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy import and_, delete as sql_delete, or_, select

from app.api.deps import CurrentUser, DBSession, RedisClient
from app.api.rate_limit import require_rate_limits
from app.config import get_settings
from app.core.rate_limit import RateLimitRule
from app.core.redis import ledger_write_lock
from app.core.security import create_access_token
from app.models import (
    Account,
    Bill,
    BillShare,
    Budget,
    Category,
    ChatHistory,
    Insight,
    Ledger,
    LedgerMember,
    LedgerRole,
    LedgerType,
    User,
)
from app.schemas.auth import DevLoginRequest, LoginRequest, TokenResponse, UserOut
from app.services.bill_service import lock_user_for_billing

router = APIRouter()
dev_router = APIRouter()
settings = get_settings()
EXPORT_BILL_LIMIT = 10_000
EXPORT_LIMIT_PER_HOUR = 10
DELETE_LIMIT_PER_HOUR = 5


async def _get_or_create_user(
    db: DBSession,
    *,
    openid: str,
    nickname: str | None = None,
) -> User:
    result = await db.execute(select(User).where(User.openid == openid))
    user = result.scalar_one_or_none()
    if user is not None:
        if nickname and not user.nickname:
            user.nickname = nickname
        return user

    user = User(openid=openid, nickname=nickname)
    db.add(user)
    await db.flush()

    ledger = Ledger(
        name="我的账本",
        type=LedgerType.PERSONAL,
        owner_id=user.id,
    )
    db.add(ledger)
    await db.flush()
    db.add(
        LedgerMember(
            ledger_id=ledger.id,
            user_id=user.id,
            role=LedgerRole.OWNER,
        )
    )
    user.default_ledger_id = ledger.id
    db.add_all(
        [
            Account(user_id=user.id, ledger_id=ledger.id, name="微信钱包", type="电子钱包", balance=0),
            Account(user_id=user.id, ledger_id=ledger.id, name="支付宝", type="电子钱包", balance=0),
            Account(user_id=user.id, ledger_id=ledger.id, name="银行卡", type="银行卡", balance=0),
            Account(user_id=user.id, ledger_id=ledger.id, name="现金", type="现金", balance=0),
        ]
    )
    return user


@router.post("/login", response_model=TokenResponse)
async def wx_login(
    payload: LoginRequest,
    request: Request,
    db: DBSession,
    redis: RedisClient,
) -> TokenResponse:
    client_host = request.client.host if request.client else "unknown"
    await require_rate_limits(
        redis,
        f"ip:{client_host}:login",
        RateLimitRule("minute", settings.LOGIN_LIMIT_PER_MINUTE, 60),
    )
    if not settings.WECHAT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="微信登录尚未配置，请联系管理员",
        )

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                "https://api.weixin.qq.com/sns/jscode2session",
                params={
                    "appid": settings.WECHAT_APPID,
                    "secret": settings.WECHAT_SECRET,
                    "js_code": payload.code,
                    "grant_type": "authorization_code",
                },
            )
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="暂时无法连接微信登录服务",
        ) from exc

    data = response.json()
    openid = data.get("openid")
    if not openid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="微信登录凭证无效或已过期",
        )

    user = await _get_or_create_user(db, openid=openid)

    return TokenResponse(
        access_token=create_access_token(user.id),
        user=UserOut.model_validate(user),
    )


@dev_router.post("/dev-login", response_model=TokenResponse, include_in_schema=False)
async def dev_login(
    payload: DevLoginRequest,
    request: Request,
    db: DBSession,
) -> TokenResponse:
    client_host = request.client.host if request.client else ""
    dev_login_enabled = (
        settings.ENVIRONMENT == "development"
        and settings.ENABLE_DEV_LOGIN
    )
    if not dev_login_enabled or client_host not in {"127.0.0.1", "::1", "localhost"}:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "接口不存在")
    user = await _get_or_create_user(
        db,
        openid="dev:h5-local",
        nickname=payload.nickname,
    )
    return TokenResponse(
        access_token=create_access_token(user.id),
        user=UserOut.model_validate(user),
    )


@router.get("/me", response_model=UserOut)
async def get_me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)


@router.get("/export")
async def export_me(
    user: CurrentUser,
    db: DBSession,
    redis: RedisClient,
):
    """导出当前账号可访问的账本数据；账单最多 10,000 笔，超出时 truncated=true。"""
    await require_rate_limits(
        redis,
        f"user:{user.id}:export",
        RateLimitRule("hour", EXPORT_LIMIT_PER_HOUR, 3600),
    )
    ledger_rows = (
        await db.execute(
            select(Ledger)
            .join(LedgerMember, LedgerMember.ledger_id == Ledger.id)
            .where(LedgerMember.user_id == user.id)
            .order_by(Ledger.created_at.asc())
        )
    ).scalars().unique().all()
    ledger_ids = [ledger.id for ledger in ledger_rows]
    bills = (
        (
            await db.execute(
                select(Bill)
                .where(Bill.ledger_id.in_(ledger_ids))
                .order_by(Bill.bill_date, Bill.id)
                .limit(EXPORT_BILL_LIMIT + 1)
            )
        ).scalars().all()
        if ledger_ids
        else []
    )
    truncated = len(bills) > EXPORT_BILL_LIMIT
    bills = bills[:EXPORT_BILL_LIMIT]
    accounts = (
        await db.execute(select(Account).where(Account.user_id == user.id))
    ).scalars().all()
    budgets = (
        await db.execute(select(Budget).where(Budget.user_id == user.id))
    ).scalars().all()
    categories = (
        await db.execute(select(Category).where(Category.user_id == user.id))
    ).scalars().all()
    insights = (
        await db.execute(select(Insight).where(Insight.user_id == user.id))
    ).scalars().all()
    chats = (
        await db.execute(
            select(ChatHistory)
            .where(ChatHistory.user_id == user.id)
            .order_by(ChatHistory.created_at)
        )
    ).scalars().all()

    return jsonable_encoder(
        {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "truncated": truncated,
            "user": {
                "id": user.id,
                "nickname": user.nickname,
                "avatar_url": user.avatar_url,
                "created_at": user.created_at,
            },
            "ledgers": [
                {
                    "id": ledger.id,
                    "name": ledger.name,
                    "type": ledger.type.value,
                    "owner_id": ledger.owner_id,
                    "created_at": ledger.created_at,
                }
                for ledger in ledger_rows
            ],
            "bills": [
                {
                    "id": bill.id,
                    "ledger_id": bill.ledger_id,
                    "creator_id": bill.creator_id,
                    "type": bill.type.value,
                    "amount": bill.amount,
                    "category": bill.category,
                    "subcategory": bill.subcategory,
                    "account": bill.account,
                    "note": bill.note,
                    "bill_date": bill.bill_date,
                    "created_at": bill.created_at,
                }
                for bill in bills
            ],
            "accounts": [
                {
                    "id": account.id,
                    "ledger_id": account.ledger_id,
                    "name": account.name,
                    "type": account.type,
                    "balance": account.balance,
                }
                for account in accounts
            ],
            "budgets": [
                {
                    "id": budget.id,
                    "ledger_id": budget.ledger_id,
                    "year": budget.year,
                    "month": budget.month,
                    "total_budget": budget.total_budget,
                    "category_budgets": budget.category_budgets,
                }
                for budget in budgets
            ],
            "categories": [
                {
                    "id": category.id,
                    "ledger_id": category.ledger_id,
                    "type": category.type.value,
                    "parent_name": category.parent_name,
                    "name": category.name,
                }
                for category in categories
            ],
            "insights": [
                {
                    "id": insight.id,
                    "ledger_id": insight.ledger_id,
                    "report_type": insight.report_type,
                    "content": insight.content,
                    "generated_at": insight.generated_at,
                }
                for insight in insights
            ],
            "chats": [
                {
                    "id": chat.id,
                    "ledger_id": chat.ledger_id,
                    "session_id": chat.session_id,
                    "role": chat.role.value,
                    "content": chat.content,
                    "created_at": chat.created_at,
                }
                for chat in chats
            ],
        }
    )


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_me(
    user: CurrentUser,
    db: DBSession,
    redis: RedisClient,
) -> Response:
    """删除账号及其个人数据；共享账本中由本人创建的账单也会一并删除。"""
    await require_rate_limits(
        redis,
        f"user:{user.id}:delete-account",
        RateLimitRule("hour", DELETE_LIMIT_PER_HOUR, 3600),
    )
    # 先锁 user 行，再按 id 排序锁账本，保持 user→ledger 的全局锁顺序。
    await lock_user_for_billing(db, user.id)
    ledger_ids = list(
        (
            await db.scalars(
                select(LedgerMember.ledger_id).where(
                    LedgerMember.user_id == user.id
                )
            )
        ).all()
    )
    async with AsyncExitStack() as stack:
        for ledger_id in sorted(set(ledger_ids)):
            await stack.enter_async_context(ledger_write_lock(redis, ledger_id))
        return await _delete_me_locked(user, db)


async def _delete_me_locked(user: User, db: DBSession) -> Response:
    other_member_ledger = await db.scalar(
        select(LedgerMember.ledger_id)
        .join(Ledger, Ledger.id == LedgerMember.ledger_id)
        .where(
            Ledger.owner_id == user.id,
            Ledger.type == LedgerType.SHARED,
            LedgerMember.user_id != user.id,
        )
        .limit(1)
    )
    if other_member_ledger is not None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "你仍是共享账本创建者，请先转移所有权或移除其他成员后再删除账号",
        )

    unsettled_share = await db.scalar(
        select(BillShare.id)
        .join(Bill, Bill.id == BillShare.bill_id)
        .where(
            BillShare.settled.is_(False),
            or_(
                and_(
                    BillShare.user_id == user.id,
                    Bill.creator_id != user.id,
                ),
                and_(
                    Bill.creator_id == user.id,
                    BillShare.user_id != user.id,
                ),
            ),
            Bill.ledger_id.in_(
                select(LedgerMember.ledger_id).where(
                    LedgerMember.user_id == user.id
                )
            ),
        )
        .limit(1)
    )
    if unsettled_share is not None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "你还有未结算的分摊，请先完成结算后再删除账号",
        )
    user.default_ledger_id = None
    await db.flush()
    await db.execute(sql_delete(BillShare).where(BillShare.user_id == user.id))
    await db.execute(sql_delete(Bill).where(Bill.creator_id == user.id))
    await db.execute(sql_delete(Ledger).where(Ledger.owner_id == user.id))
    await db.execute(sql_delete(LedgerMember).where(LedgerMember.user_id == user.id))
    await db.execute(sql_delete(Account).where(Account.user_id == user.id))
    await db.execute(sql_delete(Budget).where(Budget.user_id == user.id))
    await db.execute(sql_delete(Category).where(Category.user_id == user.id))
    await db.execute(sql_delete(Insight).where(Insight.user_id == user.id))
    await db.execute(sql_delete(ChatHistory).where(ChatHistory.user_id == user.id))
    await db.delete(user)
    # 必须在锁内提交：否则锁先释放、依赖层后提交，其他请求会看到半完成状态。
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

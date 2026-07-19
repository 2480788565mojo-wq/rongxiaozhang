import httpx
from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DBSession, RedisClient
from app.api.rate_limit import require_rate_limits
from app.config import get_settings
from app.core.rate_limit import RateLimitRule
from app.core.security import create_access_token
from app.models import Account, Ledger, LedgerMember, LedgerRole, LedgerType, User
from app.schemas.auth import DevLoginRequest, LoginRequest, TokenResponse, UserOut

router = APIRouter()
dev_router = APIRouter()
settings = get_settings()


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

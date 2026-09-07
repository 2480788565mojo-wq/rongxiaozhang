from fastapi import APIRouter

from app.config import get_settings
from app.api.v1 import (
    accounts,
    auth,
    bills,
    budgets,
    categories,
    insights,
    ledgers,
    sse,
    stats,
)


api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["认证"])
settings = get_settings()
if settings.ENVIRONMENT == "development" and settings.ENABLE_DEV_LOGIN:
    api_router.include_router(auth.dev_router, prefix="/auth", tags=["认证"])
api_router.include_router(accounts.router, prefix="/accounts", tags=["账户"])
api_router.include_router(bills.router, prefix="/bills", tags=["账单"])
api_router.include_router(ledgers.router, prefix="/ledgers", tags=["账本"])
api_router.include_router(budgets.router, prefix="/budgets", tags=["预算"])
api_router.include_router(categories.router, prefix="/categories", tags=["分类"])
api_router.include_router(stats.router, prefix="/stats", tags=["统计"])
api_router.include_router(insights.router, prefix="/insights", tags=["洞察"])
api_router.include_router(sse.router, prefix="/sse", tags=["实时推送"])


@api_router.get("/health", tags=["系统"])
async def api_health() -> dict[str, str]:
    return {"status": "ok", "version": "2.0.0"}


@api_router.get("/config", tags=["系统"])
async def public_config() -> dict[str, bool]:
    """免登录的客户端配置接口：前端启动时拉取，决定 AI 相关功能是否展示。"""
    return {"ai_enabled": settings.AI_FEATURES_ENABLED}

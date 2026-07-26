from typing import Annotated

from fastapi import Depends, HTTPException, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.redis import get_redis
from app.core.security import get_current_user
from app.models import Ledger, LedgerMember, User
from app.services.bill_service import get_accessible_ledger


DBSession = Annotated[AsyncSession, Depends(get_db)]
RedisClient = Annotated[Redis, Depends(get_redis)]
CurrentUser = Annotated[User, Depends(get_current_user)]


async def require_ledger_access(
    db: AsyncSession,
    ledger_id: int,
    user_id: int,
) -> tuple[Ledger, LedgerMember]:
    """Return the requested ledger membership or hide it behind a 404.

    Keeping this translation at the API dependency boundary ensures every
    ledger-scoped endpoint exposes the same response without leaking whether
    an inaccessible ledger exists.
    """
    try:
        return await get_accessible_ledger(db, ledger_id, user_id)
    except PermissionError as exc:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "账本不存在或无权访问",
        ) from exc

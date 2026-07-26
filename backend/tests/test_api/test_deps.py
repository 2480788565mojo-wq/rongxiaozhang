from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.api import deps


@pytest.mark.asyncio
async def test_require_ledger_access_returns_service_result(monkeypatch):
    expected = (object(), object())
    service = AsyncMock(return_value=expected)
    monkeypatch.setattr(deps, "get_accessible_ledger", service)
    db = object()

    result = await deps.require_ledger_access(db, ledger_id=23, user_id=42)

    assert result == expected
    service.assert_awaited_once_with(db, 23, 42)


@pytest.mark.asyncio
async def test_require_ledger_access_hides_forbidden_ledger(monkeypatch):
    service = AsyncMock(side_effect=PermissionError("无权访问该账本"))
    monkeypatch.setattr(deps, "get_accessible_ledger", service)

    with pytest.raises(HTTPException) as exc_info:
        await deps.require_ledger_access(object(), ledger_id=23, user_id=42)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "账本不存在或无权访问"


@pytest.mark.asyncio
async def test_require_ledger_access_preserves_infrastructure_errors(monkeypatch):
    monkeypatch.setattr(
        deps,
        "get_accessible_ledger",
        AsyncMock(side_effect=RuntimeError("database unavailable")),
    )

    with pytest.raises(RuntimeError, match="database unavailable"):
        await deps.require_ledger_access(object(), ledger_id=23, user_id=42)

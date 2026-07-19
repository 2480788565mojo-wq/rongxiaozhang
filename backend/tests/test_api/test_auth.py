from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import select

import app.api.v1.auth as auth_api
from app.models import Account, Ledger, User
from app.schemas.auth import DevLoginRequest


@pytest.mark.asyncio
async def test_dev_login_creates_local_user_ledger_and_accounts(db_session, monkeypatch):
    monkeypatch.setattr(auth_api.settings, "ENVIRONMENT", "development")
    monkeypatch.setattr(auth_api.settings, "ENABLE_DEV_LOGIN", True)
    response = await auth_api.dev_login(
        DevLoginRequest(),
        SimpleNamespace(client=SimpleNamespace(host="127.0.0.1")),
        db_session,
    )

    assert response.access_token
    assert response.user.nickname == "H5 测试用户"
    assert await db_session.scalar(select(User.id)) == response.user.id
    assert await db_session.scalar(select(Ledger.id)) == response.user.default_ledger_id
    assert len((await db_session.scalars(select(Account))).all()) == 4


@pytest.mark.asyncio
async def test_dev_login_is_hidden_when_debug_is_disabled(db_session, monkeypatch):
    monkeypatch.setattr(auth_api.settings, "ENVIRONMENT", "development")
    monkeypatch.setattr(auth_api.settings, "ENABLE_DEV_LOGIN", False)
    with pytest.raises(HTTPException) as error:
        await auth_api.dev_login(
            DevLoginRequest(),
            SimpleNamespace(client=SimpleNamespace(host="127.0.0.1")),
            db_session,
        )
    assert error.value.status_code == 404


@pytest.mark.asyncio
async def test_dev_login_is_hidden_outside_development(db_session, monkeypatch):
    monkeypatch.setattr(auth_api.settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(auth_api.settings, "ENABLE_DEV_LOGIN", True)
    with pytest.raises(HTTPException) as error:
        await auth_api.dev_login(
            DevLoginRequest(),
            SimpleNamespace(client=SimpleNamespace(host="127.0.0.1")),
            db_session,
        )
    assert error.value.status_code == 404

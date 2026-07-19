import pytest
from pydantic import ValidationError

from app.config import Settings


def settings(**overrides) -> Settings:
    values = {
        "JWT_SECRET": "test-secret-with-at-least-32-random-characters",
        "ENVIRONMENT": "test",
        "DEBUG": False,
        "ENABLE_DEV_LOGIN": False,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


@pytest.mark.parametrize(
    "secret",
    [
        "too-short",
        "your-secret-key-change-in-production",
        "change-me-to-random-string",
        "replace-with-at-least-32-random-characters",
    ],
)
def test_insecure_jwt_secrets_are_rejected(secret):
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        settings(JWT_SECRET=secret)


def test_production_rejects_debug_mode():
    with pytest.raises(ValidationError, match="生产环境禁止开启 DEBUG"):
        settings(ENVIRONMENT="production", DEBUG=True)


def test_production_rejects_dev_login():
    with pytest.raises(ValidationError, match="生产环境禁止开启开发登录"):
        settings(ENVIRONMENT="production", ENABLE_DEV_LOGIN=True)


def test_production_accepts_a_secure_configuration():
    configured = settings(ENVIRONMENT="production")
    assert configured.ENVIRONMENT == "production"
    assert configured.DEBUG is False
    assert configured.ENABLE_DEV_LOGIN is False

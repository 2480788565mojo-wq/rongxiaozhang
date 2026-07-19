from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

import app.api.v1.sse as sse_api


@pytest.mark.asyncio
async def test_sse_rejects_third_connection(monkeypatch):
    monkeypatch.setattr(sse_api, "acquire_connection_slot", AsyncMock(return_value=False))

    with pytest.raises(HTTPException) as error:
        await sse_api.sse_subscribe(SimpleNamespace(id=1), AsyncMock())

    assert error.value.status_code == 429


@pytest.mark.asyncio
async def test_sse_sends_heartbeat_and_releases_slot(monkeypatch):
    pubsub = SimpleNamespace(
        subscribe=AsyncMock(),
        get_message=AsyncMock(return_value=None),
        unsubscribe=AsyncMock(),
        aclose=AsyncMock(),
    )
    redis = SimpleNamespace(pubsub=lambda: pubsub)
    monkeypatch.setattr(sse_api, "acquire_connection_slot", AsyncMock(return_value=True))
    monkeypatch.setattr(sse_api, "touch_connection_slot", AsyncMock(return_value=True))
    release = AsyncMock()
    monkeypatch.setattr(sse_api, "release_connection_slot", release)

    response = await sse_api.sse_subscribe(SimpleNamespace(id=1), redis)
    stream = response.body_iterator
    first = await anext(stream)
    heartbeat = await anext(stream)
    await stream.aclose()

    assert "event: connected" in first
    assert heartbeat == ": heartbeat\n\n"
    release.assert_awaited_once()

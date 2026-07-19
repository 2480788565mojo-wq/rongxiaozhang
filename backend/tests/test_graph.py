from unittest.mock import AsyncMock

import pytest

import app.agents.graph as graph_module
from app.agents.graph import (
    clear_transaction_session,
    prepare_transaction_config,
    route_after_guardian,
    route_after_parser,
    transaction_thread_id,
)


def test_parser_route_stops_for_missing_fields():
    assert route_after_parser({"missing_fields": ["amount"]}) == "__end__"


def test_parser_route_stops_for_error():
    assert route_after_parser({"error": "failed"}) == "__end__"


def test_parser_route_continues_when_complete():
    assert route_after_parser({"missing_fields": [], "error": None}) == "guardian"


def test_guardian_route_stops_when_blocked():
    assert route_after_guardian({"risk_level": "blocked"}) == "__end__"


def test_guardian_route_selects_personal_or_shared_branch():
    assert route_after_guardian(
        {"risk_level": "safe", "is_shared_ledger": False}
    ) == "oracle"
    assert route_after_guardian(
        {"risk_level": "safe", "is_shared_ledger": True}
    ) == "social_ledger"


def test_transaction_thread_is_isolated_by_user_and_ledger():
    assert transaction_thread_id(1, 9, "same") != transaction_thread_id(2, 9, "same")
    assert transaction_thread_id(1, 9, "same") != transaction_thread_id(1, 10, "same")


def test_expired_transaction_sessions_are_deleted(monkeypatch):
    saver = type("Saver", (), {"delete_thread": lambda self, thread_id: deleted.append(thread_id)})()
    graph = type("Graph", (), {"checkpointer": saver})()
    deleted = []
    graph_module._session_last_seen.clear()
    monkeypatch.setattr(graph_module.settings, "AGENT_SESSION_TTL_SECONDS", 1800)
    times = iter([0.0, 1801.0])
    monkeypatch.setattr(graph_module, "monotonic", lambda: next(times))

    first = prepare_transaction_config(graph, 1, 9, "first")
    prepare_transaction_config(graph, 1, 9, "second")

    first_thread = first["configurable"]["thread_id"]
    assert deleted == [first_thread]


@pytest.mark.asyncio
async def test_completed_transaction_session_uses_official_delete_api(monkeypatch):
    saver = type("Saver", (), {"adelete_thread": AsyncMock()})()
    compiled = type("Graph", (), {"checkpointer": saver})()
    monkeypatch.setattr(graph_module, "compiled_graph", compiled)
    thread_id = transaction_thread_id(1, 9, "done")
    graph_module._session_last_seen[thread_id] = 1.0

    await clear_transaction_session(1, 9, "done")

    saver.adelete_thread.assert_awaited_once_with(thread_id)
    assert thread_id not in graph_module._session_last_seen

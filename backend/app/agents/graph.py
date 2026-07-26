import asyncio
from importlib.util import find_spec
import logging
from time import monotonic
from typing import Any

from app.agents.advisor import advisor_node
from app.agents.guardian import guardian_node, guardian_review_node
from app.agents.oracle import oracle_node
from app.agents.orchestrator import orchestrator_finalize_node, orchestrator_node
from app.agents.parser import parser_node
from app.agents.social import social_node
from app.agents.state import TransactionState
from app.config import get_settings


END_NODE = "__end__"
settings = get_settings()
logger = logging.getLogger(__name__)
_session_last_seen: dict[str, float] = {}


def route_after_parser(state: TransactionState) -> str:
    if state.get("error"):
        return END_NODE
    if state.get("missing_fields"):
        return END_NODE
    return "guardian"


def route_after_guardian(state: TransactionState) -> str:
    if state.get("error") or state.get("risk_level") == "blocked":
        return END_NODE
    if state.get("is_shared_ledger", False):
        return "social_ledger"
    return "oracle"


def route_after_parser_collaboration(state: TransactionState) -> str:
    """New graph routing while keeping route_after_parser backward compatible."""
    if state.get("error") or state.get("missing_fields"):
        return END_NODE
    if state.get("route_mode") == "quick":
        return "oracle"
    return "guardian"


def route_after_guardian_collaboration(state: TransactionState) -> str:
    if state.get("error"):
        return END_NODE
    opinion = state.get("guardian_opinion") or {}
    if (
        state.get("route_mode") == "deep"
        or state.get("risk_level") in {"warning", "blocked"}
        or opinion.get("needs_advisor") is True
    ):
        return "advisor"
    if state.get("is_shared_ledger", False):
        return "social_ledger"
    return "oracle"


def route_after_advisor(state: TransactionState) -> str:
    if state.get("error"):
        return END_NODE
    if state.get("intent") == "advice":
        return "oracle"
    return "guardian_review"


def route_after_guardian_review(state: TransactionState) -> str:
    if state.get("is_shared_ledger", False):
        return "social_ledger"
    return "oracle"


def route_after_orchestrator(state: TransactionState) -> str:
    if state.get("intent") == "advice":
        return "advisor"
    return "parser"


def build_graph() -> Any:
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.graph import END, StateGraph

    builder = StateGraph(TransactionState)
    builder.add_node("orchestrator", orchestrator_node)
    builder.add_node("parser", parser_node)
    builder.add_node("guardian", guardian_node)
    builder.add_node("guardian_review", guardian_review_node)
    builder.add_node("advisor", advisor_node)
    builder.add_node("social_ledger", social_node)
    builder.add_node("oracle", oracle_node)
    builder.add_node("finalize", orchestrator_finalize_node)
    builder.set_entry_point("orchestrator")
    builder.add_conditional_edges(
        "orchestrator",
        route_after_orchestrator,
        {"parser": "parser", "advisor": "advisor"},
    )

    builder.add_conditional_edges(
        "parser",
        route_after_parser_collaboration,
        {
            "guardian": "guardian",
            "oracle": "oracle",
            END_NODE: END,
        },
    )
    builder.add_conditional_edges(
        "guardian",
        route_after_guardian_collaboration,
        {
            "advisor": "advisor",
            "social_ledger": "social_ledger",
            "oracle": "oracle",
            END_NODE: END,
        },
    )
    builder.add_conditional_edges(
        "advisor",
        route_after_advisor,
        {
            "guardian_review": "guardian_review",
            "oracle": "oracle",
        },
    )
    builder.add_conditional_edges(
        "guardian_review",
        route_after_guardian_review,
        {
            "social_ledger": "social_ledger",
            "oracle": "oracle",
        },
    )
    builder.add_edge("social_ledger", "oracle")
    builder.add_edge("oracle", "finalize")
    builder.add_edge("finalize", END)

    return builder.compile(checkpointer=MemorySaver())


# Keep pure routing helpers importable while dependencies are being installed.
# A normal backend process builds this immediately once LangGraph is available.
compiled_graph = build_graph() if find_spec("langgraph") is not None else None


def get_compiled_graph() -> Any:
    if compiled_graph is None:
        raise RuntimeError("LangGraph 尚未安装，无法启动 Agent 状态机")
    return compiled_graph


def transaction_thread_id(user_id: int, ledger_id: int, session_id: str) -> str:
    return f"user:{user_id}:ledger:{ledger_id}:session:{session_id}"


def prepare_transaction_config(
    graph: Any,
    user_id: int,
    ledger_id: int,
    session_id: str,
) -> dict[str, dict[str, str]]:
    now = monotonic()
    cleanup_expired_transaction_sessions(graph, now=now)

    thread_id = transaction_thread_id(user_id, ledger_id, session_id)
    _session_last_seen[thread_id] = now
    return {"configurable": {"thread_id": thread_id}}


def cleanup_expired_transaction_sessions(
    graph: Any | None = None,
    *,
    now: float | None = None,
) -> int:
    target_graph = graph or compiled_graph
    if target_graph is None:
        return 0
    checkpointer = getattr(target_graph, "checkpointer", None)
    if checkpointer is None:
        return 0
    current_time = monotonic() if now is None else now
    expired = [
        thread_id
        for thread_id, last_seen in _session_last_seen.items()
        if current_time - last_seen >= settings.AGENT_SESSION_TTL_SECONDS
    ]
    for thread_id in expired:
        checkpointer.delete_thread(thread_id)
        _session_last_seen.pop(thread_id, None)
    return len(expired)


async def run_transaction_session_cleanup(interval_seconds: int = 60) -> None:
    while True:
        await asyncio.sleep(interval_seconds)
        try:
            cleanup_expired_transaction_sessions()
        except Exception:
            logger.warning("AI 过期会话清理失败", exc_info=True)


async def clear_transaction_session(
    user_id: int,
    ledger_id: int,
    session_id: str,
) -> None:
    thread_id = transaction_thread_id(user_id, ledger_id, session_id)
    _session_last_seen.pop(thread_id, None)
    if compiled_graph is not None:
        try:
            await compiled_graph.checkpointer.adelete_thread(thread_id)
        except Exception:
            logger.warning("AI 会话清理失败，将由过期清理再次处理", exc_info=True)

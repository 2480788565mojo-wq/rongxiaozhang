from typing import Any, Literal, TypedDict


RiskLevel = Literal["safe", "warning", "blocked"]
RouteMode = Literal["quick", "standard", "deep"]
AgentIntent = Literal["transaction", "advice", "unknown"]


class AgentMessage(TypedDict, total=False):
    agent: str
    role: Literal["decision", "analysis", "recommendation", "fallback"]
    content: str
    metadata: dict[str, Any]


class TransactionState(TypedDict, total=False):
    # Request context
    raw_input: str
    user_id: int
    ledger_id: int
    session_id: str

    # Agent collaboration context
    intent: AgentIntent
    route_mode: RouteMode
    route_reason: str | None
    agent_messages: list[AgentMessage]
    context_memory: dict[str, Any]
    degraded_agents: list[str]

    # Parser output
    parsed: dict | None
    missing_fields: list[str]
    clarification_question: str | None
    clarification_round: int

    # Guardian output
    budget_check: dict | None
    risk_level: RiskLevel
    rule_risk_level: RiskLevel
    ai_risk_level: RiskLevel
    guardian_opinion: dict | None
    guardian_review: dict | None

    # Advisor and orchestration output
    advisor_recommendation: dict | None
    final_advice: str | None
    debate_round: int

    # Social ledger output
    is_shared_ledger: bool
    settlements: list[dict] | None

    # Oracle output
    insight_triggered: bool

    # Shared error channel
    error: str | None


def new_transaction_state(
    *,
    raw_input: str,
    user_id: int,
    ledger_id: int,
    session_id: str,
) -> TransactionState:
    return {
        "raw_input": raw_input,
        "user_id": user_id,
        "ledger_id": ledger_id,
        "session_id": session_id,
        "intent": "transaction",
        "route_mode": "standard",
        "route_reason": None,
        "agent_messages": [],
        "context_memory": {},
        "degraded_agents": [],
        "parsed": None,
        "missing_fields": [],
        "clarification_question": None,
        "clarification_round": 0,
        "budget_check": None,
        "risk_level": "safe",
        "rule_risk_level": "safe",
        "ai_risk_level": "safe",
        "guardian_opinion": None,
        "guardian_review": None,
        "advisor_recommendation": None,
        "final_advice": None,
        "debate_round": 0,
        "is_shared_ledger": False,
        "settlements": None,
        "insight_triggered": False,
        "error": None,
    }

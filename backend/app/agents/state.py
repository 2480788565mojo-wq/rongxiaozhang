from typing import Literal, TypedDict


RiskLevel = Literal["safe", "warning", "blocked"]


class TransactionState(TypedDict, total=False):
    # Request context
    raw_input: str
    user_id: int
    ledger_id: int
    session_id: str

    # Parser output
    parsed: dict | None
    missing_fields: list[str]
    clarification_question: str | None
    clarification_round: int

    # Guardian output
    budget_check: dict | None
    risk_level: RiskLevel

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
        "parsed": None,
        "missing_fields": [],
        "clarification_question": None,
        "clarification_round": 0,
        "budget_check": None,
        "risk_level": "safe",
        "is_shared_ledger": False,
        "settlements": None,
        "insight_triggered": False,
        "error": None,
    }

from app.agents.state import TransactionState


async def oracle_node(state: TransactionState) -> TransactionState:
    # Report generation is intentionally scheduled outside the transaction
    # path so saving a bill is not delayed by RAG retrieval or a second LLM.
    state["insight_triggered"] = bool(state.get("parsed")) and not state.get("error")
    return state

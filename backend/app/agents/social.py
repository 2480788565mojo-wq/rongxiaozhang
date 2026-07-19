from decimal import Decimal, ROUND_HALF_UP

from app.agents.state import TransactionState


CENT = Decimal("0.01")


def _money(value: float | int | Decimal) -> Decimal:
    return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)


def minimize_debts(
    balances: dict[int, float],
    member_names: dict[int, str],
) -> list[dict]:
    """Convert member net balances into a compact set of transfers.

    Positive balances are amounts to receive and negative balances are
    amounts to pay. Values within one cent are treated as settled.
    """

    normalized = {user_id: _money(amount) for user_id, amount in balances.items()}
    total = sum(normalized.values(), start=Decimal("0.00"))
    if abs(total) > CENT:
        raise ValueError("成员净额不平衡，无法生成结算方案")

    creditors = [
        [user_id, amount]
        for user_id, amount in normalized.items()
        if amount > CENT
    ]
    debtors = [
        [user_id, -amount]
        for user_id, amount in normalized.items()
        if amount < -CENT
    ]
    creditors.sort(key=lambda item: item[1], reverse=True)
    debtors.sort(key=lambda item: item[1], reverse=True)

    settlements: list[dict] = []
    debtor_index = 0
    creditor_index = 0

    while debtor_index < len(debtors) and creditor_index < len(creditors):
        debtor_id, debt = debtors[debtor_index]
        creditor_id, credit = creditors[creditor_index]
        amount = min(debt, credit).quantize(CENT, rounding=ROUND_HALF_UP)

        if amount > CENT:
            settlements.append(
                {
                    "from_user_id": debtor_id,
                    "from_user_name": member_names.get(debtor_id, str(debtor_id)),
                    "to_user_id": creditor_id,
                    "to_user_name": member_names.get(creditor_id, str(creditor_id)),
                    "amount": float(amount),
                }
            )

        debtors[debtor_index][1] = debt - amount
        creditors[creditor_index][1] = credit - amount

        if debtors[debtor_index][1] <= CENT:
            debtor_index += 1
        if creditors[creditor_index][1] <= CENT:
            creditor_index += 1

    return settlements


async def social_node(state: TransactionState) -> TransactionState:
    if not state.get("is_shared_ledger", False):
        state["settlements"] = None
        return state

    # A new bill only updates share records. Full debt minimization is run by
    # the ledger settlement API after it aggregates all member balances.
    state["settlements"] = state.get("settlements") or []
    return state

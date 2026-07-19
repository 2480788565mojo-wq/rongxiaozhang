from decimal import Decimal

import pytest

from app.agents.social import minimize_debts
from app.services.bill_service import _equal_share_amounts


def test_minimize_debts_simple():
    result = minimize_debts(
        {1: -50, 2: 30, 3: 20},
        {1: "A", 2: "B", 3: "C"},
    )

    assert len(result) == 2
    assert sum(item["amount"] for item in result) == 50


def test_minimize_debts_equal_split():
    result = minimize_debts(
        {1: 90, 2: -30, 3: -30, 4: -30},
        {1: "A", 2: "B", 3: "C", 4: "D"},
    )

    assert len(result) == 3
    assert [item["amount"] for item in result] == [30, 30, 30]


def test_minimize_debts_returns_empty_when_settled():
    assert minimize_debts({1: 0, 2: 0}, {1: "A", 2: "B"}) == []


def test_minimize_debts_rejects_unbalanced_values():
    with pytest.raises(ValueError, match="不平衡"):
        minimize_debts({1: 10, 2: -5}, {1: "A", 2: "B"})


def test_equal_share_amounts_keep_every_cent():
    amounts = _equal_share_amounts(Decimal("100.00"), 3)

    assert amounts == [Decimal("33.33"), Decimal("33.33"), Decimal("33.34")]
    assert sum(amounts) == Decimal("100.00")

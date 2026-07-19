from unittest.mock import AsyncMock

import pytest

import app.agents.parser as parser


@pytest.mark.asyncio
async def test_parser_extracts_complete_bill(monkeypatch, transaction_state):
    monkeypatch.setattr(
        parser,
        "call_parser_llm",
        AsyncMock(
            return_value={
                "type": "expense",
                "amount": 68,
                "category": "餐饮美食",
            }
        ),
    )

    result = await parser.parser_node(transaction_state)

    assert result["parsed"]["amount"] == 68
    assert result["missing_fields"] == []
    assert result["clarification_question"] is None


@pytest.mark.asyncio
async def test_parser_asks_for_missing_amount(monkeypatch, transaction_state):
    monkeypatch.setattr(
        parser,
        "call_parser_llm",
        AsyncMock(
            return_value={
                "type": "expense",
                "amount": None,
                "category": "餐饮美食",
            }
        ),
    )

    result = await parser.parser_node(transaction_state)

    assert result["missing_fields"] == ["amount"]
    assert result["clarification_round"] == 1
    assert "金额" in result["clarification_question"]


@pytest.mark.asyncio
async def test_parser_stops_after_three_questions(monkeypatch, transaction_state):
    transaction_state["clarification_round"] = 3
    monkeypatch.setattr(
        parser,
        "call_parser_llm",
        AsyncMock(return_value={"type": "expense", "category": "餐饮美食"}),
    )

    result = await parser.parser_node(transaction_state)

    assert result["clarification_question"] is None
    assert "手动表单" in result["error"]


@pytest.mark.asyncio
async def test_parser_keeps_previous_fields_during_follow_up(
    monkeypatch,
    transaction_state,
):
    transaction_state["parsed"] = {
        "type": "expense",
        "category": "餐饮美食",
    }
    transaction_state["clarification_question"] = "请问金额是多少？"
    monkeypatch.setattr(
        parser,
        "call_parser_llm",
        AsyncMock(return_value={"amount": 68}),
    )

    result = await parser.parser_node(transaction_state)

    assert result["parsed"]["category"] == "餐饮美食"
    assert result["parsed"]["amount"] == 68
    assert result["missing_fields"] == []


@pytest.mark.asyncio
async def test_parser_hides_external_error_details(monkeypatch, transaction_state):
    monkeypatch.setattr(
        parser,
        "call_parser_llm",
        AsyncMock(side_effect=RuntimeError("secret provider detail")),
    )

    result = await parser.parser_node(transaction_state)

    assert "secret provider detail" not in result["error"]
    assert "手动记账" in result["error"]

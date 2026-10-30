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
async def test_parser_extracts_multiple_bills_in_one_input(monkeypatch, transaction_state):
    monkeypatch.setattr(
        parser,
        "call_parser_llm",
        AsyncMock(
            return_value={
                "items": [
                    {
                        "type": "expense",
                        "amount": 5,
                        "category": "餐饮美食",
                        "subcategory": "早餐",
                    },
                    {
                        "type": "expense",
                        "amount": 10,
                        "category": "餐饮美食",
                        "subcategory": "午餐",
                    },
                ]
            }
        ),
    )

    result = await parser.parser_node(transaction_state)

    assert len(result["parsed_items"]) == 2
    assert result["parsed"]["amount"] == 5
    assert result["parsed_items"][1]["amount"] == 10
    assert result["missing_fields"] == []


@pytest.mark.asyncio
async def test_parser_clarification_keeps_other_batch_items(monkeypatch, transaction_state):
    transaction_state["parsed_items"] = [
        {
            "type": "expense",
            "amount": 5,
            "category": "餐饮美食",
            "subcategory": "早餐",
            "bill_date": "2026-07-15",
        },
        {
            "type": "expense",
            "amount": None,
            "category": "餐饮美食",
            "bill_date": "2026-07-15",
        },
    ]
    transaction_state["parsed"] = transaction_state["parsed_items"][0]
    transaction_state["clarification_question"] = "第 2 笔：请问金额是多少？"
    transaction_state["clarification_item_index"] = 1
    transaction_state["clarification_round"] = 1
    monkeypatch.setattr(
        parser,
        "call_parser_llm",
        AsyncMock(return_value={"amount": 10}),
    )

    result = await parser.parser_node(transaction_state)

    assert len(result["parsed_items"]) == 2
    assert result["parsed_items"][0]["amount"] == 5
    assert result["parsed_items"][1]["amount"] == 10
    assert result["missing_fields"] == []


@pytest.mark.asyncio
async def test_parser_parsed_points_to_active_clarification_item(
    monkeypatch, transaction_state
):
    transaction_state["parsed_items"] = [
        {
            "type": "expense",
            "amount": 5,
            "category": "餐饮美食",
            "bill_date": "2026-07-15",
        },
        {
            "type": "expense",
            "amount": None,
            "category": "餐饮美食",
            "bill_date": "2026-07-15",
        },
    ]
    transaction_state["parsed"] = transaction_state["parsed_items"][0]
    transaction_state["clarification_question"] = "第 2 笔：请问金额是多少？"
    transaction_state["clarification_item_index"] = 1
    transaction_state["clarification_round"] = 1
    monkeypatch.setattr(
        parser,
        "call_parser_llm",
        # 只补充类别，金额仍缺失；追问对象仍是第 2 笔。
        AsyncMock(return_value={"category": "餐饮美食"}),
    )

    result = await parser.parser_node(transaction_state)

    assert result["clarification_item_index"] == 1
    assert result["missing_fields"] == ["amount"]
    assert result["parsed"]["amount"] is None
    assert result["parsed_items"][1]["amount"] is None


@pytest.mark.asyncio
async def test_parser_parsed_points_to_second_item_on_first_parse(
    monkeypatch, transaction_state
):
    monkeypatch.setattr(
        parser,
        "call_parser_llm",
        AsyncMock(
            return_value={
                "items": [
                    {
                        "type": "expense",
                        "amount": 5,
                        "category": "餐饮美食",
                        "bill_date": "2026-07-15",
                    },
                    {
                        "type": "expense",
                        "category": "餐饮美食",
                        "bill_date": "2026-07-15",
                    },
                ]
            }
        ),
    )

    result = await parser.parser_node(transaction_state)

    assert len(result["parsed_items"]) == 2
    assert result["missing_fields"] == ["amount"]
    assert result["clarification_item_index"] == 1
    # 前端展示的 parsed 必须是被追问的第 2 笔，而不是第 1 笔。
    assert result["parsed"] is result["parsed_items"][1]
    assert result["parsed"]["amount"] is None
    assert "第 2 笔" in result["clarification_question"]


@pytest.mark.asyncio
async def test_parser_parsed_returns_to_first_item_after_second_filled(
    monkeypatch, transaction_state
):
    transaction_state["parsed_items"] = [
        {
            "type": "expense",
            "amount": 5,
            "category": "餐饮美食",
            "bill_date": "2026-07-15",
        },
        {
            "type": "expense",
            "amount": None,
            "category": "餐饮美食",
            "bill_date": "2026-07-15",
        },
    ]
    transaction_state["parsed"] = transaction_state["parsed_items"][0]
    transaction_state["clarification_question"] = "第 2 笔：请问金额是多少？"
    transaction_state["clarification_item_index"] = 1
    transaction_state["clarification_round"] = 1
    monkeypatch.setattr(
        parser,
        "call_parser_llm",
        AsyncMock(return_value={"amount": 10}),
    )

    result = await parser.parser_node(transaction_state)

    assert result["parsed_items"][0]["amount"] == 5
    assert result["parsed_items"][1]["amount"] == 10
    assert result["missing_fields"] == []
    assert result["clarification_question"] is None
    assert result["clarification_item_index"] == 0
    # 没有待补字段后，parsed 回到第 1 笔。
    assert result["parsed"] is result["parsed_items"][0]


@pytest.mark.asyncio
async def test_parser_single_item_parsed_and_index_unchanged(
    monkeypatch, transaction_state
):
    monkeypatch.setattr(
        parser,
        "call_parser_llm",
        AsyncMock(
            return_value={
                "type": "expense",
                "category": "餐饮美食",
                "bill_date": "2026-07-15",
            }
        ),
    )

    result = await parser.parser_node(transaction_state)

    assert len(result["parsed_items"]) == 1
    assert result["missing_fields"] == ["amount"]
    assert result["clarification_item_index"] == 0
    assert result["parsed"] is result["parsed_items"][0]
    assert result["parsed"]["amount"] is None
    assert "第" not in result["clarification_question"]


@pytest.mark.asyncio
async def test_parser_parsed_points_to_third_missing_item(
    monkeypatch, transaction_state
):
    monkeypatch.setattr(
        parser,
        "call_parser_llm",
        AsyncMock(
            return_value={
                "items": [
                    {
                        "type": "expense",
                        "amount": 5,
                        "category": "餐饮美食",
                        "bill_date": "2026-07-15",
                    },
                    {
                        "type": "expense",
                        "amount": 10,
                        "category": "餐饮美食",
                        "bill_date": "2026-07-15",
                    },
                    {
                        "type": "expense",
                        "category": "餐饮美食",
                        "bill_date": "2026-07-15",
                    },
                ]
            }
        ),
    )

    result = await parser.parser_node(transaction_state)

    assert len(result["parsed_items"]) == 3
    assert result["missing_fields"] == ["amount"]
    assert result["clarification_item_index"] == 2
    assert result["parsed"] is result["parsed_items"][2]
    assert result["parsed"]["amount"] is None
    assert "第 3 笔" in result["clarification_question"]


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


@pytest.mark.asyncio
async def test_parser_includes_current_ledger_categories(monkeypatch, transaction_state):
    transaction_state["available_categories"] = [
        {"type": "expense", "category": "宠物养护", "subcategory": ""},
        {"type": "expense", "category": "宠物养护", "subcategory": "宠物食品"},
    ]
    captured: dict[str, object] = {}

    async def fake_call(messages, tools):
        captured["messages"] = messages
        return {"type": "expense", "amount": 35, "category": "宠物养护"}

    monkeypatch.setattr(parser, "call_parser_llm", fake_call)

    result = await parser.parser_node(transaction_state)

    assert result["parsed"]["category"] == "宠物养护"
    assert "宠物养护" in "\n".join(
        str(message.get("content", "")) for message in captured["messages"]
    )

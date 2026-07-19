from datetime import date
from typing import Any

from pydantic import ValidationError

from app.agents.state import TransactionState
from app.agents.tools import PARSER_SYSTEM_PROMPT, ParsedBill, get_extract_tool


REQUIRED_FIELDS = ("type", "amount", "category")
MAX_CLARIFY_ROUNDS = 3
CLARIFICATION_QUESTIONS = {
    "type": "这笔是收入还是支出？",
    "amount": "请问金额是多少？",
    "category": "这是哪类收支？例如餐饮、交通、购物或工资。",
}


async def call_parser_llm(
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
) -> dict[str, Any] | None:
    # Keep the SDK import lazy so schema and routing tests can run without
    # loading an external AI client.
    from app.core.llm import LLMClient

    client = LLMClient("deepseek")
    return await client.call_with_tools(messages, tools)


def _merge_parsed(
    previous: dict[str, Any] | None,
    current: ParsedBill,
) -> dict[str, Any]:
    merged = dict(previous or {})
    for field, value in current.model_dump().items():
        if value is not None:
            merged[field] = value

    if not merged.get("bill_date"):
        merged["bill_date"] = date.today().isoformat()
    return merged


def _build_messages(state: TransactionState) -> list[dict[str, Any]]:
    today = date.today().isoformat()
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": PARSER_SYSTEM_PROMPT},
    ]

    previous = state.get("parsed")
    if previous:
        messages.append(
            {
                "role": "system",
                "content": f"已确认的账单字段：{previous}。保留用户未修改的字段。",
            }
        )

    question = state.get("clarification_question")
    if question:
        messages.append({"role": "assistant", "content": question})

    messages.append(
        {
            "role": "user",
            "content": f"今天是 {today}。用户输入：{state['raw_input']}",
        }
    )
    return messages


async def parser_node(state: TransactionState) -> TransactionState:
    try:
        result = await call_parser_llm(
            _build_messages(state),
            [get_extract_tool()],
        )
    except Exception:
        state["error"] = "AI 解析暂时不可用，请稍后重试或使用手动记账"
        return state

    if result is None:
        state["error"] = "AI 未返回可识别的记账信息，请重试"
        return state

    try:
        parsed_bill = ParsedBill.model_validate(result)
    except ValidationError as exc:
        state["error"] = f"AI 返回的账单格式无效：{exc.errors()[0]['msg']}"
        return state

    parsed = _merge_parsed(state.get("parsed"), parsed_bill)
    missing_fields = [
        field for field in REQUIRED_FIELDS if parsed.get(field) is None
    ]
    state["parsed"] = parsed
    state["missing_fields"] = missing_fields
    state["error"] = None

    if not missing_fields:
        state["clarification_question"] = None
        return state

    current_round = state.get("clarification_round", 0)
    if current_round >= MAX_CLARIFY_ROUNDS:
        state["clarification_question"] = None
        state["error"] = "信息仍不完整，请切换到手动表单完成记账"
        return state

    missing_field = missing_fields[0]
    state["clarification_question"] = CLARIFICATION_QUESTIONS[missing_field]
    state["clarification_round"] = current_round + 1
    return state

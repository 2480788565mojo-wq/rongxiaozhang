import asyncio
import json
from datetime import date
from typing import Any

from pydantic import ValidationError

from app.agents.base import AgentBase
from app.agents.state import TransactionState
from app.agents.tools import PARSER_SYSTEM_PROMPT, ParsedBill, get_extract_tool
from app.config import get_settings


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
    if not get_settings().QWEN_API_KEY.strip():
        return None

    from app.core.llm import LLMClient

    client = LLMClient("qwen")
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

    memory = state.get("context_memory") or {}
    safe_memory = {
        key: str(memory[key])[:120]
        for key in ("last_category", "last_account")
        if memory.get(key)
    }
    if safe_memory:
        messages.append(
            {
                "role": "system",
                "content": "可参考但不得覆盖用户明确表达的会话偏好："
                + json.dumps(safe_memory, ensure_ascii=False),
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


class ParserAgent(AgentBase[ParsedBill]):
    name = "parser"

    async def run(self, state: TransactionState) -> TransactionState:
        try:
            result = await asyncio.wait_for(
                call_parser_llm(
                    _build_messages(state),
                    [get_extract_tool()],
                ),
                timeout=self.timeout_seconds,
            )
        except Exception:
            state["error"] = "AI 解析暂时不可用，请稍后重试或使用手动记账"
            self.mark_degraded(state, "记账解析模型调用失败")
            return state

        if result is None:
            state["error"] = "AI 未返回可识别的记账信息，请重试"
            self.mark_degraded(state, "记账解析模型未返回结构化结果")
            return state

        try:
            parsed_bill = ParsedBill.model_validate(result)
        except ValidationError as exc:
            state["error"] = f"AI 返回的账单格式无效：{exc.errors()[0]['msg']}"
            self.mark_degraded(state, "记账解析结果未通过字段校验")
            return state

        parsed = _merge_parsed(state.get("parsed"), parsed_bill)
        missing_fields = [
            field for field in REQUIRED_FIELDS if parsed.get(field) is None
        ]
        state["parsed"] = parsed
        state["missing_fields"] = missing_fields
        state["error"] = None
        memory = dict(state.get("context_memory") or {})
        if parsed.get("category"):
            memory["last_category"] = str(parsed["category"])[:120]
        if parsed.get("account"):
            memory["last_account"] = str(parsed["account"])[:120]
        state["context_memory"] = {
            key: value
            for key, value in memory.items()
            if key in {"last_category", "last_account"}
        }
        self.record(
            state,
            role="analysis",
            content="已提取账单字段" if not missing_fields else "账单信息不完整，需要继续追问",
            metadata={"missing_fields": missing_fields},
        )

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


async def parser_node(state: TransactionState) -> TransactionState:
    return await ParserAgent().run(state)

import asyncio
import json
import logging
from datetime import date
from typing import Any

from pydantic import ValidationError

from app.agents.base import AgentBase
from app.agents.state import TransactionState, parsed_items_from_state
from app.agents.tools import (
    PARSER_SYSTEM_PROMPT,
    ParsedBill,
    ParsedBillBatch,
    get_extract_tool,
)
from app.config import get_settings


logger = logging.getLogger(__name__)
REQUIRED_FIELDS = ("type", "amount", "category")
MAX_CLARIFY_ROUNDS = 3
CLARIFICATION_QUESTIONS = {
    "type": "这笔是收入还是支出？",
    "amount": "请问金额是多少？",
    "category": "这是哪类收支？例如餐饮、交通、购物或工资。",
}


def configured_parser_providers() -> list[str]:
    """按可用 Key 返回 Parser 的 Provider 顺序，DeepSeek 优先、Qwen 可选兜底。"""
    settings = get_settings()
    providers: list[str] = []
    if settings.DEEPSEEK_API_KEY.strip():
        providers.append("deepseek")
    if settings.QWEN_API_KEY.strip():
        providers.append("qwen")
    return providers


async def call_parser_llm(
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
) -> dict[str, Any] | None:
    # Keep the SDK import lazy so schema and routing tests can run without
    # loading an external AI client.
    providers = configured_parser_providers()
    if not providers:
        return None

    from app.core.llm import LLMClient

    last_error: Exception | None = None
    saw_empty_result = False
    for provider in providers:
        try:
            client = LLMClient(provider)  # type: ignore[arg-type]
            result = await client.call_with_tools(messages, tools)
            if result is not None:
                return result
            saw_empty_result = True
            logger.warning("Parser provider %s returned no structured result", provider)
        except Exception as exc:
            last_error = exc
            logger.warning(
                "Parser provider %s failed: %s", provider, type(exc).__name__,
                exc_info=True,
            )
    # 所有 provider 都返回空结果时是“无结构化结果”，不是旧 provider 的异常。
    if last_error is not None and not saw_empty_result:
        raise last_error
    return None


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

    previous_items = parsed_items_from_state(state)
    if previous_items:
        messages.append(
            {
                "role": "system",
                "content": (
                    "已确认的账单字段（JSON）："
                    + json.dumps(previous_items, ensure_ascii=False)
                    + "。保留用户未修改的字段；如果用户是在补充多笔中的某一笔，只返回那一笔。"
                ),
            }
        )

    available_categories = state.get("available_categories") or []
    if available_categories:
        messages.append(
            {
                "role": "system",
                "content": (
                    "当前账本可使用的自定义分类如下（JSON）。用户明确说出其中的分类时，"
                    "必须按名称原样返回；大类使用 category，细分使用 subcategory。"
                    "列表外的名称只有在没有匹配项时才可使用："
                    + json.dumps(available_categories, ensure_ascii=False)
                ),
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


class ParserAgent(AgentBase[ParsedBillBatch]):
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

        if isinstance(result, list):
            raw_items = result
        elif isinstance(result, dict):
            raw_items = result.get("items")
        else:
            raw_items = None
        if not isinstance(raw_items, list) or not raw_items:
            raw_items = [result]

        try:
            if len(raw_items) == 1:
                parsed_items = [ParsedBill.model_validate(raw_items[0])]
            else:
                parsed_items = ParsedBillBatch.model_validate(
                    {"items": raw_items}
                ).items
        except ValidationError as exc:
            state["error"] = f"AI 返回的账单格式无效：{exc.errors()[0]['msg']}"
            self.mark_degraded(state, "记账解析结果未通过字段校验")
            return state

        previous_items = parsed_items_from_state(state)
        clarify_index = state.get("clarification_item_index", 0)
        is_clarification = bool(state.get("clarification_question"))
        # 追问只补当前缺失的那一笔；其余已经解析好的账单必须保留。
        if len(parsed_items) == 1 and previous_items:
            if is_clarification and 0 <= clarify_index < len(previous_items):
                merged_items = list(previous_items)
                merged = _merge_parsed(
                    merged_items[clarify_index],
                    parsed_items[0],
                )
                merged_items[clarify_index] = merged
                parsed_items = [
                    ParsedBill.model_validate(item) for item in merged_items
                ]
            elif len(previous_items) == 1:
                merged = _merge_parsed(previous_items[0], parsed_items[0])
                parsed_items = [ParsedBill.model_validate(merged)]

        item_dicts: list[dict] = []
        for item in parsed_items:
            data = item.model_dump()
            if not data.get("bill_date"):
                data["bill_date"] = date.today().isoformat()
            item_dicts.append(data)

        missing_by_item: list[tuple[int, list[str]]] = []
        for index, data in enumerate(item_dicts):
            missing = [
                field for field in REQUIRED_FIELDS if data.get(field) is None
            ]
            if missing:
                missing_by_item.append((index, missing))

        active_index = missing_by_item[0][0] if missing_by_item else 0
        state["parsed_items"] = item_dicts
        # parsed 必须指向当前追问项；否则前端会展示第 1 笔，却让用户补第 2 笔。
        state["parsed"] = item_dicts[active_index] if item_dicts else None
        state["missing_fields"] = (
            missing_by_item[0][1] if missing_by_item else []
        )
        state["clarification_item_index"] = active_index
        state["error"] = None

        memory = dict(state.get("context_memory") or {})
        for item in item_dicts:
            if item.get("category"):
                memory["last_category"] = str(item["category"])[:120]
            if item.get("account"):
                memory["last_account"] = str(item["account"])[:120]
        state["context_memory"] = {
            key: value
            for key, value in memory.items()
            if key in {"last_category", "last_account"}
        }
        self.record(
            state,
            role="analysis",
            content=(
                f"已提取 {len(item_dicts)} 笔账单"
                if not missing_by_item
                else f"已提取 {len(item_dicts)} 笔账单，其中 1 笔信息不完整"
            ),
            metadata={
                "count": len(item_dicts),
                "missing_fields": state["missing_fields"],
            },
        )

        if not missing_by_item:
            state["clarification_question"] = None
            return state

        current_round = state.get("clarification_round", 0)
        if current_round >= MAX_CLARIFY_ROUNDS:
            state["clarification_question"] = None
            state["error"] = "信息仍不完整，请切换到手动表单完成记账"
            return state

        missing_index, missing_fields = missing_by_item[0]
        missing_field = missing_fields[0]
        question = CLARIFICATION_QUESTIONS[missing_field]
        if len(item_dicts) > 1:
            question = f"第 {missing_index + 1} 笔：{question}"
        state["clarification_question"] = question
        state["clarification_round"] = current_round + 1
        return state


async def parser_node(state: TransactionState) -> TransactionState:
    return await ParserAgent().run(state)

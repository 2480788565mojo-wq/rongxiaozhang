import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, ValidationError

from app.agents.state import AgentMessage, TransactionState
from app.config import get_settings


logger = logging.getLogger(__name__)
OutputModel = TypeVar("OutputModel", bound=BaseModel)


class AgentBase(ABC, Generic[OutputModel]):
    """Shared, failure-tolerant runtime for LLM-backed agents."""

    name: str
    timeout_seconds = 12.0
    max_attempts = 2

    def __init__(self, provider: str = "deepseek") -> None:
        self.provider = provider

    @property
    def is_configured(self) -> bool:
        settings = get_settings()
        if self.provider == "deepseek":
            return bool(settings.DEEPSEEK_API_KEY.strip())
        if self.provider == "qwen":
            return bool(settings.QWEN_API_KEY.strip())
        return False

    async def call_tool(
        self,
        *,
        messages: list[dict[str, Any]],
        tool: dict[str, Any],
        output_model: type[OutputModel],
    ) -> OutputModel | None:
        if not self.is_configured:
            return None

        from app.core.llm import LLMClient

        last_error: Exception | None = None
        for attempt in range(self.max_attempts):
            try:
                client = LLMClient(self.provider)  # type: ignore[arg-type]
                raw = await asyncio.wait_for(
                    client.call_with_tools(
                        messages,
                        [tool],
                        tool_choice="required",
                    ),
                    timeout=self.timeout_seconds,
                )
                if raw is None:
                    return None
                return output_model.model_validate(raw)
            except (TimeoutError, ValidationError, ValueError, KeyError) as exc:
                last_error = exc
            except Exception as exc:  # Provider/network failures must degrade safely.
                last_error = exc
            if attempt + 1 < self.max_attempts:
                await asyncio.sleep(0.15 * (attempt + 1))

        logger.warning("%s Agent 调用失败，使用降级逻辑: %s", self.name, type(last_error).__name__)
        return None

    def record(
        self,
        state: TransactionState,
        *,
        role: Literal["decision", "analysis", "recommendation", "fallback"],
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        messages = list(state.get("agent_messages") or [])
        messages.append(
            {
                "agent": self.name,
                "role": role,
                "content": content[:1000],
                "metadata": metadata or {},
            }
        )
        state["agent_messages"] = messages[-20:]

    def mark_degraded(self, state: TransactionState, reason: str) -> None:
        degraded = list(state.get("degraded_agents") or [])
        if self.name not in degraded:
            degraded.append(self.name)
        state["degraded_agents"] = degraded
        self.record(state, role="fallback", content=reason)

    @abstractmethod
    async def run(self, state: TransactionState) -> TransactionState:
        raise NotImplementedError

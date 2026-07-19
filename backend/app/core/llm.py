import json
from typing import Any, Literal, TypeVar

from openai import AsyncOpenAI
from pydantic import BaseModel

from app.config import get_settings


settings = get_settings()
Provider = Literal["deepseek", "qwen"]
ModelType = TypeVar("ModelType", bound=BaseModel)


class LLMClient:
    PROVIDERS: dict[Provider, dict[str, str]] = {
        "deepseek": {
            "base_url": settings.DEEPSEEK_BASE_URL,
            "api_key": settings.DEEPSEEK_API_KEY,
            "model": settings.DEEPSEEK_MODEL,
        },
        "qwen": {
            "base_url": settings.QWEN_BASE_URL,
            "api_key": settings.QWEN_API_KEY,
            "model": settings.QWEN_MODEL,
        },
    }

    def __init__(self, provider: Provider):
        config = self.PROVIDERS[provider]
        self.provider = provider
        self.model = config["model"]
        self.client = AsyncOpenAI(
            base_url=config["base_url"],
            api_key=config["api_key"] or "not-configured",
        )

    async def call_with_tools(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        tool_choice: str = "auto",
    ) -> dict[str, Any] | None:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools,
            tool_choice=tool_choice,
        )
        tool_calls = response.choices[0].message.tool_calls
        if not tool_calls:
            return None
        return json.loads(tool_calls[0].function.arguments)

    async def chat(
        self,
        messages: list[dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""

    @staticmethod
    def pydantic_to_openai_tool(
        model_cls: type[ModelType],
        name: str,
        description: str,
    ) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": model_cls.model_json_schema(),
            },
        }

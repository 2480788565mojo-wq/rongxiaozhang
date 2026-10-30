"""Parser Provider 路由与 failover 测试。

这些测试完全不触网：LLMClient 被替换成记录 provider 的假工厂，
get_settings 被替换成简单配置替身。
"""

from types import SimpleNamespace
from typing import Any

import pytest

import app.agents.parser as parser


MESSAGES = [{"role": "user", "content": "午饭68块"}]
TOOLS = [{"type": "function", "function": {"name": "extract_bill"}}]
QWEN_RESULT = {"type": "expense", "amount": 68, "category": "餐饮美食"}
DEEPSEEK_RESULT = {"type": "expense", "amount": 88, "category": "交通"}


def make_settings(qwen: str = "", deepseek: str = "") -> SimpleNamespace:
    """构造只带 Key 字段的 settings 替身。"""
    return SimpleNamespace(QWEN_API_KEY=qwen, DEEPSEEK_API_KEY=deepseek)


def use_settings(monkeypatch, *, qwen: str = "", deepseek: str = "") -> None:
    monkeypatch.setattr(
        parser,
        "get_settings",
        lambda: make_settings(qwen=qwen, deepseek=deepseek),
    )


class FakeClient:
    """记录调用的假 LLMClient 实例。"""

    def __init__(self, provider: str, behavior: Any):
        self.provider = provider
        self.behavior = behavior
        self.calls: list[tuple[list[dict[str, Any]], list[dict[str, Any]]]] = []

    async def call_with_tools(self, messages, tools):
        self.calls.append((messages, tools))
        if isinstance(self.behavior, BaseException):
            raise self.behavior
        return self.behavior


class FakeLLMClientFactory:
    """替代 app.core.llm.LLMClient：按 provider 返回预置结果的假客户端。"""

    def __init__(self, behaviors: dict[str, Any] | None = None):
        self.behaviors = behaviors or {}
        self.providers: list[str] = []
        self.clients: list[FakeClient] = []

    def __call__(self, provider: str) -> FakeClient:
        self.providers.append(provider)
        client = FakeClient(provider, self.behaviors.get(provider))
        self.clients.append(client)
        return client


def install_fake_llm(
    monkeypatch,
    behaviors: dict[str, Any] | None = None,
) -> FakeLLMClientFactory:
    import app.core.llm as llm_module

    factory = FakeLLMClientFactory(behaviors)
    monkeypatch.setattr(llm_module, "LLMClient", factory)
    return factory


def forbid_llm_client(monkeypatch) -> None:
    """任何 LLMClient 构造都会立刻让测试失败。"""
    import app.core.llm as llm_module

    def explode(provider: str):
        raise AssertionError(
            f"未配置 Key 时不应构造 LLMClient，实际构造了 {provider!r}"
        )

    monkeypatch.setattr(llm_module, "LLMClient", explode)


async def test_no_keys_returns_none_without_constructing_client(monkeypatch):
    use_settings(monkeypatch, qwen="", deepseek="")
    forbid_llm_client(monkeypatch)

    assert parser.configured_parser_providers() == []
    assert await parser.call_parser_llm(MESSAGES, TOOLS) is None


async def test_whitespace_only_keys_count_as_missing(monkeypatch):
    use_settings(monkeypatch, qwen="   ", deepseek="\t")
    forbid_llm_client(monkeypatch)

    assert parser.configured_parser_providers() == []
    assert await parser.call_parser_llm(MESSAGES, TOOLS) is None


async def test_keys_are_stripped_before_use(monkeypatch):
    use_settings(monkeypatch, qwen="  qwen-key  ", deepseek="  deepseek-key ")
    factory = install_fake_llm(monkeypatch, {"qwen": QWEN_RESULT})

    assert parser.configured_parser_providers() == ["qwen", "deepseek"]
    assert await parser.call_parser_llm(MESSAGES, TOOLS) == QWEN_RESULT
    assert factory.providers == ["qwen"]


def test_provider_order_is_qwen_then_deepseek(monkeypatch):
    use_settings(monkeypatch, qwen="qwen-key", deepseek="deepseek-key")
    assert parser.configured_parser_providers() == ["qwen", "deepseek"]


@pytest.mark.parametrize(
    "qwen_key,deepseek_key,expected",
    [
        ("qwen-key", "", ["qwen"]),
        ("", "deepseek-key", ["deepseek"]),
        ("qwen-key", "deepseek-key", ["qwen", "deepseek"]),
        ("", "", []),
    ],
)
def test_configured_provider_order_matrix(monkeypatch, qwen_key, deepseek_key, expected):
    use_settings(monkeypatch, qwen=qwen_key, deepseek=deepseek_key)
    assert parser.configured_parser_providers() == expected


async def test_qwen_only_uses_qwen(monkeypatch):
    use_settings(monkeypatch, qwen="qwen-key", deepseek="")
    factory = install_fake_llm(monkeypatch, {"qwen": QWEN_RESULT})

    result = await parser.call_parser_llm(MESSAGES, TOOLS)

    assert result == QWEN_RESULT
    assert factory.providers == ["qwen"]
    assert factory.clients[0].calls == [(MESSAGES, TOOLS)]


async def test_deepseek_only_uses_deepseek(monkeypatch):
    """回归：只配置 DeepSeek 时不能静默失去 AI 解析。"""
    use_settings(monkeypatch, qwen="", deepseek="deepseek-key")
    factory = install_fake_llm(monkeypatch, {"deepseek": DEEPSEEK_RESULT})

    result = await parser.call_parser_llm(MESSAGES, TOOLS)

    assert result == DEEPSEEK_RESULT
    assert factory.providers == ["deepseek"]
    assert factory.clients[0].calls == [(MESSAGES, TOOLS)]


async def test_qwen_error_falls_back_to_deepseek(monkeypatch):
    use_settings(monkeypatch, qwen="qwen-key", deepseek="deepseek-key")
    factory = install_fake_llm(
        monkeypatch,
        {"qwen": RuntimeError("qwen down"), "deepseek": DEEPSEEK_RESULT},
    )

    result = await parser.call_parser_llm(MESSAGES, TOOLS)

    assert result == DEEPSEEK_RESULT
    assert factory.providers == ["qwen", "deepseek"]
    assert len(factory.clients[0].calls) == 1
    assert len(factory.clients[1].calls) == 1


async def test_fallback_logs_primary_provider_failure(monkeypatch, caplog):
    use_settings(monkeypatch, qwen="qwen-key", deepseek="deepseek-key")
    install_fake_llm(
        monkeypatch,
        {"qwen": RuntimeError("qwen down"), "deepseek": DEEPSEEK_RESULT},
    )

    with caplog.at_level("WARNING", logger="app.agents.parser"):
        result = await parser.call_parser_llm(MESSAGES, TOOLS)

    assert result == DEEPSEEK_RESULT
    assert "qwen" in caplog.text
    assert "RuntimeError" in caplog.text


async def test_error_then_empty_result_returns_none_not_stale_error(monkeypatch):
    use_settings(monkeypatch, qwen="qwen-key", deepseek="deepseek-key")
    install_fake_llm(
        monkeypatch,
        {"qwen": RuntimeError("qwen down"), "deepseek": None},
    )

    assert await parser.call_parser_llm(MESSAGES, TOOLS) is None


async def test_qwen_none_falls_back_to_deepseek(monkeypatch):
    use_settings(monkeypatch, qwen="qwen-key", deepseek="deepseek-key")
    factory = install_fake_llm(
        monkeypatch,
        {"qwen": None, "deepseek": DEEPSEEK_RESULT},
    )

    result = await parser.call_parser_llm(MESSAGES, TOOLS)

    assert result == DEEPSEEK_RESULT
    assert factory.providers == ["qwen", "deepseek"]


async def test_all_providers_return_none_returns_none(monkeypatch):
    use_settings(monkeypatch, qwen="qwen-key", deepseek="deepseek-key")
    factory = install_fake_llm(monkeypatch, {"qwen": None, "deepseek": None})

    assert await parser.call_parser_llm(MESSAGES, TOOLS) is None
    assert factory.providers == ["qwen", "deepseek"]


async def test_all_providers_raise_raises_last_error(monkeypatch):
    use_settings(monkeypatch, qwen="qwen-key", deepseek="deepseek-key")
    qwen_error = RuntimeError("qwen down")
    deepseek_error = RuntimeError("deepseek down")
    factory = install_fake_llm(
        monkeypatch,
        {"qwen": qwen_error, "deepseek": deepseek_error},
    )

    with pytest.raises(RuntimeError) as excinfo:
        await parser.call_parser_llm(MESSAGES, TOOLS)

    assert excinfo.value is deepseek_error
    assert factory.providers == ["qwen", "deepseek"]
    assert len(factory.clients) == 2

from app.agents import parser
from app.services import insight_service


def test_insight_prefers_deepseek(monkeypatch):
    monkeypatch.setattr(insight_service.settings, "DEEPSEEK_API_KEY", "deepseek-key", raising=False)
    monkeypatch.setattr(insight_service.settings, "QWEN_API_KEY", "qwen-key", raising=False)

    assert insight_service.configured_insight_provider() == "deepseek"


def test_insight_falls_back_to_qwen(monkeypatch):
    monkeypatch.setattr(insight_service.settings, "DEEPSEEK_API_KEY", "", raising=False)
    monkeypatch.setattr(insight_service.settings, "QWEN_API_KEY", "qwen-key", raising=False)

    assert insight_service.configured_insight_provider() == "qwen"


def test_insight_has_no_provider_without_keys(monkeypatch):
    monkeypatch.setattr(insight_service.settings, "DEEPSEEK_API_KEY", "", raising=False)
    monkeypatch.setattr(insight_service.settings, "QWEN_API_KEY", "", raising=False)

    assert insight_service.configured_insight_provider() is None


def test_parser_prefers_deepseek_then_qwen(monkeypatch):
    settings = parser.get_settings()
    monkeypatch.setattr(settings, "DEEPSEEK_API_KEY", "deepseek-key", raising=False)
    monkeypatch.setattr(settings, "QWEN_API_KEY", "qwen-key", raising=False)

    assert parser.configured_parser_providers() == ["deepseek", "qwen"]

from unittest.mock import AsyncMock

import pytest

import app.agents.guardian as guardian_module
from app.agents.advisor import AdvisorAgent
from app.agents.graph import (
    route_after_advisor,
    route_after_guardian_collaboration,
    route_after_guardian_review,
    route_after_orchestrator,
    route_after_parser_collaboration,
)
from app.agents.guardian import GuardianAgent
from app.agents.orchestrator import OrchestratorAgent
from app.agents.state import new_transaction_state
from app.agents.tools import GuardianOpinion


def make_state(raw_input: str = "午餐30元") -> dict:
    return new_transaction_state(
        raw_input=raw_input,
        user_id=1,
        ledger_id=9,
        session_id="collaboration-test",
    )


@pytest.mark.asyncio
async def test_orchestrator_fallback_selects_quick_route_for_simple_bill(monkeypatch):
    agent = OrchestratorAgent()
    monkeypatch.setattr(agent, "call_tool", AsyncMock(return_value=None))

    result = await agent.run(make_state("午餐30元"))

    assert result["intent"] == "transaction"
    assert result["route_mode"] == "quick"
    assert "orchestrator" not in result["degraded_agents"]
    agent.call_tool.assert_not_awaited()


@pytest.mark.asyncio
async def test_orchestrator_fallback_selects_deep_route_for_large_bill(monkeypatch):
    agent = OrchestratorAgent()
    monkeypatch.setattr(agent, "call_tool", AsyncMock(return_value=None))

    result = await agent.run(make_state("买手机花了5000元"))

    assert result["route_mode"] == "deep"


@pytest.mark.asyncio
async def test_orchestrator_routes_monthly_spending_question_to_advisor(monkeypatch):
    agent = OrchestratorAgent()
    monkeypatch.setattr(agent, "call_tool", AsyncMock(return_value=None))

    result = await agent.run(make_state("这个月我花多了吗？"))

    assert result["intent"] == "advice"
    assert result["route_mode"] == "deep"
    agent.call_tool.assert_not_awaited()


def test_agent_message_history_is_bounded_and_truncated():
    state = make_state()
    agent = OrchestratorAgent()

    for index in range(25):
        agent.record(state, role="analysis", content=f"{index}:" + "x" * 1500)

    assert len(state["agent_messages"]) == 20
    assert len(state["agent_messages"][-1]["content"]) == 1000


@pytest.mark.asyncio
async def test_guardian_llm_opinion_cannot_downgrade_system_risk(monkeypatch):
    async def calculated(state, db=None):
        state["risk_level"] = "blocked"
        state["budget_check"] = {
            "category": "购物消费",
            "percentage": 120,
            "remaining": -200,
        }
        return state

    monkeypatch.setattr(guardian_module, "_calculate_budget_risk", calculated)
    agent = GuardianAgent()
    monkeypatch.setattr(
        agent,
        "call_tool",
        AsyncMock(
            return_value=GuardianOpinion(
                assessment="模型认为可以买",
                suggestion="这是非权威建议",
                needs_advisor=False,
            )
        ),
    )
    state = make_state("买手机5000元")
    state["parsed"] = {
        "type": "expense",
        "amount": 5000,
        "category": "购物消费",
        "bill_date": "2026-07-23",
    }

    result = await agent.run(state)

    assert result["risk_level"] == "blocked"
    assert result["budget_check"]["percentage"] == 120


@pytest.mark.asyncio
async def test_guardian_ai_can_escalate_rule_risk(monkeypatch):
    async def calculated(state, db=None):
        state["risk_level"] = "safe"
        state["budget_check"] = {
            "category": "购物消费",
            "percentage": 40,
            "remaining": 600,
        }
        return state

    monkeypatch.setattr(guardian_module, "_calculate_budget_risk", calculated)
    agent = GuardianAgent()
    monkeypatch.setattr(
        agent,
        "call_tool",
        AsyncMock(
            return_value=GuardianOpinion(
                recommended_risk_level="warning",
                confidence=0.85,
                assessment="该笔消费相对当前场景金额较大",
                suggestion="建议确认必要性",
                needs_advisor=True,
            )
        ),
    )
    state = make_state("买了一个比较贵的电子产品")
    state["route_mode"] = "deep"
    state["parsed"] = {
        "type": "expense",
        "amount": 800,
        "category": "购物消费",
        "bill_date": "2026-07-23",
    }

    result = await agent.run(state)

    assert result["rule_risk_level"] == "safe"
    assert result["ai_risk_level"] == "warning"
    assert result["risk_level"] == "warning"
    assert result["budget_check"]["risk_level"] == "warning"


@pytest.mark.asyncio
async def test_advisor_failure_returns_bounded_deterministic_recommendation(monkeypatch):
    state = make_state("买手机5000元")
    state["risk_level"] = "blocked"
    state["budget_check"] = {
        "category": "购物消费",
        "percentage": 120,
        "remaining": -200,
    }
    agent = AdvisorAgent()
    monkeypatch.setattr(agent, "call_tool", AsyncMock(return_value=None))

    result = await agent.run(state)

    assert result["advisor_recommendation"]["urgency"] == "high"
    assert len(result["advisor_recommendation"]["actions"]) <= 3
    assert result["debate_round"] == 1
    assert "advisor" in result["degraded_agents"]


@pytest.mark.asyncio
async def test_advisor_uses_bounded_financial_snapshot_when_model_fails(monkeypatch):
    state = make_state("这个月我花多了吗？")
    state["context_memory"] = {
        "financial_snapshot": {
            "income": 5000,
            "expense": 3200,
            "budget_used_percentage": 80,
            "top_categories": [{"category": "餐饮美食", "amount": 1200}],
        }
    }
    agent = AdvisorAgent()
    monkeypatch.setattr(agent, "call_tool", AsyncMock(return_value=None))

    result = await agent.run(state)

    assert "3200.00" in result["advisor_recommendation"]["summary"]
    assert "餐饮美食" in result["advisor_recommendation"]["actions"][0]


def test_collaboration_routes_keep_fast_path_and_bound_debate():
    assert route_after_orchestrator({"intent": "advice"}) == "advisor"
    assert route_after_orchestrator({"intent": "transaction"}) == "parser"
    assert route_after_parser_collaboration({"route_mode": "quick"}) == "oracle"
    assert route_after_parser_collaboration({"route_mode": "standard"}) == "guardian"
    assert route_after_guardian_collaboration({"risk_level": "blocked"}) == "advisor"
    assert route_after_advisor({"intent": "transaction"}) == "guardian_review"
    assert route_after_advisor({"intent": "advice"}) == "oracle"
    assert route_after_guardian_review({"is_shared_ledger": True}) == "social_ledger"

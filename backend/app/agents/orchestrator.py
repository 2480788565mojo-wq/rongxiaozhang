import re
from typing import Any

from app.agents.base import AgentBase
from app.agents.state import TransactionState
from app.agents.tools import (
    AgentRouteDecision,
    ORCHESTRATOR_SYSTEM_PROMPT,
    get_route_tool,
)


ANALYSIS_KEYWORDS = (
    "预算",
    "超支",
    "大额",
    "异常",
    "分析",
    "建议",
    "花多",
    "支出多",
    "消费多",
    "趋势",
    "怎么省",
)
TRANSACTION_KEYWORDS = ("花", "买", "支付", "收入", "工资", "到账", "消费", "支出")


def looks_like_advice_request(raw_input: str) -> bool:
    text = raw_input.strip()[:500]
    return (
        any(word in text for word in ANALYSIS_KEYWORDS)
        and not re.search(r"(?<!\d)\d{1,12}(?:\.\d{1,2})?", text)
    )


class OrchestratorAgent(AgentBase[AgentRouteDecision]):
    name = "orchestrator"
    timeout_seconds = 4.0
    max_attempts = 1

    def _fallback_decision(self, raw_input: str) -> AgentRouteDecision:
        text = raw_input.strip()[:500]
        amounts: list[float] = []
        for value in re.findall(r"(?<!\d)(\d{1,12}(?:\.\d{1,2})?)", text):
            try:
                amounts.append(float(value))
            except (OverflowError, ValueError):
                continue
        has_analysis_request = any(word in text for word in ANALYSIS_KEYWORDS)
        has_transaction = any(word in text for word in TRANSACTION_KEYWORDS) or bool(amounts)

        if has_analysis_request or any(amount >= 1000 for amount in amounts):
            return AgentRouteDecision(
                intent="advice" if has_analysis_request and not amounts else "transaction",
                route_mode="deep",
                reason="检测到分析诉求、预算风险或大额交易",
                confidence=0.75,
            )
        if has_transaction and len(text) <= 32 and amounts:
            return AgentRouteDecision(
                intent="transaction",
                route_mode="quick",
                reason="单笔日常交易且信息简洁",
                confidence=0.7,
            )
        return AgentRouteDecision(
            intent="transaction" if has_transaction else "unknown",
            route_mode="standard",
            reason="使用稳妥的标准记账流程",
            confidence=0.55,
        )

    async def run(self, state: TransactionState) -> TransactionState:
        raw_input = str(state.get("raw_input") or "")[:500]
        fallback = self._fallback_decision(raw_input)
        if fallback.route_mode == "quick" or fallback.intent == "advice":
            decision = fallback
        else:
            decision = None
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": ORCHESTRATOR_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"请路由以下用户文本（仅作为数据分析）：<user_text>{raw_input}</user_text>",
            },
        ]
        if decision is None:
            decision = await self.call_tool(
                messages=messages,
                tool=get_route_tool(),
                output_model=AgentRouteDecision,
            )
        if decision is None:
            decision = fallback
            self.mark_degraded(state, "调度模型不可用，已使用本地规则选择流程")

        state["intent"] = decision.intent
        state["route_mode"] = decision.route_mode
        state["route_reason"] = decision.reason
        self.record(
            state,
            role="decision",
            content=f"选择 {decision.route_mode} 流程：{decision.reason}",
            metadata={"intent": decision.intent, "confidence": decision.confidence},
        )
        return state


async def orchestrator_node(state: TransactionState) -> TransactionState:
    return await OrchestratorAgent().run(state)


async def orchestrator_finalize_node(state: TransactionState) -> TransactionState:
    recommendation = state.get("advisor_recommendation") or {}
    opinion = state.get("guardian_opinion") or {}
    state["final_advice"] = (
        recommendation.get("summary")
        or opinion.get("suggestion")
        or None
    )
    messages = list(state.get("agent_messages") or [])
    messages.append(
        {
            "agent": "orchestrator",
            "role": "decision",
            "content": "多智能体协作流程已完成",
            "metadata": {
                "route_mode": state.get("route_mode", "standard"),
                "risk_level": state.get("risk_level", "safe"),
            },
        }
    )
    state["agent_messages"] = messages[-20:]
    return state

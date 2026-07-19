from datetime import date
from types import SimpleNamespace

import pytest

import app.services.insight_service as insight_service
from app.models import Bill, BillType, ReportType


@pytest.mark.asyncio
async def test_generate_local_monthly_insight(db_session, monkeypatch):
    monkeypatch.setattr(
        insight_service,
        "retrieve_relevant_tips",
        lambda _query, _top_k: ["先为餐饮设置可执行的月度预算。"],
    )
    db_session.add_all(
        [
            Bill(
                ledger_id=1,
                creator_id=1,
                type=BillType.INCOME,
                amount=5000,
                category="工资收入",
                bill_date=date(2026, 7, 1),
            ),
            Bill(
                ledger_id=1,
                creator_id=1,
                type=BillType.EXPENSE,
                amount=680,
                category="餐饮美食",
                bill_date=date(2026, 7, 10),
            ),
        ]
    )
    await db_session.flush()

    insight = await insight_service.generate_insight_report(
        db_session,
        user_id=1,
        ledger_id=1,
        report_type=ReportType.MONTHLY,
        today=date(2026, 7, 15),
    )

    assert "收入 ¥5000.00" in insight.content
    assert "支出 ¥680.00" in insight.content
    assert any("餐饮美食" in item for item in insight.key_findings)
    assert insight.suggested_actions == ["先为餐饮设置可执行的月度预算。"]


@pytest.mark.asyncio
async def test_generate_insight_can_use_structured_llm_result(db_session, monkeypatch):
    monkeypatch.setattr(insight_service, "retrieve_relevant_tips", lambda *_: [])
    client = SimpleNamespace(
        call_with_tools=lambda *_args, **_kwargs: None,
    )

    async def call_with_tools(*_args, **_kwargs):
        return {
            "content": "本月消费结构稳定。",
            "key_findings": ["餐饮支出可控"],
            "suggested_actions": ["保持每周复盘"],
        }

    client.call_with_tools = call_with_tools
    insight = await insight_service.generate_insight_report(
        db_session,
        user_id=1,
        ledger_id=1,
        report_type=ReportType.ON_DEMAND,
        today=date(2026, 7, 15),
        llm_client=client,
    )
    assert insight.content == "本月消费结构稳定。"
    assert insight.key_findings == ["餐饮支出可控"]

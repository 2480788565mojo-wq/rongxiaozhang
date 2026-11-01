import asyncio
import json
import uuid
from datetime import date, timedelta
from typing import Any

from redis.asyncio import Redis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.config import get_settings
from app.models import Bill, BillType, Insight, ReportType
from app.rag.retriever import retrieve_relevant_tips


INSIGHT_QUEUE = "insight:generation:queue"
settings = get_settings()


def configured_insight_provider() -> str | None:
    """Prefer DeepSeek when configured; keep Qwen as a legacy fallback."""
    if settings.DEEPSEEK_API_KEY.strip():
        return "deepseek"
    if settings.QWEN_API_KEY.strip():
        return "qwen"
    return None


QUEUE_PUSH_IF_AVAILABLE_SCRIPT = """
local size = redis.call('LLEN', KEYS[1])
if size >= tonumber(ARGV[1]) then
    return 0
end
return redis.call('RPUSH', KEYS[1], ARGV[2])
"""


class InsightQueueFull(Exception):
    pass


class InsightDraft(BaseModel):
    content: str = Field(min_length=1, max_length=4000)
    key_findings: list[str] = Field(default_factory=list, max_length=5)
    suggested_actions: list[str] = Field(default_factory=list, max_length=5)


def _report_bounds(report_type: ReportType, today: date) -> tuple[date, date, str]:
    if report_type == ReportType.WEEKLY:
        start = today - timedelta(days=6)
        return start, today + timedelta(days=1), f"{start} 至 {today}"
    start = today.replace(day=1)
    if start.month == 12:
        end = date(start.year + 1, 1, 1)
    else:
        end = date(start.year, start.month + 1, 1)
    return start, end, f"{start.year}年{start.month}月"


async def _report_snapshot(
    db: AsyncSession,
    ledger_id: int,
    report_type: ReportType,
    today: date,
) -> dict[str, Any]:
    start, end, period = _report_bounds(report_type, today)
    totals_result = await db.execute(
        select(Bill.type, func.coalesce(func.sum(Bill.amount), 0))
        .where(
            Bill.ledger_id == ledger_id,
            Bill.bill_date >= start,
            Bill.bill_date < end,
        )
        .group_by(Bill.type)
    )
    totals = {bill_type: float(amount) for bill_type, amount in totals_result.all()}
    categories_result = await db.execute(
        select(Bill.category, func.sum(Bill.amount))
        .where(
            Bill.ledger_id == ledger_id,
            Bill.type == BillType.EXPENSE,
            Bill.bill_date >= start,
            Bill.bill_date < end,
        )
        .group_by(Bill.category)
        .order_by(func.sum(Bill.amount).desc())
        .limit(5)
    )
    categories = [
        {"category": category, "amount": round(float(amount), 2)}
        for category, amount in categories_result.all()
    ]
    income = round(totals.get(BillType.INCOME, 0.0), 2)
    expense = round(totals.get(BillType.EXPENSE, 0.0), 2)
    return {
        "period": period,
        "income": income,
        "expense": expense,
        "balance": round(income - expense, 2),
        "categories": categories,
    }


def _fallback_draft(snapshot: dict[str, Any], tips: list[str]) -> InsightDraft:
    top = snapshot["categories"][0] if snapshot["categories"] else None
    if top:
        top_sentence = f"最大支出分类是{top['category']}，共 ¥{top['amount']:.2f}。"
        key_findings = [
            f"{snapshot['period']}支出 ¥{snapshot['expense']:.2f}",
            f"{top['category']}是支出最多的分类",
            f"本期结余 ¥{snapshot['balance']:.2f}",
        ]
    else:
        top_sentence = "本期还没有支出分类数据。"
        key_findings = [f"{snapshot['period']}暂无支出记录"]

    actions = tips[:3]
    if not actions:
        actions = ["继续完整记录每笔收支，积累数据后再观察消费趋势。"]
    content = (
        f"{snapshot['period']}收入 ¥{snapshot['income']:.2f}，"
        f"支出 ¥{snapshot['expense']:.2f}，结余 ¥{snapshot['balance']:.2f}。"
        f"{top_sentence}建议先关注金额最大的支出分类，并结合预算逐步调整。"
    )
    return InsightDraft(
        content=content,
        key_findings=key_findings,
        suggested_actions=actions,
    )


async def generate_insight_report(
    db: AsyncSession,
    *,
    user_id: int,
    ledger_id: int,
    report_type: ReportType,
    today: date | None = None,
    llm_client: Any | None = None,
) -> Insight:
    snapshot = await _report_snapshot(
        db,
        ledger_id,
        report_type,
        today or date.today(),
    )
    query = "消费预算建议 " + " ".join(
        item["category"] for item in snapshot["categories"]
    )
    try:
        tips = await asyncio.to_thread(retrieve_relevant_tips, query, 3)
    except Exception:
        # Chroma or the embedding model can be temporarily unavailable while
        # the core report should still be generated from accounting data.
        tips = []

    draft = _fallback_draft(snapshot, tips)
    client = llm_client
    provider = configured_insight_provider()
    if client is None and provider is not None:
        # Keep the external SDK optional for local/offline report generation.
        from app.core.llm import LLMClient

        client = LLMClient(provider)
    if client is not None:
        tool = {
            "type": "function",
            "function": {
                "name": "write_finance_insight",
                "description": "根据账本统计与理财知识生成简洁、审慎的中文财务洞察",
                "parameters": InsightDraft.model_json_schema(),
            },
        }
        messages = [
            {
                "role": "system",
                "content": (
                    "你是荣小账财务洞察助手。只基于提供的数据分析，不虚构；"
                    "不承诺收益，不提供高风险投资指令；语气友好、结论具体。"
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {"statistics": snapshot, "reference_tips": tips},
                    ensure_ascii=False,
                ),
            },
        ]
        try:
            result = await client.call_with_tools(messages, [tool], "required")
            if result:
                draft = InsightDraft.model_validate(result)
        except Exception:
            # External model failure falls back to a deterministic local
            # report so the queued job always reaches a useful end state.
            pass

    insight = Insight(
        user_id=user_id,
        ledger_id=ledger_id,
        report_type=report_type,
        content=draft.content,
        key_findings=draft.key_findings,
        suggested_actions=draft.suggested_actions,
    )
    db.add(insight)
    await db.flush()
    return insight


async def list_insights(
    db: AsyncSession,
    user_id: int,
    *,
    ledger_id: int | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Insight], int]:
    conditions = [Insight.user_id == user_id]
    if ledger_id is not None:
        conditions.append(Insight.ledger_id == ledger_id)
    total = (
        await db.execute(select(func.count(Insight.id)).where(*conditions))
    ).scalar_one()
    result = await db.execute(
        select(Insight)
        .where(*conditions)
        .order_by(Insight.generated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(result.scalars().all()), total


async def get_insight(
    db: AsyncSession,
    insight_id: int,
    user_id: int,
) -> Insight | None:
    result = await db.execute(
        select(Insight).where(
            Insight.id == insight_id,
            Insight.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def queue_insight_generation(
    redis: Redis,
    *,
    user_id: int,
    ledger_id: int,
    report_type: ReportType,
) -> str:
    job_id = uuid.uuid4().hex
    payload = json.dumps(
        {
            "job_id": job_id,
            "user_id": user_id,
            "ledger_id": ledger_id,
            "report_type": report_type.value,
            "attempts": 0,
        },
        ensure_ascii=False,
    )
    accepted = await redis.eval(
        QUEUE_PUSH_IF_AVAILABLE_SCRIPT,
        1,
        INSIGHT_QUEUE,
        settings.INSIGHT_QUEUE_MAX_LENGTH,
        payload,
    )
    if not accepted:
        raise InsightQueueFull("洞察任务队列已满，请稍后再试")
    return job_id

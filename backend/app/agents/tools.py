from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


TransactionType = Literal["expense", "income"]


class ParsedBill(BaseModel):
    type: TransactionType | None = Field(
        default=None,
        description="交易类型：expense=消费支出，income=收入",
    )
    amount: float | None = Field(
        default=None,
        gt=0,
        description="金额（元），例如 68.5；用户没说则为 null",
    )
    category: str | None = Field(
        default=None,
        max_length=64,
        description=(
            "一级分类，例如餐饮美食、交通出行、购物消费、工资收入；"
            "无法确定则为 null"
        ),
    )
    subcategory: str | None = Field(
        default=None,
        max_length=64,
        description="二级细分，例如午餐、打车、工资",
    )
    account: str | None = Field(
        default=None,
        max_length=64,
        description="支付或收款账户，例如微信支付、支付宝、银行卡、现金",
    )
    note: str | None = Field(default=None, max_length=256)
    bill_date: str | None = Field(
        default=None,
        description="交易日期，格式 YYYY-MM-DD；无法确定则为 null",
    )

    @field_validator("category", "subcategory", "account", "note")
    @classmethod
    def empty_text_to_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @field_validator("bill_date")
    @classmethod
    def validate_bill_date(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        return date.fromisoformat(value.strip()).isoformat()


def get_extract_tool() -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": "extract_transaction",
            "description": "从用户自然语言中提取结构化记账信息",
            "parameters": ParsedBill.model_json_schema(),
        },
    }


PARSER_SYSTEM_PROMPT = """你是荣小账智能记账助手，只负责提取记账信息。
请调用 extract_transaction 工具返回结构化结果，不要编造用户没有表达的信息。

规则：
1. 识别口语金额，例如“六十八块五”是 68.5 元。
2. 根据语义推断分类，例如“奶茶”归入“餐饮美食”，“打车”归入“交通出行”。
3. 收入使用收入分类，例如工资收入、副业收入、其他收入。
4. 根据请求中给出的今天日期推断“昨天”“上周五”等相对日期。
5. 无法可靠判断的字段必须返回 null，由系统向用户追问。
6. 不提供投资、借贷或信用评分建议。"""

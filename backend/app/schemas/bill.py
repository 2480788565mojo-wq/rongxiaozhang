from datetime import date, datetime
from decimal import Decimal
import math
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


BillKind = Literal["expense", "income"]
EXCEL_IMPORT_KEY_PATTERN = r"^excel:[a-f0-9]{32}:[0-9]{1,7}$"


class TranscribeRequest(BaseModel):
    text: str = Field(min_length=1, max_length=500)
    ledger_id: int = Field(default=1, gt=0)
    session_id: str | None = Field(default=None, max_length=64)

    @field_validator("text", mode="before")
    @classmethod
    def text_must_contain_content(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("输入内容不能为空")
        return cleaned


class TranscribeResponse(BaseModel):
    status: Literal["completed", "clarifying", "blocked"]
    parsed: dict | None = None
    clarification_question: str | None = None
    budget_check: dict | None = None
    bill: dict | None = None


class BillCreateRequest(BaseModel):
    # 同一次 Excel 导入的每行固定编号，断网重试时不重复入账。
    import_key: str | None = Field(default=None, pattern=EXCEL_IMPORT_KEY_PATTERN)
    ledger_id: int = Field(gt=0)
    type: BillKind
    amount: float = Field(gt=0, le=100_000_000, allow_inf_nan=False)
    category: str = Field(min_length=1, max_length=64)
    subcategory: str | None = Field(default=None, max_length=64)
    account: str | None = Field(default=None, max_length=64)
    note: str | None = Field(default=None, max_length=256)
    bill_date: date

    @field_validator("category", "subcategory", "account", "note", mode="before")
    @classmethod
    def trim_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class ParsedBillInput(BaseModel):
    type: BillKind
    amount: float = Field(gt=0, le=100_000_000, allow_inf_nan=False)
    category: str = Field(min_length=1, max_length=64)
    subcategory: str | None = Field(default=None, max_length=64)
    account: str | None = Field(default=None, max_length=64)
    note: str | None = Field(default=None, max_length=256)
    bill_date: date

    @field_validator("category", "subcategory", "account", "note", mode="before")
    @classmethod
    def trim_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class BillImportItem(ParsedBillInput):
    import_key: str = Field(pattern=EXCEL_IMPORT_KEY_PATTERN)

    @field_validator("amount")
    @classmethod
    def money_has_at_most_two_decimal_places(cls, value: float) -> float:
        amount = Decimal(str(value))
        if amount != amount.quantize(Decimal("0.01")):
            raise ValueError("导入金额最多保留两位小数")
        return value


class BillImportRequest(BaseModel):
    ledger_id: int = Field(gt=0)
    items: list[BillImportItem] = Field(min_length=1, max_length=100)

    @field_validator("items")
    @classmethod
    def import_keys_must_be_unique(cls, items: list[BillImportItem]) -> list[BillImportItem]:
        keys = [item.import_key for item in items]
        if len(keys) != len(set(keys)):
            raise ValueError("同一批导入中不能有重复的账单编号")
        return items


class BillImportResultItem(BaseModel):
    import_key: str
    bill_id: int
    created: bool


class BillImportResponse(BaseModel):
    items: list[BillImportResultItem]


class BillConfirmRequest(BaseModel):
    ledger_id: int = Field(default=1, gt=0)
    session_id: str = Field(min_length=1, max_length=64)
    raw_input: str = Field(min_length=1, max_length=500)
    parsed: ParsedBillInput
    share_user_ids: list[int] = Field(default_factory=list, max_length=50)
    # 批量逐笔确认时由客户端显式标记，避免再从 session_id 里猜冒号。
    is_batch_item: bool = False

    @field_validator("raw_input", mode="before")
    @classmethod
    def raw_input_must_contain_content(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("原始输入不能为空")
        return cleaned
    force: bool = False

    @field_validator("share_user_ids")
    @classmethod
    def unique_share_users(cls, value: list[int]) -> list[int]:
        if any(user_id <= 0 for user_id in value):
            raise ValueError("参与成员编号必须大于 0")
        if len(value) != len(set(value)):
            raise ValueError("参与成员不能重复")
        if value and len(value) < 2:
            raise ValueError("AA 分摊至少需要 2 名参与成员")
        return value


class BillShareOut(BaseModel):
    user_id: int
    share_amount: float
    settled: bool
    settled_at: date | None = None

    model_config = ConfigDict(from_attributes=True)


class BillOut(BaseModel):
    id: int
    ledger_id: int
    creator_id: int
    type: BillKind
    amount: float
    category: str
    subcategory: str | None = None
    account: str | None = None
    note: str | None = None
    bill_date: date
    raw_input: str | None = None
    ai_parsed: bool
    created_at: datetime
    shares: list[BillShareOut] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class BillUpdate(BaseModel):
    type: BillKind | None = None
    amount: float | None = Field(default=None, gt=0, le=100_000_000, allow_inf_nan=False)
    category: str | None = Field(default=None, min_length=1, max_length=64)
    subcategory: str | None = Field(default=None, max_length=64)
    account: str | None = Field(default=None, max_length=64)
    note: str | None = Field(default=None, max_length=256)
    bill_date: date | None = None

    @field_validator("category", "subcategory", "account", "note", mode="before")
    @classmethod
    def trim_update_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @model_validator(mode="after")
    def required_fields_cannot_be_cleared(self) -> "BillUpdate":
        for field in ("type", "amount", "category", "bill_date"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} 不能设置为空")
        return self


class BillListParams(BaseModel):
    ledger_id: int = Field(default=1, gt=0)
    year: int | None = Field(default=None, ge=2000, le=2100)
    month: int | None = Field(default=None, ge=1, le=12)
    category: str | None = Field(default=None, max_length=64)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class BillListResponse(BaseModel):
    items: list[BillOut]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)

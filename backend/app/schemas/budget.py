import math
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BudgetSet(BaseModel):
    ledger_id: int = Field(default=1, gt=0)
    year: int = Field(ge=2000, le=2100)
    month: int = Field(ge=1, le=12)
    total_budget: float | None = Field(default=None, ge=0, le=100_000_000, allow_inf_nan=False)
    category_budgets: dict[str, float] = Field(default_factory=dict, max_length=100)

    @field_validator("category_budgets")
    @classmethod
    def validate_category_budgets(
        cls,
        value: dict[str, float],
    ) -> dict[str, float]:
        cleaned: dict[str, float] = {}
        for category, amount in value.items():
            name = category.strip()
            if not name or len(name) > 64:
                raise ValueError("预算分类名称长度必须为 1 到 64 个字符")
            if not math.isfinite(amount) or amount < 0 or amount > 100_000_000:
                raise ValueError("分类预算必须是有限的 0 到 1 亿以内金额")
            cleaned[name] = amount
        return cleaned


class BudgetOut(BaseModel):
    id: int
    ledger_id: int
    user_id: int
    year: int
    month: int
    total_budget: float | None = None
    category_budgets: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)


class BudgetStatus(BaseModel):
    category: str
    kind: Literal["category", "total"] = "category"
    spent: float = Field(ge=0)
    budget: float = Field(ge=0)
    remaining: float
    percentage: float = Field(ge=0)
    risk_level: Literal["safe", "warning", "blocked"] = "safe"


class BudgetStatusResponse(BaseModel):
    ledger_id: int
    year: int
    month: int
    statuses: list[BudgetStatus] = Field(default_factory=list)

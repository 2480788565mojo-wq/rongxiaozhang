from pydantic import BaseModel, Field


class StatsOverview(BaseModel):
    ledger_id: int
    year: int
    month: int
    income: float = Field(ge=0)
    expense: float = Field(ge=0)
    balance: float
    budget_used_percentage: float | None = Field(default=None, ge=0)


class TrendPoint(BaseModel):
    period: str
    income: float = Field(ge=0)
    expense: float = Field(ge=0)


class TrendResponse(BaseModel):
    ledger_id: int
    items: list[TrendPoint] = Field(default_factory=list)


class CategoryStat(BaseModel):
    category: str
    amount: float = Field(ge=0)
    percentage: float = Field(ge=0)


class CategoryStatsResponse(BaseModel):
    ledger_id: int
    year: int
    month: int
    total: float = Field(ge=0)
    items: list[CategoryStat] = Field(default_factory=list)

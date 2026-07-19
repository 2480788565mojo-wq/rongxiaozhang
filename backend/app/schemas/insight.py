from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


ReportKind = Literal["weekly", "monthly", "on_demand"]


class InsightGenerateRequest(BaseModel):
    ledger_id: int = Field(default=1, gt=0)
    report_type: ReportKind = "on_demand"


class InsightGenerateResponse(BaseModel):
    status: Literal["queued"] = "queued"
    ledger_id: int
    report_type: ReportKind


class InsightOut(BaseModel):
    id: int
    user_id: int
    ledger_id: int
    report_type: ReportKind
    content: str
    key_findings: list[Any] | None = None
    suggested_actions: list[Any] | None = None
    generated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InsightListResponse(BaseModel):
    items: list[InsightOut] = Field(default_factory=list)
    total: int = Field(ge=0)

from datetime import datetime
import math

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AccountCreate(BaseModel):
    ledger_id: int = Field(gt=0)
    name: str = Field(min_length=1, max_length=64)
    type: str = Field(min_length=1, max_length=32)
    icon: str | None = Field(default=None, max_length=64)
    balance: float = Field(default=0, ge=-100_000_000, le=100_000_000, allow_inf_nan=False)

    @model_validator(mode="after")
    def normalize_create_text(self) -> "AccountCreate":
        self.name = self.name.strip()
        self.type = self.type.strip()
        if not self.name or not self.type:
            raise ValueError("账户名称和类型不能为空")
        if not math.isfinite(self.balance):
            raise ValueError("账户余额必须是有限数字")
        return self


class AccountUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=64)
    type: str | None = Field(default=None, min_length=1, max_length=32)
    icon: str | None = Field(default=None, max_length=64)
    balance: float | None = Field(default=None, ge=-100_000_000, le=100_000_000, allow_inf_nan=False)

    @model_validator(mode="after")
    def required_fields_cannot_be_cleared(self) -> "AccountUpdate":
        for field in ("name", "type", "balance"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} 不能设置为空")
        if self.name is not None:
            self.name = self.name.strip()
            if not self.name:
                raise ValueError("name 不能设置为空")
        if self.type is not None:
            self.type = self.type.strip()
            if not self.type:
                raise ValueError("type 不能设置为空")
        if self.balance is not None and not math.isfinite(self.balance):
            raise ValueError("账户余额必须是有限数字")
        return self


class AccountOut(BaseModel):
    id: int
    user_id: int
    ledger_id: int
    name: str
    type: str
    icon: str | None = None
    balance: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


CategoryKind = Literal["expense", "income"]


class CategoryCreate(BaseModel):
    ledger_id: int = Field(gt=0)
    type: CategoryKind
    parent_name: str = Field(default="", max_length=64)
    name: str = Field(min_length=1, max_length=64)
    icon: str | None = Field(default=None, max_length=64)
    sort: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def normalize_create_text(self) -> "CategoryCreate":
        self.parent_name = self.parent_name.strip()
        self.name = self.name.strip()
        if not self.name:
            raise ValueError("分类名称不能为空")
        return self


class CategoryUpdate(BaseModel):
    parent_name: str | None = Field(default=None, max_length=64)
    name: str | None = Field(default=None, min_length=1, max_length=64)
    icon: str | None = Field(default=None, max_length=64)
    sort: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def required_fields_cannot_be_cleared(self) -> "CategoryUpdate":
        for field in ("parent_name", "name", "sort"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} 不能设置为空")
        for field in ("parent_name", "name", "icon"):
            value = getattr(self, field)
            if isinstance(value, str):
                setattr(self, field, value.strip())
        if self.name == "":
            raise ValueError("name 不能设置为空")
        return self


class CategoryOut(BaseModel):
    id: int
    user_id: int
    ledger_id: int
    type: CategoryKind
    parent_name: str
    name: str
    icon: str | None = None
    sort: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

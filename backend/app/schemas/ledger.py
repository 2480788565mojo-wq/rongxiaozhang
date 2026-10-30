from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


LedgerKind = Literal["personal", "shared"]
MemberRole = Literal["owner", "admin", "member"]


class LedgerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    type: LedgerKind = "personal"

    @model_validator(mode="after")
    def normalize_name(self) -> "LedgerCreate":
        self.name = self.name.strip()
        if not self.name:
            raise ValueError("账本名称不能为空")
        return self


class LedgerJoin(BaseModel):
    invite_code: str = Field(min_length=4, max_length=32)

    @model_validator(mode="after")
    def normalize_code(self) -> "LedgerJoin":
        self.invite_code = self.invite_code.strip()
        if len(self.invite_code) < 4:
            raise ValueError("邀请码长度无效")
        return self


class LedgerMemberOut(BaseModel):
    user_id: int
    role: MemberRole
    nickname: str | None = None
    avatar_url: str | None = None

    model_config = ConfigDict(from_attributes=True)


class MemberRoleUpdate(BaseModel):
    role: Literal["admin", "member"]


class LedgerOut(BaseModel):
    id: int
    name: str
    type: LedgerKind
    owner_id: int
    invite_code: str | None = None
    settle_strategy: str = "equal"
    member_count: int = 0
    created_at: datetime | None = None
    members: list[LedgerMemberOut] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class SettlementOut(BaseModel):
    from_user_id: int
    from_user_name: str
    to_user_id: int
    to_user_name: str
    amount: float = Field(gt=0)
    # 能直接对应到“该付款人欠该收款人”的账单分摊；
    # 如果这笔转账是多人链路抵消出来的，列表为空，需要到账单详情逐笔处理。
    share_ids: list[int] = Field(default_factory=list)


class SettlementConfirm(BaseModel):
    from_user_id: int = Field(gt=0)
    to_user_id: int = Field(gt=0)
    share_ids: list[int] = Field(min_length=1, max_length=100)


class LedgerSettlementResponse(BaseModel):
    ledger_id: int
    settlements: list[SettlementOut] = Field(default_factory=list)

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    code: str = Field(min_length=1, max_length=256)


class DevLoginRequest(BaseModel):
    nickname: str = Field(default="H5 测试用户", min_length=1, max_length=64)


class UserOut(BaseModel):
    id: int
    nickname: str | None = None
    avatar_url: str | None = None
    default_ledger_id: int | None = None

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut

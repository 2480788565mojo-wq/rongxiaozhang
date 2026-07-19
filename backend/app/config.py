from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings


INSECURE_JWT_SECRETS = {
    "your-secret-key-change-in-production",
    "change-me-to-random-string",
    "replace-with-at-least-32-random-characters",
}

class Settings(BaseSettings):
    # 数据库
    DATABASE_URL: str = "mysql+asyncmy://root:password@localhost:3306/rxz"
    DATABASE_TEST_URL: str = "sqlite+aiosqlite:///./test.db"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    JWT_SECRET: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_DAYS: int = 30

    # 微信
    WECHAT_APPID: str = "wx790e9576e610670e"
    WECHAT_SECRET: str = ""

    # LLM
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"
    DEEPSEEK_MODEL: str = "deepseek-chat"

    QWEN_API_KEY: str = ""
    QWEN_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    QWEN_MODEL: str = "qwen-max"

    # 应用
    APP_NAME: str = "荣小账 API"
    ENVIRONMENT: Literal["development", "test", "production"] = "development"
    DEBUG: bool = False
    ENABLE_DEV_LOGIN: bool = False
    CORS_ORIGINS: list[str] = ["*"]

    # 滥用防护
    LOGIN_LIMIT_PER_MINUTE: int = Field(default=10, gt=0)
    AI_TRANSCRIBE_LIMIT_PER_MINUTE: int = Field(default=20, gt=0)
    AI_TRANSCRIBE_LIMIT_PER_DAY: int = Field(default=200, gt=0)
    AI_INSIGHT_LIMIT_PER_HOUR: int = Field(default=3, gt=0)
    AI_INSIGHT_LIMIT_PER_DAY: int = Field(default=10, gt=0)
    SSE_CONNECTION_LIMIT_PER_USER: int = Field(default=2, gt=0)
    AGENT_SESSION_TTL_SECONDS: int = Field(default=1800, ge=60)
    INSIGHT_QUEUE_MAX_LENGTH: int = Field(default=1000, gt=0)

    # ChromaDB
    CHROMA_PERSIST_DIR: str = "./chroma_data"
    EMBEDDING_MODEL: str = "BAAI/bge-small-zh-v1.5"
    EMBEDDING_DEVICE: str = "cpu"

    # 后台任务
    INSIGHT_WORKER_ENABLED: bool = True

    # 预算告警阈值
    BUDGET_WARNING_RATIO: float = 0.8   # 80% 黄色告警
    BUDGET_BLOCKED_RATIO: float = 1.0   # 100% 红色拦截

    @field_validator("JWT_SECRET")
    @classmethod
    def validate_jwt_secret(cls, value: str) -> str:
        secret = value.strip()
        if len(secret) < 32 or secret.lower() in INSECURE_JWT_SECRETS:
            raise ValueError("JWT_SECRET 必须是至少 32 个字符的随机密钥")
        return secret

    @model_validator(mode="after")
    def validate_environment_safety(self) -> "Settings":
        if self.ENVIRONMENT == "production" and self.DEBUG:
            raise ValueError("生产环境禁止开启 DEBUG")
        if self.ENVIRONMENT == "production" and self.ENABLE_DEV_LOGIN:
            raise ValueError("生产环境禁止开启开发登录")
        return self

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

@lru_cache
def get_settings() -> Settings:
    return Settings()

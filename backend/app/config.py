from pydantic_settings import BaseSettings
from functools import lru_cache

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
    DEBUG: bool = False
    CORS_ORIGINS: list[str] = ["*"]

    # ChromaDB
    CHROMA_PERSIST_DIR: str = "./chroma_data"

    # 预算告警阈值
    BUDGET_WARNING_RATIO: float = 0.8   # 80% 黄色告警
    BUDGET_BLOCKED_RATIO: float = 1.0   # 100% 红色拦截

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

@lru_cache
def get_settings() -> Settings:
    return Settings()

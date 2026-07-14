# 荣小账 v2.0 — 实施计划

> **For agentic workers:** Use superpowers:subagent-driven-development to implement task-by-task.
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将荣小账从纯本地存储的简单记账APP重构为AI多Agent驱动的智能财务协同系统

**Architecture:** 五层架构 — UniApp/Pinia前端 → FastAPI网关 → LangGraph Agent编排 → MySQL/Redis/ChromaDB数据层 → 微信云托管

**Tech Stack:** FastAPI + LangGraph + Pydantic v2 + SQLAlchemy async + Redis + ChromaDB + UniApp Vue3 + Pinia + ECharts + 原子化CSS

**Reference Spec:** `docs/superpowers/specs/2026-07-14-rongxiaozhang-rebuild-design.md`

## Global Constraints

- 严禁使用 LangChain AgentExecutor / LLMChain / ConversationChain / RetrievalQA
- LLM Function Calling 用 Pydantic v2 BaseModel 严格约束
- 前端状态管理必须用 Pinia（不再直接调用 store.ts 函数）
- 图表用 ECharts（不再手写 Canvas）
- MySQL 多账本隔离（所有业务表带 ledger_id）
- Redis 分布式锁 + 预算计数器 + SSE Pub/Sub
- 微信小程序 appid: wx790e9576e610670e
- 部署目标: 微信云托管 CloudBase Run
- 项目已发布上线，重构后重新提交审核

---

## 文件结构映射

### 新建：后端 backend/

```
backend/
├── pyproject.toml, Dockerfile, .env.example
├── alembic.ini, alembic/env.py, alembic/versions/
├── app/
│   ├── main.py, config.py
│   ├── api/v1/{router,auth,bills,ledgers,budgets,stats,insights,sse}.py
│   ├── agents/{graph,state,parser,guardian,social,oracle,tools}.py
│   ├── core/{database,redis,security,llm}.py
│   ├── models/{base,user,ledger,bill,budget,insight}.py
│   ├── schemas/{auth,bill,ledger,budget,stats,insight}.py
│   ├── services/{bill,budget,ledger,insight}_service.py
│   └── rag/{chroma_store,embeddings,retriever}.py + seed_data/
└── tests/{conftest,test_parser,test_guardian,test_social,test_graph}.py
    └── test_api/{test_auth,test_bills,test_transcribe}.py
```

### 修改：前端 src/

```
src/
├── main.ts (修改：挂载Pinia)
├── App.vue (修改：挂载SSEHandler)
├── pages.json (修改：新增7个页面路由)
├── pages/
│   ├── transcribe/index.vue          ★新建 AI记账页
│   ├── ledgers/{index,members,settle}.vue ★新建 多账本
│   ├── insights/{index,report}.vue   ★新建 AI洞察
│   ├── bills/detail.vue              ★新建 账单详情
│   ├── {home,stats,budget,accounts,categories,settings}/index.vue (修改)
│   └── snake/index.vue (保留不动)
├── components/
│   ├── SSEHandler.vue, BudgetAlert.vue  ★新建
│   └── charts/{TrendLine,CategoryPie,BudgetGauge}.vue ★新建
├── stores/{user,ledger,bill,budget,sse}.ts ★新建
├── api/{client,auth,bills,ledgers,budgets,stats,insights}.ts ★新建
├── styles/{atoms,tokens,theme}.css    ★新建
└── utils/sse.ts                      ★新建
```

---

## Phase 1: 后端基础设施（Tasks 1-4）

### Task 1: Python 项目初始化 ✅ 已完成

**Commit:** 43e938d — backend/pyproject.toml, .env.example, app/__init__.py, app/config.py, Dockerfile

---

### Task 2: 数据库核心层 + ORM 模型

**Files:**
- Create: `backend/app/core/database.py`
- Create: `backend/app/models/__init__.py`, `base.py`, `user.py`, `ledger.py`, `bill.py`, `budget.py`, `insight.py`

**Interfaces:**
- Produces: `async def get_db() -> AsyncGenerator[AsyncSession, None]` — FastAPI Depends
- Produces: `Base` (DeclarativeBase), 8 ORM Model 类
- Produces: `async def init_db()` — 创建所有表

- [ ] **Step 1: 编写 database.py**

```python
# backend/app/core/database.py
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import get_settings

settings = get_settings()
engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG, pool_size=20, max_overflow=40, pool_pre_ping=True)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def get_db():
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

- [ ] **Step 2: 编写 8 张表的 ORM 模型**

参考 Spec §4.2。关键模型签名：

```python
# models/user.py
class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    openid: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    nickname, avatar_url, default_ledger_id, created_at, updated_at

# models/ledger.py
class Ledger(Base):
    __tablename__ = "ledgers"
    id, name, type(Enum: personal/shared), owner_id(FK→users), invite_code, settle_strategy

class LedgerMember(Base):
    __tablename__ = "ledger_members"
    ledger_id(FK), user_id(FK), role(Enum: owner/admin/member) — 联合主键

# models/bill.py
class Bill(Base):
    __tablename__ = "bills"
    id, ledger_id(FK), creator_id(FK), type(Enum: expense/income), amount(DECIMAL),
    category, subcategory, account, note, bill_date, raw_input, ai_parsed, created_at

class BillShare(Base):
    __tablename__ = "bill_shares"
    id, bill_id(FK), user_id(FK), share_amount(DECIMAL), settled, settled_at

# models/budget.py
class Budget(Base):
    __tablename__ = "budgets"
    id, ledger_id(FK), user_id(FK), year, month, total_budget, category_budgets(JSON)
    __table_args__ = (UniqueConstraint("user_id", "year", "month", "ledger_id"),)

# models/insight.py
class Insight(Base):
    __tablename__ = "insights"
    id, user_id(FK), ledger_id(FK), report_type(Enum), content(TEXT), key_findings(JSON), suggested_actions(JSON)

class ChatHistory(Base):
    __tablename__ = "chat_history"
    id, user_id(FK), ledger_id(FK), session_id, role(Enum), content(TEXT), created_at
```

- [ ] **Step 3: 运行类型检查**

```bash
cd backend && pip install -e ".[dev]" && python -c "from app.models import *; print('Models OK')"
```

- [ ] **Step 4: 提交**

```bash
git add backend/app/core/database.py backend/app/models/
git commit -m "feat: SQLAlchemy async引擎 + 8张表ORM模型（User/Ledger/Bill/Budget/Insight）"
```

---

### Task 3: Redis + JWT + LLM 工厂

**Files:**
- Create: `backend/app/core/redis.py`
- Create: `backend/app/core/security.py`
- Create: `backend/app/core/llm.py`

**Interfaces:**
- Produces: `async def get_redis() -> Redis` — FastAPI Depends
- Produces: `def create_access_token(user_id: int) -> str`
- Produces: `async def get_current_user(credentials, db) -> User`
- Produces: `class LLMClient` — `call_with_tools(messages, tools) -> dict`

- [ ] **Step 1: 编写 redis.py — 连接池 + 预算计数器 + 分布式锁**

```python
# backend/app/core/redis.py
from redis.asyncio import Redis, ConnectionPool
from app.config import get_settings

settings = get_settings()
pool = ConnectionPool.from_url(settings.REDIS_URL, max_connections=50, decode_responses=True)

async def get_redis() -> Redis:
    return Redis(connection_pool=pool)

async def incr_budget_spent(redis: Redis, user_id: int, year: int, month: int, category: str, amount: float) -> float:
    key = f"budget:{user_id}:{year}:{month}:{category}"
    return await redis.incrbyfloat(key, amount)

async def get_budget_spent(redis: Redis, user_id: int, year: int, month: int, category: str) -> float:
    val = await redis.get(f"budget:{user_id}:{year}:{month}:{category}")
    return float(val) if val else 0.0

async def acquire_ledger_lock(redis: Redis, ledger_id: int, request_id: str, ttl: int = 5) -> bool:
    return await redis.set(f"lock:ledger:{ledger_id}:write", request_id, nx=True, ex=ttl)

async def release_ledger_lock(redis: Redis, ledger_id: int, request_id: str):
    script = """if redis.call("get", KEYS[1]) == ARGV[1] then return redis.call("del", KEYS[1]) else return 0 end"""
    await redis.eval(script, 1, f"lock:ledger:{ledger_id}:write", request_id)
```

- [ ] **Step 2: 编写 security.py — JWT + 微信登录**

```python
# backend/app/core/security.py
from datetime import datetime, timedelta
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.config import get_settings
from app.core.database import get_db
from app.models import User

settings = get_settings()
security_scheme = HTTPBearer()

def create_access_token(user_id: int) -> str:
    expire = datetime.utcnow() + timedelta(days=settings.JWT_EXPIRE_DAYS)
    return jwt.encode({"sub": str(user_id), "exp": expire}, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        payload = jwt.decode(credentials.credentials, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "无效的登录凭证")
    result = await db.execute(select(User).where(User.id == int(payload["sub"])))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "用户不存在")
    return user
```

- [ ] **Step 3: 编写 llm.py — 双 Provider LLM 工厂**

```python
# backend/app/core/llm.py
import json
from typing import Literal
from openai import AsyncOpenAI
from app.config import get_settings

settings = get_settings()

class LLMClient:
    PROVIDERS = {
        "deepseek": {"base_url": settings.DEEPSEEK_BASE_URL, "api_key": settings.DEEPSEEK_API_KEY, "model": settings.DEEPSEEK_MODEL},
        "qwen": {"base_url": settings.QWEN_BASE_URL, "api_key": settings.QWEN_API_KEY, "model": settings.QWEN_MODEL},
    }

    def __init__(self, provider: Literal["deepseek", "qwen"]):
        cfg = self.PROVIDERS[provider]
        self.client = AsyncOpenAI(base_url=cfg["base_url"], api_key=cfg["api_key"])
        self.model = cfg["model"]

    async def call_with_tools(self, messages: list[dict], tools: list[dict], tool_choice: str = "auto") -> dict | None:
        response = await self.client.chat.completions.create(model=self.model, messages=messages, tools=tools, tool_choice=tool_choice)
        choice = response.choices[0]
        if choice.message.tool_calls:
            return json.loads(choice.message.tool_calls[0].function.arguments)
        return None

    async def chat(self, messages: list[dict], temperature: float = 0.7, max_tokens: int = 2048) -> str:
        response = await self.client.chat.completions.create(model=self.model, messages=messages, temperature=temperature, max_tokens=max_tokens)
        return response.choices[0].message.content or ""

    @staticmethod
    def pydantic_to_openai_tool(model_cls, name: str, description: str) -> dict:
        return {"type": "function", "function": {"name": name, "description": description, "parameters": model_cls.model_json_schema()}}
```

- [ ] **Step 4: 提交**

```bash
git add backend/app/core/redis.py backend/app/core/security.py backend/app/core/llm.py
git commit -m "feat: Redis连接池+分布式锁 + JWT认证 + LLM双Provider工厂"
```

---

### Task 4: Pydantic Schema 层

**Files:**
- Create: `backend/app/schemas/__init__.py`, `auth.py`, `bill.py`, `ledger.py`, `budget.py`, `stats.py`, `insight.py`

**Interfaces:**
- Produces: 全部 Request/Response Schema 类

- [ ] **Step 1: 编写核心 Schema**

```python
# schemas/auth.py
class LoginRequest(BaseModel): code: str
class TokenResponse(BaseModel): access_token: str; token_type: str = "bearer"; user: "UserOut"
class UserOut(BaseModel): id: int; nickname: str | None; avatar_url: str | None
    model_config = {"from_attributes": True}

# schemas/bill.py
class TranscribeRequest(BaseModel):
    text: str = Field(min_length=1, max_length=500)
    ledger_id: int = 1
    session_id: str | None = None

class TranscribeResponse(BaseModel):
    status: Literal["completed", "clarifying", "blocked"]
    parsed: dict | None = None
    clarification_question: str | None = None
    budget_check: dict | None = None
    bill: dict | None = None

class BillOut(BaseModel):
    id: int; ledger_id: int; type: str; amount: float; category: str
    subcategory: str | None; account: str | None; note: str | None
    bill_date: date; raw_input: str | None; ai_parsed: bool; created_at: datetime
    shares: list["BillShareOut"] = []
    model_config = {"from_attributes": True}

class BillShareOut(BaseModel):
    user_id: int; share_amount: float; settled: bool
    model_config = {"from_attributes": True}

class BillListParams(BaseModel):
    ledger_id: int = 1; year: int | None = None; month: int | None = None
    category: str | None = None; page: int = Field(default=1, ge=1); page_size: int = Field(default=20, ge=1, le=100)

# schemas/ledger.py
class LedgerCreate(BaseModel): name: str; type: Literal["personal", "shared"] = "personal"
class LedgerJoin(BaseModel): invite_code: str
class LedgerOut(BaseModel): id: int; name: str; type: str; owner_id: int; invite_code: str | None; member_count: int = 0

# schemas/budget.py
class BudgetSet(BaseModel): ledger_id: int = 1; year: int; month: int; total_budget: float | None = None; category_budgets: dict[str, float] = {}
class BudgetStatus(BaseModel): category: str; spent: float; budget: float; percentage: float

# schemas/insight.py
class InsightOut(BaseModel): id: int; report_type: str; content: str; key_findings: list | None; suggested_actions: list | None; generated_at: datetime
```

- [ ] **Step 2: 提交**

```bash
git add backend/app/schemas/
git commit -m "feat: Pydantic v2 Schema层（全部Request/Response模型）"
```

---

## Phase 2: LangGraph Agent 系统（Tasks 5-8）

### Task 5: Agent State + Tools

**Files:**
- Create: `backend/app/agents/__init__.py`, `state.py`, `tools.py`

**Interfaces:**
- Produces: `TransactionState` TypedDict, `ParsedBill` Pydantic model, `get_extract_tool()` → OpenAI tool dict

- [ ] **Step 1: 编写 state.py — TransactionState**

```python
# backend/app/agents/state.py
from typing import TypedDict, Literal, Optional

class TransactionState(TypedDict, total=False):
    raw_input: str; user_id: int; ledger_id: int; session_id: str
    parsed: Optional[dict]; missing_fields: list[str]
    clarification_question: Optional[str]; clarification_round: int
    budget_check: Optional[dict]
    risk_level: Literal["safe", "warning", "blocked"]
    is_shared_ledger: bool; settlements: Optional[list[dict]]
    insight_triggered: bool; error: Optional[str]
```

- [ ] **Step 2: 编写 tools.py — Pydantic Function Calling Tool**

```python
# backend/app/agents/tools.py
from pydantic import BaseModel, Field
from typing import Optional, Literal
from app.core.llm import LLMClient

class ParsedBill(BaseModel):
    type: Literal["expense", "income"] = Field(description="交易类型：expense=消费支出, income=收入")
    amount: Optional[float] = Field(default=None, description="金额（元），如68.5。没说则为null")
    category: Optional[str] = Field(default=None, description="一级分类：餐饮美食/交通出行/购物消费/居住物业/休闲娱乐/人情社交/医疗健康/教育学习/通讯")
    subcategory: Optional[str] = Field(default=None, description="二级细分")
    account: Optional[str] = Field(default=None, description="支付方式：微信支付/支付宝/银行卡/现金")
    note: Optional[str] = Field(default=None, max_length=256)
    bill_date: Optional[str] = Field(default=None, description="日期YYYY-MM-DD，默认今天")

def get_extract_tool() -> dict:
    return LLMClient.pydantic_to_openai_tool(ParsedBill, "extract_transaction", "从用户自然语言中提取结构化记账信息")

PARSER_SYSTEM_PROMPT = """你是荣小账智能记账助手。用自然语言提取结构化信息。
规则：金额识别口语（"六十八块五"=68.5）；分类推断关键词（"奶茶"→餐饮美食）；日期推理（"昨天"=今天-1）；宁可留null不瞎猜。"""
```

- [ ] **Step 3: 提交**

```bash
git add backend/app/agents/__init__.py backend/app/agents/state.py backend/app/agents/tools.py
git commit -m "feat: Agent State定义 + Pydantic Function Calling Tool（ParsedBill）"
```

---

### Task 6: Parser + Guardian Node

**Files:**
- Create: `backend/app/agents/parser.py`, `guardian.py`

- [ ] **Step 1: 编写 parser.py — HITL 反问机制**

```python
# backend/app/agents/parser.py
from datetime import date
from app.agents.state import TransactionState
from app.agents.tools import ParsedBill, get_extract_tool, PARSER_SYSTEM_PROMPT
from app.core.llm import LLMClient

REQUIRED_FIELDS = ["type", "amount", "category"]
MAX_CLARIFY_ROUNDS = 3

async def parser_node(state: TransactionState) -> TransactionState:
    client = LLMClient("deepseek")
    tool = get_extract_tool()
    messages = [
        {"role": "system", "content": PARSER_SYSTEM_PROMPT},
        {"role": "user", "content": f"今天{date.today().isoformat()}。用户：{state['raw_input']}"},
    ]
    if state.get("clarification_round", 0) > 0:
        messages.append({"role": "assistant", "content": f"我问了：{state['clarification_question']}"})
        messages.append({"role": "user", "content": state["raw_input"]})

    result = await client.call_with_tools(messages, [tool])
    if result is None:
        state["error"] = "AI解析失败，请重试"
        return state

    parsed = ParsedBill(**result)
    state["parsed"] = {
        "type": parsed.type, "amount": parsed.amount, "category": parsed.category,
        "subcategory": parsed.subcategory, "account": parsed.account,
        "note": parsed.note, "bill_date": parsed.bill_date or date.today().isoformat(),
    }
    missing = [f for f in REQUIRED_FIELDS if state["parsed"].get(f) is None]
    state["missing_fields"] = missing
    round_num = state.get("clarification_round", 0)

    if missing and round_num < MAX_CLARIFY_ROUNDS:
        labels = {"type": "这是收入还是支出？", "amount": "请问花了多少钱？", "category": "这是哪类消费？"}
        state["clarification_question"] = labels.get(missing[0], f"请补充{missing[0]}")
        state["clarification_round"] = round_num + 1
    elif missing:
        state["error"] = f"已反问{MAX_CLARIFY_ROUNDS}轮，请手动填表"
    else:
        state["clarification_question"] = None
    return state
```

- [ ] **Step 2: 编写 guardian.py — 预算实时风控**

```python
# backend/app/agents/guardian.py
from datetime import date
from app.agents.state import TransactionState
from app.core.redis import get_redis, get_budget_spent
from app.config import get_settings

settings = get_settings()

async def guardian_node(state: TransactionState) -> TransactionState:
    parsed = state.get("parsed")
    if not parsed or not parsed.get("amount") or not parsed.get("category"):
        state["risk_level"] = "safe"
        return state

    today = date.today()
    redis = await get_redis()
    current = await get_budget_spent(redis, state["user_id"], today.year, today.month, parsed["category"])
    projected = current + float(parsed["amount"])
    limit = float(await redis.get(f"budget_limit:{state['user_id']}:{today.year}:{today.month}:{parsed['category']}") or 0)

    if limit <= 0:
        state["risk_level"] = "safe"
        return state

    ratio = projected / limit
    state["budget_check"] = {"category": parsed["category"], "spent": current, "budget": limit, "percentage": round(ratio * 100, 1)}

    if ratio >= settings.BUDGET_BLOCKED_RATIO:
        state["risk_level"] = "blocked"
    elif ratio >= settings.BUDGET_WARNING_RATIO:
        state["risk_level"] = "warning"
    else:
        state["risk_level"] = "safe"
    return state
```

- [ ] **Step 3: 提交**

```bash
git add backend/app/agents/parser.py backend/app/agents/guardian.py
git commit -m "feat: Parser Node(HITL反问) + Guardian Node(Redis预算风控)"
```

---

### Task 7: Social Ledger + Oracle Node

**Files:**
- Create: `backend/app/agents/social.py`, `oracle.py`

- [ ] **Step 1: 编写 social.py — 最优债务抵消算法**

```python
# backend/app/agents/social.py
from app.agents.state import TransactionState

async def social_node(state: TransactionState) -> TransactionState:
    state["is_shared_ledger"] = False
    state["settlements"] = None
    return state

def minimize_debts(balances: dict[int, float], member_names: dict[int, str]) -> list[dict]:
    creditors = [(uid, amt) for uid, amt in balances.items() if amt > 0.01]
    debtors = [(uid, -amt) for uid, amt in balances.items() if amt < -0.01]
    creditors.sort(key=lambda x: -x[1])
    debtors.sort(key=lambda x: -x[1])
    settlements, i, j = [], 0, 0
    while i < len(debtors) and j < len(creditors):
        did, debt = debtors[i]; cid, credit = creditors[j]; amt = min(debt, credit)
        if amt > 0.01:
            settlements.append({"from_user_id": did, "from_user_name": member_names[did], "to_user_id": cid, "to_user_name": member_names[cid], "amount": round(amt, 2)})
        debtors[i] = (did, debt - amt); creditors[j] = (cid, credit - amt)
        if debtors[i][1] < 0.01: i += 1
        if creditors[j][1] < 0.01: j += 1
    return settlements
```

- [ ] **Step 2: 编写 oracle.py**

```python
# backend/app/agents/oracle.py
from app.agents.state import TransactionState

async def oracle_node(state: TransactionState) -> TransactionState:
    state["insight_triggered"] = True
    return state
```

- [ ] **Step 3: 提交**

```bash
git add backend/app/agents/social.py backend/app/agents/oracle.py
git commit -m "feat: Social Ledger Node(债务抵消算法) + Oracle Node(洞察触发桩)"
```

---

### Task 8: LangGraph 状态机组装

**Files:**
- Create: `backend/app/agents/graph.py`

- [ ] **Step 1: 编写 graph.py**

```python
# backend/app/agents/graph.py
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from app.agents.state import TransactionState
from app.agents.parser import parser_node
from app.agents.guardian import guardian_node
from app.agents.social import social_node
from app.agents.oracle import oracle_node

def route_after_parser(state: TransactionState) -> str:
    if state.get("error"): return END
    if state.get("missing_fields") and state.get("clarification_round", 0) <= 3: return END
    return "guardian"

def route_after_guardian(state: TransactionState) -> str:
    if state.get("risk_level") == "blocked": return END
    if state.get("is_shared_ledger"): return "social_ledger"
    return "oracle"

builder = StateGraph(TransactionState)
builder.add_node("parser", parser_node)
builder.add_node("guardian", guardian_node)
builder.add_node("social_ledger", social_node)
builder.add_node("oracle", oracle_node)
builder.set_entry_point("parser")
builder.add_conditional_edges("parser", route_after_parser, {"guardian": "guardian", END: END})
builder.add_conditional_edges("guardian", route_after_guardian, {"social_ledger": "social_ledger", "oracle": "oracle", END: END})
builder.add_edge("social_ledger", "oracle")
builder.add_edge("oracle", END)

compiled_graph = builder.compile(checkpointer=MemorySaver(), interrupt_before=["guardian"])
```

- [ ] **Step 2: 提交**

```bash
git add backend/app/agents/graph.py
git commit -m "feat: LangGraph StateGraph组装（4节点+条件边+HITL Checkpointer）"
```

---

## Phase 3: API 层（Tasks 9-12）

### Task 9: FastAPI 入口 + 依赖注入

**Files:**
- Create: `backend/app/main.py`, `backend/app/api/__init__.py`, `backend/app/api/deps.py`
- Create: `backend/app/api/v1/__init__.py`, `router.py`

- [ ] **Step 1: 编写 main.py**

```python
# backend/app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.core.database import init_db, close_db
from app.api.v1.router import api_router

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await close_db()

app = FastAPI(title=settings.APP_NAME, version="2.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(api_router, prefix="/api/v1")
```

- [ ] **Step 2: 编写 deps.py + router.py**

```python
# api/deps.py
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from app.core.database import get_db
from app.core.redis import get_redis
from app.core.security import get_current_user
from app.models import User

DBSession = Depends(get_db)
RedisClient = Depends(get_redis)
CurrentUser = Depends(get_current_user)

# api/v1/router.py
from fastapi import APIRouter
from app.api.v1 import auth, bills, ledgers, budgets, stats, insights, sse

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["认证"])
api_router.include_router(bills.router, prefix="/bills", tags=["账单"])
api_router.include_router(ledgers.router, prefix="/ledgers", tags=["账本"])
api_router.include_router(budgets.router, prefix="/budgets", tags=["预算"])
api_router.include_router(stats.router, prefix="/stats", tags=["统计"])
api_router.include_router(insights.router, prefix="/insights", tags=["洞察"])
api_router.include_router(sse.router, prefix="/sse", tags=["实时推送"])
```

- [ ] **Step 3: 提交**

```bash
git add backend/app/main.py backend/app/api/
git commit -m "feat: FastAPI入口 + 依赖注入层 + 路由聚合"
```

---

### Task 10: 核心 API — Auth + Transcribe (SSE) + 账单 CRUD

**Files:**
- Create: `backend/app/api/v1/auth.py`, `bills.py`, `sse.py`
- Create: `backend/app/services/__init__.py`, `bill_service.py`

- [ ] **Step 1: 编写 auth.py — 微信登录**

```python
# api/v1/auth.py
import httpx
from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from app.api.deps import DBSession, CurrentUser
from app.core.security import create_access_token
from app.models import User
from app.schemas.auth import LoginRequest, TokenResponse, UserOut
from app.config import get_settings

router = APIRouter()

@router.post("/login", response_model=TokenResponse)
async def wx_login(req: LoginRequest, db= DBSession):
    settings = get_settings()
    async with httpx.AsyncClient() as client:
        resp = await client.get("https://api.weixin.qq.com/sns/jscode2session", params={
            "appid": settings.WECHAT_APPID, "secret": settings.WECHAT_SECRET,
            "js_code": req.code, "grant_type": "authorization_code",
        })
    data = resp.json()
    openid = data.get("openid")
    if not openid:
        raise HTTPException(400, f"微信登录失败: {data.get('errmsg')}")
    result = await db.execute(select(User).where(User.openid == openid))
    user = result.scalar_one_or_none()
    if not user:
        user = User(openid=openid)
        db.add(user)
        await db.flush()
    return TokenResponse(access_token=create_access_token(user.id), user=UserOut.model_validate(user))

@router.get("/me", response_model=UserOut)
async def get_me(user: User = CurrentUser):
    return UserOut.model_validate(user)
```

- [ ] **Step 2: 编写 bill_service.py**

```python
# services/bill_service.py
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from redis.asyncio import Redis
from app.models import Bill

async def create_bill_from_parsed(db: AsyncSession, redis: Redis, user_id: int, ledger_id: int, parsed: dict, raw_input: str) -> Bill:
    bill = Bill(ledger_id=ledger_id, creator_id=user_id, type=parsed["type"], amount=parsed["amount"],
                category=parsed["category"], subcategory=parsed.get("subcategory"), account=parsed.get("account"),
                note=parsed.get("note"), bill_date=date.fromisoformat(parsed["bill_date"]) if parsed.get("bill_date") else date.today(),
                raw_input=raw_input, ai_parsed=True)
    db.add(bill)
    await db.flush()
    if parsed.get("amount") and parsed.get("category"):
        today = date.today()
        await redis.incrbyfloat(f"budget:{user_id}:{today.year}:{today.month}:{parsed['category']}", float(parsed["amount"]))
    return bill

async def get_bills_paginated(db: AsyncSession, ledger_id: int, page: int = 1, page_size: int = 20, year: int = None, month: int = None, category: str = None):
    query = select(Bill).where(Bill.ledger_id == ledger_id)
    count_q = select(func.count(Bill.id)).where(Bill.ledger_id == ledger_id)
    if year and month:
        query = query.where(func.extract("year", Bill.bill_date) == year, func.extract("month", Bill.bill_date) == month)
        count_q = count_q.where(func.extract("year", Bill.bill_date) == year, func.extract("month", Bill.bill_date) == month)
    if category:
        query = query.where(Bill.category == category)
        count_q = count_q.where(Bill.category == category)
    total = (await db.execute(count_q)).scalar()
    bills = (await db.execute(query.order_by(Bill.bill_date.desc(), Bill.created_at.desc()).offset((page - 1) * page_size).limit(page_size))).scalars().all()
    return list(bills), total
```

- [ ] **Step 3: 编写 bills.py — Transcribe SSE 核心接口**

参考 Spec §5.2。实现三场景 SSE 流：
1. 正常解析完成 → `event: completed`
2. 字段缺失 → `event: clarify` (HITL)
3. 预算告警 → `event: warning/blocked`

```python
# api/v1/bills.py
import json, uuid
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from app.api.deps import DBSession, RedisClient, CurrentUser
from app.models import User, Bill
from app.schemas.bill import TranscribeRequest, BillOut, BillListParams
from app.agents.graph import compiled_graph
from app.agents.state import TransactionState
from app.services.bill_service import create_bill_from_parsed, get_bills_paginated

router = APIRouter()

@router.post("/transcribe")
async def transcribe_bill(req: TranscribeRequest, user: User = CurrentUser, db= DBSession, redis= RedisClient):
    session_id = req.session_id or uuid.uuid4().hex[:12]
    initial_state: TransactionState = {
        "raw_input": req.text, "user_id": user.id, "ledger_id": req.ledger_id, "session_id": session_id,
        "parsed": None, "missing_fields": [], "clarification_question": None, "clarification_round": 0,
        "budget_check": None, "risk_level": "safe", "is_shared_ledger": False, "settlements": None,
        "insight_triggered": False, "error": None,
    }
    config = {"configurable": {"thread_id": session_id}}

    async def event_stream():
        async for event in compiled_graph.astream(initial_state, config):
            for node_name, node_state in event.items():
                if node_name == "parser" and node_state.get("parsed"):
                    yield f"data: {json.dumps({'event': 'parsed', 'data': {'parsed': node_state['parsed']}}, ensure_ascii=False)}\n\n"
                if node_state.get("clarification_question"):
                    yield f"data: {json.dumps({'event': 'clarify', 'data': {'question': node_state['clarification_question'], 'session_id': session_id}}, ensure_ascii=False)}\n\n"
                    return
                if node_name == "guardian":
                    bc = node_state.get("budget_check")
                    risk = node_state.get("risk_level")
                    if risk in ("warning", "blocked") and bc:
                        yield f"data: {json.dumps({'event': risk, 'data': bc}, ensure_ascii=False)}\n\n"
                if node_state.get("error"):
                    yield f"data: {json.dumps({'event': 'error', 'data': {'message': node_state['error']}}, ensure_ascii=False)}\n\n"
                    return
        final_state = compiled_graph.get_state(config).values
        parsed = final_state.get("parsed")
        if parsed and parsed.get("amount"):
            bill = await create_bill_from_parsed(db, redis, user.id, req.ledger_id, parsed, req.text)
            await db.commit()
            yield f"data: {json.dumps({'event': 'completed', 'data': {'bill': {'id': bill.id, 'amount': float(bill.amount), 'category': bill.category}}}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"})

@router.get("")
async def list_bills(params: BillListParams = Depends(), user: User = CurrentUser, db= DBSession):
    bills, total = await get_bills_paginated(db, params.ledger_id, params.page, params.page_size, params.year, params.month, params.category)
    return {"items": [BillOut.model_validate(b) for b in bills], "total": total, "page": params.page, "page_size": params.page_size}

@router.get("/{bill_id}", response_model=BillOut)
async def get_bill(bill_id: int, user: User = CurrentUser, db= DBSession):
    result = await db.execute(select(Bill).where(Bill.id == bill_id))
    bill = result.scalar_one_or_none()
    if not bill: raise HTTPException(404, "账单不存在")
    return BillOut.model_validate(bill)
```

- [ ] **Step 4: 编写 sse.py — SSE 订阅端点**

```python
# api/v1/sse.py
import json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from app.api.deps import RedisClient, CurrentUser
from app.models import User

router = APIRouter()

@router.get("/subscribe")
async def sse_subscribe(user: User = CurrentUser, redis= RedisClient):
    channel = f"sse:user:{user.id}"
    async def event_stream():
        pubsub = redis.pubsub()
        await pubsub.subscribe(channel)
        try:
            yield f"data: {json.dumps({'event': 'connected', 'data': {}}, ensure_ascii=False)}\n\n"
            async for message in pubsub.listen():
                if message["type"] == "message":
                    yield f"data: {message['data']}\n\n"
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.close()
    return StreamingResponse(event_stream(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"})
```

- [ ] **Step 5: 提交**

```bash
git add backend/app/api/v1/auth.py backend/app/api/v1/bills.py backend/app/api/v1/sse.py backend/app/services/
git commit -m "feat: 核心API — 微信登录 + Transcribe SSE记账 + SSE订阅 + 账单CRUD"
```

---

### Task 11: 剩余 API — Ledgers + Budgets + Stats + Insights

**Files:**
- Create: `backend/app/api/v1/ledgers.py`, `budgets.py`, `stats.py`, `insights.py`
- Create: `backend/app/services/ledger_service.py`, `budget_service.py`, `insight_service.py`

- [ ] **Step 1: 编写 ledgers.py — 多账本管理**

实现：GET /ledgers, POST /ledgers, POST /ledgers/{id}/join
参考 Spec §5.1 路由表 + PRD US-08~US-11

- [ ] **Step 2: 编写 budgets.py — 预算管理**

实现：PUT /budgets, GET /budgets/status
预算设置同步写入 Redis `budget_limit:{uid}:{year}:{month}:{cat}` 供 Guardian 快速读取

- [ ] **Step 3: 编写 stats.py — 统计分析**

实现：GET /stats/overview (本月收支总和), GET /stats/trend (近12月趋势), GET /stats/category (分类汇总)

- [ ] **Step 4: 编写 insights.py — AI 洞察**

实现：GET /insights (列表), GET /insights/{id} (详情), POST /insights/generate (手动触发)

- [ ] **Step 5: 提交**

```bash
git add backend/app/api/v1/ledgers.py backend/app/api/v1/budgets.py backend/app/api/v1/stats.py backend/app/api/v1/insights.py backend/app/services/
git commit -m "feat: 完整API — 账本/预算/统计/洞察 CRUD + 预算Redis同步"
```

---

### Task 12: RAG 知识库模块

**Files:**
- Create: `backend/app/rag/__init__.py`, `chroma_store.py`, `embeddings.py`, `retriever.py`
- Create: `backend/app/rag/seed_data/finance_tips.jsonl`

- [ ] **Step 1: 编写 rag 模块**

```python
# rag/chroma_store.py
import chromadb
from chromadb.config import Settings as ChromaSettings
from app.config import get_settings

_client = None

def get_chroma_client():
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=get_settings().CHROMA_PERSIST_DIR, settings=ChromaSettings(anonymized_telemetry=False))
    return _client

def get_finance_collection():
    return get_chroma_client().get_or_create_collection(name="finance_tips")

# rag/retriever.py
def retrieve_relevant_tips(query: str, top_k: int = 5) -> list[str]:
    results = get_finance_collection().query(query_texts=[query], n_results=top_k)
    return results.get("documents", [[]])[0] if results else []

def seed_finance_tips(tips: list[dict]):
    collection = get_finance_collection()
    if collection.count() > 0: return
    collection.add(ids=[f"tip_{i}" for i in range(len(tips))], documents=[t["content"] for t in tips],
                   metadatas=[{"category": t.get("category", "general")} for t in tips])
```

- [ ] **Step 2: 编写种子数据**

参考 Spec §10.2，涵盖餐饮/交通/购物/居住/储蓄/信用卡/保险 7 类理财知识。

- [ ] **Step 3: 提交**

```bash
git add backend/app/rag/
git commit -m "feat: RAG知识库模块（ChromaDB + 理财种子数据7类）"
```

---

## Phase 4: 测试（Task 13）

### Task 13: 后端测试

**Files:**
- Create: `backend/tests/conftest.py`, `test_parser.py`, `test_guardian.py`, `test_social.py`, `test_graph.py`
- Create: `backend/tests/test_api/test_transcribe.py`

- [ ] **Step 1: 编写 conftest.py**

```python
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.models.base import Base

@pytest.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///./test.db", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()
    await engine.dispose()
```

- [ ] **Step 2: 编写 test_parser.py**

```python
@pytest.mark.asyncio
async def test_parser_extracts_complete_bill(mocker):
    async def mock_call(*a, **kw): return {"type": "expense", "amount": 68.0, "category": "餐饮美食"}
    mocker.patch("app.agents.parser.LLMClient.call_with_tools", side_effect=mock_call)
    state = {"raw_input": "午饭68块", "user_id": 1, "ledger_id": 1, "session_id": "t1",
             "parsed": None, "missing_fields": [], "clarification_question": None, "clarification_round": 0,
             "budget_check": None, "risk_level": "safe", "is_shared_ledger": False, "settlements": None,
             "insight_triggered": False, "error": None}
    result = await parser_node(state)
    assert result["parsed"]["amount"] == 68.0
    assert result["missing_fields"] == []

@pytest.mark.asyncio
async def test_parser_triggers_clarify_when_amount_missing(mocker):
    async def mock_call(*a, **kw): return {"type": "expense", "amount": None, "category": "餐饮美食"}
    mocker.patch("app.agents.parser.LLMClient.call_with_tools", side_effect=mock_call)
    state = {"raw_input": "吃了个饭", "user_id": 1, "ledger_id": 1, "session_id": "t2",
             "parsed": None, "missing_fields": [], "clarification_question": None, "clarification_round": 0,
             "budget_check": None, "risk_level": "safe", "is_shared_ledger": False, "settlements": None,
             "insight_triggered": False, "error": None}
    result = await parser_node(state)
    assert "amount" in result["missing_fields"]
    assert result["clarification_question"] is not None
```

- [ ] **Step 3: 编写 test_social.py — 债务算法测试**

```python
from app.agents.social import minimize_debts

def test_minimize_debts_simple():
    balances = {1: -50.0, 2: 30.0, 3: 20.0}
    names = {1: "A", 2: "B", 3: "C"}
    result = minimize_debts(balances, names)
    assert len(result) == 2
    assert result[0]["amount"] == 30.0

def test_minimize_debts_circular():
    balances = {1: 0.0, 2: 0.0, 3: 0.0}
    names = {1: "A", 2: "B", 3: "C"}
    assert len(minimize_debts(balances, names)) == 0

def test_minimize_debts_equal_split():
    balances = {1: 90.0, 2: -30.0, 3: -30.0, 4: -30.0}
    names = {1: "A", 2: "B", 3: "C", 4: "D"}
    result = minimize_debts(balances, names)
    assert len(result) == 3
    assert sum(s["amount"] for s in result) == 90.0
```

- [ ] **Step 4: 编写 test_graph.py — 条件边路由测试**

```python
from app.agents.graph import route_after_parser, route_after_guardian

def test_route_parser_hitl(): assert route_after_parser({"missing_fields": ["amount"], "clarification_round": 1}) == "__end__"
def test_route_parser_proceed(): assert route_after_parser({"missing_fields": [], "clarification_round": 0}) == "guardian"
def test_route_guardian_blocked(): assert route_after_guardian({"risk_level": "blocked"}) == "__end__"
def test_route_guardian_safe(): assert route_after_guardian({"risk_level": "safe", "is_shared_ledger": False}) == "oracle"
```

- [ ] **Step 5: 运行测试**

```bash
cd backend && pip install -e ".[dev]" && python -m pytest tests/ -v
```

- [ ] **Step 6: 提交**

```bash
git add backend/tests/
git commit -m "test: Agent节点单元测试 + 状态机路由测试 + 债务算法测试"
```

---

## Phase 5: 前端重构（Tasks 14-16）

### Task 14: 前端基础设施 — Pinia + API 层 + 原子化 CSS

**Files:**
- Modify: `src/main.ts` (挂载 Pinia)
- Modify: `src/App.vue` (挂载 SSEHandler)
- Create: `src/api/client.ts`, `auth.ts`, `bills.ts`, `ledgers.ts`, `budgets.ts`, `stats.ts`, `insights.ts`
- Create: `src/stores/user.ts`, `ledger.ts`, `bill.ts`, `budget.ts`, `sse.ts`
- Create: `src/styles/atoms.css`, `tokens.css`, `theme.css`
- Create: `src/utils/sse.ts`
- Modify: `src/types/index.ts` (更新类型定义)

- [ ] **Step 1: 编写 API 客户端 client.ts**

```typescript
// src/api/client.ts
import { useUserStore } from "@/stores/user";
const BASE_URL = import.meta.env.VITE_API_BASE || "https://api.rongxiaozhang.cn/api/v1";

export async function api<T = any>(path: string, opts: { method?: string; body?: any; params?: Record<string, any> } = {}): Promise<T> {
  const { method = "GET", body, params } = opts;
  let url = `${BASE_URL}${path}`;
  if (params) {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => { if (v !== undefined && v !== null) qs.append(k, String(v)); });
    if (qs.toString()) url += "?" + qs.toString();
  }
  const userStore = useUserStore();
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (userStore.token) headers["Authorization"] = `Bearer ${userStore.token}`;
  const res = await uni.request({ url, method, header: headers, data: body });
  if (res.statusCode === 401) { userStore.logout(); throw new Error("登录过期"); }
  if (res.statusCode >= 400) throw new Error((res.data as any)?.detail || "请求失败");
  return res.data as T;
}
```

- [ ] **Step 2: 编写 6 个 API 模块**

```typescript
// api/auth.ts
export function wxLogin(code: string) { return api("/auth/login", { method: "POST", body: { code } }); }
export function getMe() { return api("/auth/me"); }

// api/bills.ts
export function transcribeBill(text: string, ledgerId: number, sessionId?: string) {
  return api("/bills/transcribe", { method: "POST", body: { text, ledger_id: ledgerId, session_id: sessionId } }); }
export function getBills(params: any) { return api("/bills", { params }); }

// api/ledgers.ts
export function getLedgers() { return api("/ledgers"); }
export function createLedger(name: string, type: string) { return api("/ledgers", { method: "POST", body: { name, type } }); }
export function joinLedger(ledgerId: number, inviteCode: string) { return api(`/ledgers/${ledgerId}/join`, { method: "POST", body: { invite_code: inviteCode } }); }

// api/budgets.ts
export function setBudget(data: any) { return api("/budgets", { method: "PUT", body: data }); }
export function getBudgetStatus(ledgerId: number) { return api("/budgets/status", { params: { ledger_id: ledgerId } }); }

// api/stats.ts
export function getOverview(ledgerId: number) { return api("/stats/overview", { params: { ledger_id: ledgerId } }); }
export function getTrend(ledgerId: number, months = 12) { return api("/stats/trend", { params: { ledger_id: ledgerId, months } }); }
export function getCategoryStats(ledgerId: number) { return api("/stats/category", { params: { ledger_id: ledgerId } }); }

// api/insights.ts
export function getInsights() { return api("/insights"); }
export function getInsight(id: number) { return api(`/insights/${id}`); }
```

- [ ] **Step 3: 编写 5 个 Pinia Stores**

参考 Spec §6.2。核心 stores：

- `user.ts`：token 持久化 + wx.login → JWT + fetchUser
- `ledger.ts`：多账本列表 + currentId 切换
- `bill.ts`：分页账单 + prepend (SSE 完成后即时插入)
- `budget.ts`：实时预算状态 + alertVisible/alertData (SSE 触发)
- `sse.ts`：connect(token) + handleEvent 分发 → budgetStore.showAlert / billStore.prepend

- [ ] **Step 4: 编写原子化 CSS**

```css
/* styles/tokens.css */
:root {
  --color-primary: #2979ff; --color-danger: #ff4757; --color-warning: #ffa502;
  --color-success: #2ed573; --color-bg: #f5f6fa; --color-card: #ffffff;
  --color-text: #1a1a2e; --color-text-secondary: #6b7280;
  --radius-sm: 8rpx; --radius-md: 16rpx; --shadow-sm: 0 2rpx 8rpx rgba(0,0,0,.06);
}

/* styles/atoms.css */
.flex{display:flex}.flex-col{flex-direction:column}.flex-center{display:flex;align-items:center;justify-content:center}
.flex-between{display:flex;align-items:center;justify-content:space-between}.flex-1{flex:1}
.gap-sm{gap:16rpx}.gap-md{gap:24rpx}.p-sm{padding:16rpx}.p-md{padding:24rpx}.p-lg{padding:32rpx}
.mt-sm{margin-top:16rpx}.mb-sm{margin-bottom:16rpx}.mb-md{margin-bottom:24rpx}
.text-sm{font-size:24rpx}.text-md{font-size:28rpx}.text-lg{font-size:32rpx}.text-xl{font-size:40rpx}.text-2xl{font-size:48rpx}
.font-bold{font-weight:700}.text-center{text-align:center}
.text-primary{color:var(--color-primary)}.text-secondary{color:var(--color-text-secondary)}
.text-danger{color:var(--color-danger)}.text-warning{color:var(--color-warning)}.text-success{color:var(--color-success)}
.bg-card{background:var(--color-card)}.rounded-md{border-radius:var(--radius-md)}.rounded-lg{border-radius:24rpx}
.shadow-sm{box-shadow:var(--shadow-sm)}
```

- [ ] **Step 5: 修改 main.ts + App.vue**

```typescript
// main.ts — 挂载 Pinia
import { createSSRApp } from "vue"; import { createPinia } from "pinia"; import uviewPlus from "uview-plus"; import App from "./App.vue";
export function createApp() { const app = createSSRApp(App); app.use(createPinia()); app.use(uviewPlus); return { app }; }
```

```vue
<!-- App.vue — 挂载 SSEHandler -->
<script setup lang="ts">import SSEHandler from "@/components/SSEHandler.vue";</script>
<style lang="scss">@import "uview-plus/index.scss"; @import "@/styles/tokens.css"; @import "@/styles/atoms.css"; page{background-color:var(--color-bg)}</style>
```

- [ ] **Step 6: 编写 SSEHandler.vue + BudgetAlert.vue**

```vue
<!-- components/SSEHandler.vue: 隐藏组件，全局SSE连接 -->
<template><view style="display:none"/></template>
<script setup lang="ts">
import { onMounted } from "vue"; import { useSSEStore } from "@/stores/sse"; import { useUserStore } from "@/stores/user";
onMounted(() => { const u = useUserStore(); if (u.token) useSSEStore().connect(u.token); });
</script>
```

```vue
<!-- components/BudgetAlert.vue: 黄/红两级预算告警弹窗 -->
<template>
  <u-modal :show="store.alertVisible" :title="isBlocked ? '🔴 预算超限' : '🟡 预算告警'"
    @confirm="store.dismissAlert" confirmText="仍然记账" cancelText="取消">
    <view class="text-center p-md">
      <text class="text-2xl">{{ isBlocked ? '🔴' : '🟡' }}</text>
      <view class="mt-sm text-lg font-bold" :class="isBlocked ? 'text-danger' : 'text-warning'">
        {{ isBlocked ? '预算已用尽！' : `已用 ${store.alertData?.percentage}%` }}</view>
      <view class="mt-sm text-secondary text-sm" v-if="store.alertData">
        已花 ¥{{ store.alertData.spent }} / 预算 ¥{{ store.alertData.budget }}</view>
    </view>
  </u-modal>
</template>
<script setup lang="ts">import { computed } from "vue"; import { useBudgetStore } from "@/stores/budget";
const store = useBudgetStore(); const isBlocked = computed(() => store.alertData?.percentage >= 100);
</script>
```

- [ ] **Step 7: 提交**

```bash
git add src/api/ src/stores/ src/styles/ src/utils/sse.ts src/types/ src/main.ts src/App.vue src/components/SSEHandler.vue src/components/BudgetAlert.vue
git commit -m "feat: 前端重构 — Pinia(5Stores) + API层(6模块) + 原子化CSS + SSE全局处理"
```

---

### Task 15: AI 记账页 + ECharts 图表组件 + 新页面路由

**Files:**
- Create: `src/pages/transcribe/index.vue`（★核心 AI 记账页）
- Create: `src/components/charts/TrendLine.vue`, `CategoryPie.vue`, `BudgetGauge.vue`
- Create: `src/pages/bills/detail.vue`, `src/pages/ledgers/{index,members,settle}.vue`, `src/pages/insights/{index,report}.vue`
- Modify: `src/pages.json`

- [ ] **Step 1: 编写 AI 记账页 transcribe/index.vue**

参考 Spec §6.4 UI 结构。核心流程：
1. 输入框 → 调用 `transcribeBill()` API
2. 展示 AI 解析结果卡片（金额/分类/日期/账户，每项可点击修改）
3. 若 clarify → 展示反问
4. 若有 budget_check → BudgetAlert 弹窗
5. 用户确认 → 完成记账

- [ ] **Step 2: 编写 ECharts 图表组件**

`TrendLine.vue`：props.data → ECharts 折线图（支出红/收入绿，微信小程序用 ec-canvas）
`CategoryPie.vue`：props.data → ECharts 环形饼图
`BudgetGauge.vue`：props.statuses → 预算进度仪表盘

- [ ] **Step 3: 更新 pages.json 路由**

新增 7 个页面路径 + TabBar 调整（将"记账"Tab 指向 `pages/transcribe/index`）

- [ ] **Step 4: 提交**

```bash
git add src/pages/transcribe/ src/components/charts/ src/pages/bills/detail.vue src/pages/ledgers/ src/pages/insights/ src/pages.json
git commit -m "feat: AI记账页 + ECharts图表(3组件) + 新页面路由(7个)"
```

---

### Task 16: 存量页面适配

**Files:**
- Modify: `src/pages/home/index.vue`, `bills/index.vue`, `stats/index.vue`, `budget/index.vue`, `accounts/index.vue`, `categories/index.vue`, `settings/index.vue`

- [ ] **Step 1: 逐个改造页面**

每个页面执行相同模式：
1. 删除 `import { ... } from "@/utils/store"` 所有引用
2. 替换为 `useXxxStore()` Pinia Store
3. `onShow` 中调用 `store.fetch()` 从 API 获取数据
4. `stats/index.vue` 额外：删除手写 Canvas 代码 → 替换为 `<TrendLine>`, `<CategoryPie>`

- [ ] **Step 2: 提交**

```bash
git add src/pages/
git commit -m "feat: 全页面接入Pinia+API，ECharts替换Canvas"
```

---

## Phase 6: 部署与验证（Tasks 17-18）

### Task 17: 数据库迁移 + 部署配置

- [ ] **Step 1: Alembic 初始化**

```bash
cd backend && pip install alembic && alembic init alembic
```

- [ ] **Step 2: 配置 alembic/env.py 指向 Base.metadata**

- [ ] **Step 3: 生成迁移 + 部署**

```bash
alembic revision --autogenerate -m "initial: 8 tables"
alembic upgrade head
```

- [ ] **Step 4: 提交**

```bash
git add backend/alembic.ini backend/alembic/
git commit -m "feat: Alembic数据库迁移配置"
```

---

### Task 18: 端到端验证

- [ ] **Step 1: 启动后端验证**

```bash
cd backend && pip install -e ".[dev]" && uvicorn app.main:app --reload
# 验证: http://localhost:8080/docs (Swagger UI)
```

- [ ] **Step 2: API 测试**

```bash
# 1. Login → 2. Create Ledger → 3. Transcribe → 4. Set Budget → 5. Stats → 6. Insights
curl -X POST localhost:8080/api/v1/auth/login -d '{"code":"test"}'
curl -X POST localhost:8080/api/v1/bills/transcribe -H "Authorization: Bearer $TOKEN" -d '{"text":"午饭68块","ledger_id":1}'
```

- [ ] **Step 3: 前端构建**

```bash
npm run build:h5 && npm run build:mp-weixin
```

- [ ] **Step 4: 提交 + 推送**

```bash
git add -A && git commit -m "feat: E2E验证通过，荣小账v2.0重构完成"
git push origin feat/v2-rebuild
```

---

## 总结

| Phase | Tasks | 交付物 |
|-------|-------|--------|
| 1: 后端基础 | 1-4 | FastAPI + ORM + Redis/JWT/LLM + Schema |
| 2: Agent 系统 | 5-8 | State + Tools + 4 Nodes + Graph |
| 3: API 层 | 9-12 | 全部 REST 端点 + SSE + RAG |
| 4: 测试 | 13 | 单元测试 + 算法测试 + 路由测试 |
| 5: 前端 | 14-16 | Pinia + API + 原子化CSS + AI记账页 + ECharts |
| 6: 部署 | 17-18 | DB迁移 + E2E验证 |


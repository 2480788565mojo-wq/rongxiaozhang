# 荣小账 v2.0 — 智能记账/财务协同系统技术规格文档

> **文档类型**：Technical Specification / System Design Doc
> **版本**：v2.0
> **日期**：2026-07-14
> **状态**：已确认
> **作者**：荣小账开发团队

---

## 目录

1. [项目背景与痛点映射](#1-项目背景与痛点映射)
2. [系统架构总览](#2-系统架构总览)
3. [LangGraph 多 Agent 状态机](#3-langgraph-多-agent-状态机)
4. [数据库设计](#4-数据库设计)
5. [API 设计](#5-api-设计)
6. [前端架构](#6-前端架构)
7. [后端项目结构](#7-后端项目结构)
8. [LangGraph 代码契约](#8-langgraph-代码契约)
9. [核心算法：最优债务抵消](#9-核心算法最优债务抵消)
10. [RAG 知识库设计](#10-rag-知识库设计)
11. [关键决策记录](#11-关键决策记录)
12. [验证方案](#12-验证方案)

---

## 1. 项目背景与痛点映射

### 1.1 项目现状

荣小账 v1.0 是一个已发布的 uni-app 微信记账小程序（appid: `wx790e9576e610670e`），当前架构为：

- **前端**：uni-app (Vue 3 + TypeScript) + uView Plus UI 组件库
- **数据存储**：纯本地存储（`uni.getStorageSync`），无后端、无云同步
- **图表**：手写 Canvas API 绘图（uCharts 已安装但未使用）
- **状态管理**：无 Pinia/Vuex，页面直接调用 `src/utils/store.ts` 函数

### 1.2 四大业务痛点 → 技术方案映射

| # | 业务痛点 | 用户影响 | 技术方案 | 对应 Agent |
|---|---------|---------|---------|-----------|
| 1 | **记账录入阻力大** | 传统填表式记账步骤繁琐（选类型→输金额→选分类→选账户→填日期→写备注），用户极易流失 | 自然语言/语音输入 + LLM Function Calling 自动提取结构化数据 + HITL 反问澄清缺失字段 | **Parser Node** |
| 2 | **预算风控严重滞后** | 传统记账只能"事后看报表"，用户超支时已无法挽回 | 消费落库前 Redis 实时流控检查 + SSE 推送黄色告警/红色拦截 + 视觉强打断 | **Guardian Node** |
| 3 | **多人协同账本混乱** | 室友/情侣/团队出游场景下，并发记账冲突频发，AA 结算计算复杂易错 | Redis 分布式锁保护写入 + 图论最优债务抵消算法 + 微信分享邀请机制 | **Social Ledger Node** |
| 4 | **财务数据无洞察力** | 纯粹图表堆砌无法指导用户决策，用户不知道"下一步该怎么做" | MySQL 长序列消费数据分析 + ChromaDB RAG 理财知识库检索 + LLM 深度推理生成可执行建议 | **Oracle Node** |

### 1.3 技术栈红线（不可变）

| 层 | 技术选型 | 约束 |
|----|---------|------|
| 前端框架 | UniApp + Vue 3 + Pinia + TypeScript | Vue ^3.4 |
| UI 方案 | 原子化 CSS（自建）+ ECharts | 替换 uView Plus 表单 + 手写 Canvas |
| 后端框架 | FastAPI (Python 3.10+) + Pydantic v2 | 异步非阻塞 |
| AI 编排 | **LangGraph StateGraph** + MemorySaver Checkpointer | 严禁 AgentExecutor / LLMChain / RetrievalQA |
| 业务数据库 | MySQL 8.0（8 表，多账本隔离） | InnoDB，utf8mb4 |
| 缓存/并发 | Redis 7.0 | 预算计数器 + 分布式锁 + SSE Pub/Sub |
| 向量数据库 | ChromaDB（嵌入模式） | 轻量级，零运维 |
| LLM Provider | DeepSeek-V3（高频解析）+ Qwen-Max（深度推理） | 混合路由，按场景选模型 |
| 部署 | 微信云托管 CloudBase Run | 免备案 HTTPS，支持 SSE 长连接 |

### 1.4 严禁使用清单

```
❌ langchain.agents.AgentExecutor
❌ langchain.chains.LLMChain
❌ langchain.chains.ConversationChain
❌ langchain.chains.RetrievalQA
❌ langchain.agents.create_openai_functions_agent
✅ 仅允许：langgraph + langchain-core (messages, tools) + 底层 LLM SDK (openai)
```

---

## 2. 系统架构总览

### 2.1 五层架构图

```
┌──────────────────────────────────────────────────────────────┐
│  表现层 (Presentation)                                        │
│  UniApp (Vue 3 + Pinia + TypeScript)                         │
│  微信小程序 / H5 Web / Windows 桌面                           │
│  原子化 CSS + ECharts 图表                                    │
└──────────────────────┬───────────────────────────────────────┘
                       │ HTTPS (REST JSON + SSE Stream)
┌──────────────────────▼───────────────────────────────────────┐
│  API 网关层 (Gateway)                                         │
│  FastAPI + Uvicorn                                            │
│  CORS 中间件 / JWT Bearer 认证 / 请求限流 / SSE 连接管理       │
└──────────────────────┬───────────────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────────────┐
│  Agent 编排层 (Orchestration) ★ 核心                           │
│  LangGraph StateGraph                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │  Parser  │─▶│ Guardian │─▶│  Social  │─▶│  Oracle  │    │
│  │   Node   │  │   Node   │  │ Ledger N.│  │   Node   │    │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘    │
│       │HITL         │SSE Push    │Redis Lock │RAG + LLM    │
│       │反问澄清      │预算告警     │债务抵消    │深度洞察      │
│       ▼             ▼            ▼           ▼             │
│  Conditional Edges + MemorySaver Checkpointer               │
└──────────────────────┬───────────────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────────────┐
│  数据与服务层 (Data & Services)                                │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                   │
│  │ MySQL 8.0│  │ Redis 7.0│  │ChromaDB  │                   │
│  │ 8 张业务表│  │ 计数器/锁 │  │ 向量检索  │                   │
│  └──────────┘  └──────────┘  └──────────┘                   │
└──────────────────────────────────────────────────────────────┘
```

### 2.2 核心数据流

```
用户输入: "午饭湘菜花了68块"
    │
    ▼
┌─────────────────────────────────────────────────────┐
│ POST /api/v1/bills/transcribe  (SSE Streaming)       │
│                                                      │
│  ┌─────────┐   ┌──────────┐   ┌────────┐   ┌──────┐│
│  │ Parser  │──▶│ Guardian │──▶│ Social │──▶│Oracle││
│  │ 68元/   │   │ 餐饮95%  │   │ 个人   │   │ 异步 ││
│  │ 餐饮/   │   │ ⚠️告警   │   │ 账本   │   │ 触发 ││
│  │ 微信支付 │   │          │   │ 跳过   │   │      ││
│  └─────────┘   └──────────┘   └────────┘   └──────┘│
│                                                      │
│  SSE Events:                                         │
│  1. event: parsed     → {parsed: {...}}              │
│  2. event: warning    → {category, spent, budget}    │
│  3. event: completed  → {bill: {...}}                │
└─────────────────────────────────────────────────────┘
    │
    ▼
MySQL INSERT bill → Redis INCRBY budget counter → SSE push insight_ready
```

---

## 3. LangGraph 多 Agent 状态机

### 3.1 TransactionState

```python
from typing import TypedDict, Literal, Optional, NotRequired

class TransactionState(TypedDict, total=False):
    # === 输入 ===
    raw_input: str                     # "午饭湘菜68块"
    user_id: int
    ledger_id: int
    session_id: str                    # 多轮对话标识

    # === Parser 产出 ===
    parsed: Optional[dict]             # ParsedBill
    missing_fields: list[str]          # ["amount"] → 触发 HITL
    clarification_question: Optional[str]
    clarification_round: int           # 最多 3 轮

    # === Guardian 产出 ===
    budget_check: Optional[dict]       # BudgetCheck
    risk_level: Literal["safe", "warning", "blocked"]

    # === Social 产出 ===
    is_shared_ledger: bool
    settlements: Optional[list[dict]]  # DebtSettlement[]

    # === Oracle 产出 ===
    insight_triggered: bool

    # === 错误 ===
    error: Optional[str]
```

### 3.2 节点一：Parser Node

**LLM**：DeepSeek-V3（快、便宜、中文强）
**机制**：Pydantic v2 → OpenAI Function Calling tool → 字段完整性检查

```
用户输入 ──▶ LLM Function Calling ──▶ ParsedBill(BaseModel)
                  │
          ┌───────┴───────┐
          │ 字段完整性检查  │
          └───────┬───────┘
            ┌─────┴─────┐
            │           │
       全部完整      缺少字段
            │           │
            ▼           ▼
      → Guardian    → HITL 中断
                      clarification_question = "请问花了多少钱？"
                      → __end__ (前端展示反问)
                      → 用户补充后 resume（最多3轮）
```

**Function Calling Schema**：

```python
class ParsedBill(BaseModel):
    type: Literal["expense", "income"]
    amount: Optional[float]        # None → 触发反问
    category: Optional[str]        # 9 大类枚举
    subcategory: Optional[str]
    account: Optional[str]
    note: Optional[str]
    bill_date: Optional[str]       # 默认今天
```

### 3.3 节点二：Guardian Node

**执行方式**：在落库前并行执行
**Redis 计数器**：`budget:{user_id}:{year}:{month}:{category}` → `INCRBYFLOAT amount`

| 预算消耗 | risk_level | 行为 |
|---------|-----------|------|
| < 80% | `safe` | 静默放行 |
| 80% ~ 100% | `warning` | SSE 推送黄色告警弹窗，用户确认后继续 |
| ≥ 100% | `blocked` | SSE 推送红色全屏告警，用户二次确认后才能强行记账 |

**SSE 告警事件**：

```json
{
  "event": "warning",
  "data": {
    "category": "餐饮美食",
    "spent": 2850,
    "budget": 3000,
    "percentage": 95,
    "message": "⚠️ 本月餐饮预算已用95%，剩余仅¥150"
  }
}
```

### 3.4 节点三：Social Ledger Node

**触发条件**：`ledger.type == "shared"`
**并发控制**：Redis 分布式锁 `lock:ledger:{ledger_id}:write`（5 秒超时，Lua 安全释放）
**核心算法**：最优债务抵消（见 §9）

### 3.5 节点四：Oracle Node

**触发方式**：异步（BackgroundTasks），不阻塞主流程
**RAG 流程**：

```
1. SQL 查询近 3 个月消费记录
2. 消费记录 → Embedding → ChromaDB 检索 Top-K 理财知识
3. 组装 Prompt: System(理财顾问) + Context(检索知识) + User(消费数据摘要)
4. LLM (Qwen-Max) 生成报告
5. 结果写入 MySQL insights 表
6. Redis Pub/Sub → SSE 推送 insight_ready 通知前端
```

### 3.6 状态机路由

```
START → parser
           │
    ┌──────┴──────┐
    │ 条件边       │
    └──────┬──────┘
   ┌───────┴───────┐
   │               │
 fields 完整     fields 缺失
   │               │
   ▼               ▼
guardian         __end__ (HITL)
   │
┌──┴──────────┐
│ 条件边       │
└──┬──────────┘
   │
safe/warning → social_ledger (if shared) or oracle (if personal)
blocked      → __end__ (等待用户二次确认)

social_ledger → oracle → END
```

---

## 4. 数据库设计

### 4.1 ER 图

```
users ──1:N──▶ ledgers ──1:N──▶ bills
  │               │                │
  │               │                ├── bill_shares (AA 分摊)
  │               │                │
  │               ├── ledger_members (成员 M:N)
  │               │
  │               ├── budgets
  │               │
  └── 1:N ────────▶ insights
                   chat_history
```

### 4.2 核心表（8 张）

| 表名 | 核心字段 | 职责 |
|------|---------|------|
| `users` | id, openid, nickname, avatar_url | 微信用户 |
| `ledgers` | id, name, type(个人/共享), owner_id, invite_code | 账本 |
| `ledger_members` | ledger_id, user_id, role(owner/admin/member) | 成员关系 |
| `bills` | id, ledger_id, creator_id, type, amount, category, bill_date, raw_input, ai_parsed | 账单 |
| `bill_shares` | bill_id, user_id, share_amount, settled | AA 分摊 |
| `budgets` | user_id, ledger_id, year, month, total_budget, category_budgets(JSON) | 预算 |
| `insights` | user_id, ledger_id, report_type, content, key_findings(JSON), suggested_actions(JSON) | AI 洞察 |
| `chat_history` | user_id, session_id, role, content | 对话记录 |

### 4.3 关键索引

```sql
-- bills: 按月 + 分类查询
INDEX idx_ledger_date (ledger_id, bill_date)
INDEX idx_ledger_category (ledger_id, category, bill_date)

-- budgets: 用户月度唯一预算
UNIQUE KEY uk_user_ym_ledger (user_id, year, month, ledger_id)

-- insights: 按用户 + 类型倒序
INDEX idx_user_type (user_id, report_type, generated_at DESC)
```

---

## 5. API 设计

### 5.1 完整路由表

```
# ─── 认证 ───
POST   /api/v1/auth/login              # 微信 code → JWT token
GET    /api/v1/auth/me                  # 当前用户信息

# ─── 账本 ───
GET    /api/v1/ledgers                  # 我的账本列表
POST   /api/v1/ledgers                  # 创建账本
GET    /api/v1/ledgers/{id}             # 账本详情 + 成员
POST   /api/v1/ledgers/{id}/join        # 邀请码加入
POST   /api/v1/ledgers/{id}/settle      # 触发最优债务计算

# ─── 账单（核心）───
POST   /api/v1/bills/transcribe         # ★ AI 自然语言记账（SSE Stream）
GET    /api/v1/bills                    # 账单列表（分页 + 筛选）
GET    /api/v1/bills/{id}               # 账单详情（含 AA 分摊）
PUT    /api/v1/bills/{id}               # 修改账单
DELETE /api/v1/bills/{id}               # 删除账单

# ─── 预算 ───
GET    /api/v1/budgets                  # 预算查询
PUT    /api/v1/budgets                  # 设置/更新预算
GET    /api/v1/budgets/status           # 实时预算消耗（Redis 读取）

# ─── 统计 ───
GET    /api/v1/stats/overview           # 仪表盘总览
GET    /api/v1/stats/trend              # N 月趋势
GET    /api/v1/stats/category           # 分类统计

# ─── 洞察 ───
POST   /api/v1/insights/generate        # 手动生成洞察
GET    /api/v1/insights                 # 洞察列表
GET    /api/v1/insights/{id}            # 报告详情

# ─── 实时推送 ───
GET    /api/v1/sse/subscribe            # SSE 事件流
```

### 5.2 核心接口：POST /bills/transcribe

**请求**：
```json
{
  "text": "午饭湘菜68块",
  "ledger_id": 1,
  "session_id": "abc123"
}
```

**SSE 事件流（分场景）**：

场景 1 — 正常完成：
```
event: parsed    data: {"parsed":{"type":"expense","amount":68,"category":"餐饮美食",...}}
event: completed data: {"bill":{"id":42,"amount":68,"category":"餐饮美食"}}
```

场景 2 — HITL 反问：
```
event: clarify   data: {"question":"请问花了多少钱？","session_id":"abc123"}
// 用户回复 "68块" → 再次 POST with session_id
event: parsed    data: {...}
event: completed data: {...}
```

场景 3 — 预算告警：
```
event: parsed    data: {...}
event: warning   data: {"category":"餐饮美食","spent":2850,"budget":3000,"percentage":95}
// 用户点击"仍然记账" → 继续
event: completed data: {...}
```

---

## 6. 前端架构

### 6.1 目录结构（重构后）

```
src/
├── main.ts                          # 挂载 Pinia + uView Plus
├── App.vue                          # 挂载 SSEHandler（全局隐藏组件）
├── pages.json                       # 路由 + TabBar（新增 7 个页面）
│
├── pages/
│   ├── home/index.vue               # 仪表盘（接入 Pinia + API）
│   ├── transcribe/index.vue         # ★ AI 记账页
│   ├── bills/index.vue              # 账单列表（支持账本切换）
│   ├── bills/detail.vue             # ★ 账单详情（AA 分摊展示）
│   ├── stats/index.vue              # 统计（ECharts 替换 Canvas）
│   ├── budget/index.vue             # 预算管理（实时进度条 + SSE 告警）
│   ├── ledgers/index.vue            # ★ 多账本管理
│   ├── ledgers/members.vue          # ★ 成员管理
│   ├── ledgers/settle.vue           # ★ AA 结算
│   ├── insights/index.vue           # ★ AI 洞察列表
│   ├── insights/report.vue          # ★ 洞察报告详情
│   ├── accounts/index.vue           # 账户管理（接入 API）
│   ├── categories/index.vue         # 分类管理（接入 API）
│   ├── settings/index.vue           # 设置（数据导出 + 登出）
│   └── snake/index.vue              # 贪吃蛇彩蛋（保留不动）
│
├── components/
│   ├── SSEHandler.vue               # ★ SSE 全局事件分发（隐藏组件）
│   ├── BudgetAlert.vue              # ★ 预算告警弹窗（黄/红两级）
│   ├── BillCard.vue                 # 账单卡片
│   ├── FabBtn.vue                   # 浮动按钮（跳转改为 AI 记账页）
│   └── charts/
│       ├── TrendLine.vue            # ★ ECharts 趋势折线图
│       ├── CategoryPie.vue          # ★ ECharts 分类饼图
│       └── BudgetGauge.vue          # ★ ECharts 预算仪表盘
│
├── stores/                          # Pinia（替代旧 store.ts）
│   ├── user.ts                      # 登录态 + JWT
│   ├── ledger.ts                    # 当前账本 + 多账本
│   ├── bill.ts                      # 账单 CRUD
│   ├── budget.ts                    # 预算 + 实时告警
│   └── sse.ts                       # SSE 连接 + 事件分发
│
├── api/                             # HTTP 请求层
│   ├── client.ts                    # Axios 封装 + JWT 拦截
│   ├── auth.ts, bills.ts, ledgers.ts, budgets.ts, stats.ts, insights.ts
│
├── styles/
│   ├── atoms.css                    # 原子化 CSS（flex/grid/spacing/color）
│   ├── tokens.css                   # 设计 Token（色板/间距/圆角/阴影）
│   └── theme.css                    # 深色/浅色主题
│
├── utils/
│   ├── sse.ts                       # SSE 客户端（自动重连）
│   └── format.ts                    # 金额/日期格式化
│
└── types/
    └── index.ts                     # 全局 TypeScript 类型定义
```

### 6.2 Pinia Store 设计（5 个）

| Store | 核心状态 | 关键 Action |
|-------|---------|------------|
| `user` | token, user | login(), logout(), fetchUser() |
| `ledger` | ledgers[], currentId, current | fetch(), switchLedger(), create(), join() |
| `bill` | bills[], total, loading | fetch(), prepend() |
| `budget` | statuses[], alertVisible, alertData | fetch(), save(), showAlert(), dismissAlert() |
| `sse` | connection state | connect(), handleEvent(), disconnect() |

### 6.3 SSE 事件分发架构

```
SSEHandler.vue (App.vue 中挂载，全局唯一)
    │
    │  GET /api/v1/sse/subscribe (JWT 认证)
    │
    ├── event: "warning" | "blocked"
    │   → budgetStore.showAlert(data)
    │   → uni.showModal({ 全屏告警 })
    │
    ├── event: "insight_ready"
    │   → uni.showTabBarRedDot({ index: insights tab })
    │
    ├── event: "clarify"
    │   → 若在 transcribe 页 → 直接展示反问
    │   → 否则 → uni.showToast 提示
    │
    └── event: "completed"
        → billStore.prependBill(data.bill)
        → uni.showToast("记账成功 ✓")
```

### 6.4 AI 记账页 UI 结构

```
┌─────────────────────────────────┐
│  💬 AI 智能记账                   │
├─────────────────────────────────┤
│  ┌─────────────────────────┐    │
│  │ 说说你今天花了什么？       │    │
│  │ 午饭和同事吃湘菜花了68块   │    │
│  │ [🎤 语音]  [📋 解析]     │    │
│  └─────────────────────────┘    │
│                                 │
│  ┌─ AI 解析结果 ───────────┐   │
│  │ ✅ 支出  ¥68.00          │   │
│  │ ✅ 餐饮美食·中餐          │   │
│  │ ✅ 微信支付  今天         │   │
│  │ [✏️ 修改] [✓ 确认记账]   │   │
│  └─────────────────────────┘   │
│                                 │
│  ⚠️ 预算告警 (如有)             │
│  ┌─────────────────────────┐   │
│  │ 🔴 本月餐饮已用 95%      │   │
│  │ 已花 ¥2,850 / ¥3,000    │   │
│  │ [仍然记账]  [取消]       │   │
│  └─────────────────────────┘   │
└─────────────────────────────────┘
```

---

## 7. 后端项目结构

```
backend/
├── pyproject.toml                  # 依赖管理
├── Dockerfile                      # 微信云托管容器
├── .env.example
├── alembic.ini                     # 数据库迁移
├── alembic/
│   └── versions/
│
├── app/
│   ├── main.py                     # FastAPI 应用工厂（lifespan 事件）
│   ├── config.py                   # Pydantic Settings（环境变量）
│   │
│   ├── api/
│   │   ├── deps.py                 # 依赖注入（get_db, get_redis, get_current_user）
│   │   └── v1/
│   │       ├── router.py           # 聚合路由
│   │       ├── auth.py             # 微信登录
│   │       ├── bills.py            # 账单 CRUD + Transcribe (SSE)
│   │       ├── ledgers.py          # 账本管理
│   │       ├── budgets.py          # 预算管理
│   │       ├── stats.py            # 统计查询
│   │       ├── insights.py         # 洞察报告
│   │       └── sse.py              # SSE 订阅端点
│   │
│   ├── agents/                     # ★ LangGraph Agent 核心
│   │   ├── graph.py                # StateGraph 定义 + 条件边 + Checkpointer
│   │   ├── state.py                # TransactionState TypedDict
│   │   ├── parser.py               # Parser Node（DeepSeek-V3 Function Calling）
│   │   ├── guardian.py             # Guardian Node（Redis 预算检查）
│   │   ├── social.py               # Social Ledger Node（债务抵消算法）
│   │   ├── oracle.py               # Oracle Node（异步洞察触发）
│   │   └── tools.py                # Pydantic Tool 定义
│   │
│   ├── core/
│   │   ├── database.py             # SQLAlchemy async engine + session
│   │   ├── redis.py                # Redis 连接池 + 预算计数器 + 分布式锁
│   │   ├── security.py             # JWT + 微信 code→openid
│   │   └── llm.py                  # LLM Provider 工厂（DeepSeek / Qwen）
│   │
│   ├── models/                     # SQLAlchemy ORM
│   │   ├── base.py                 # Declarative Base
│   │   ├── user.py, ledger.py, bill.py, budget.py, insight.py
│   │
│   ├── schemas/                    # Pydantic v2 Request/Response
│   │   ├── auth.py, bill.py, ledger.py, budget.py, stats.py, insight.py
│   │
│   ├── services/                   # 业务逻辑层
│   │   ├── bill_service.py         # 账单创建 + 预算联动
│   │   ├── budget_service.py       # 预算设置 + Redis 同步
│   │   ├── ledger_service.py       # 账本 + 成员管理
│   │   └── insight_service.py      # 洞察生成 + 触发调度
│   │
│   └── rag/                        # RAG 知识库
│       ├── chroma_store.py         # ChromaDB Collection 管理
│       ├── embeddings.py           # 嵌入模型封装
│       ├── retriever.py            # 语义检索接口
│       └── seed_data/
│           └── finance_tips.jsonl  # 理财知识种子数据
│
└── tests/
    ├── conftest.py                 # Fixtures（test DB, mock LLM）
    ├── test_parser.py              # Parser Node 单元测试
    ├── test_guardian.py            # Guardian Node 单元测试
    ├── test_social.py              # 债务抵消算法测试
    ├── test_graph.py               # StateGraph 路由测试
    └── test_api/
        ├── test_auth.py
        ├── test_bills.py
        └── test_transcribe.py
```

---

## 8. LangGraph 代码契约

### 8.1 正确用法

```python
# ✅ StateGraph 构建
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

builder = StateGraph(TransactionState)
builder.add_node("parser", parser_node)
builder.add_node("guardian", guardian_node)
builder.add_node("social_ledger", social_node)
builder.add_node("oracle", oracle_node)

builder.set_entry_point("parser")

builder.add_conditional_edges("parser", route_after_parser, {
    "guardian": "guardian",
    END: END
})

builder.add_conditional_edges("guardian", route_after_guardian, {
    "social_ledger": "social_ledger",
    "oracle": "oracle",
    END: END
})

builder.add_edge("social_ledger", "oracle")
builder.add_edge("oracle", END)

graph = builder.compile(
    checkpointer=MemorySaver(),
    interrupt_before=["guardian"],  # Parser 完成后中断，等用户确认
)
```

### 8.2 LLM 调用模式

```python
# ✅ 直接使用底层 SDK
from openai import AsyncOpenAI

class LLMClient:
    def __init__(self, provider: Literal["deepseek", "qwen"]):
        cfg = self.PROVIDERS[provider]
        self.client = AsyncOpenAI(base_url=cfg["base_url"], api_key=cfg["api_key"])
        self.model = cfg["model"]

    async def call_with_tools(self, messages, tools) -> dict | None:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
        )
        if response.choices[0].message.tool_calls:
            return json.loads(response.choices[0].message.tool_calls[0].function.arguments)
        return None

    @staticmethod
    def pydantic_to_openai_tool(model_cls, name, description) -> dict:
        """Pydantic v2 → OpenAI Function Calling tool format"""
        return {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": model_cls.model_json_schema(),
            }
        }
```

### 8.3 禁止用法

```python
# ❌ 严禁
from langchain.agents import AgentExecutor
from langchain.chains import LLMChain
from langchain.chains import RetrievalQA
chain.run(input)  # 任何黑盒 Chain 调用
```

---

## 9. 核心算法：最优债务抵消

### 9.1 问题定义

**输入**：共享账本中 N 个成员之间的债权债务净额
**输出**：最小化转账指令集

**示例**：
- A 代付午餐 ¥120（3 人 AA，每人 ¥40）→ A 应收 ¥80
- B 代付电影票 ¥90（3 人 AA，每人 ¥30）→ B 应收 ¥60
- C 代付打车 ¥30（3 人 AA，每人 ¥10）→ C 应收 ¥20

**净额**：A:+80, B:+60, C:+20, D:-50, E:-50, F:-60
**最优结算**：D→A:50, E→A:30, E→B:20, F→B:40, F→C:20（5 笔）

### 9.2 贪心算法实现

```python
def minimize_debts(
    balances: dict[int, float],       # {user_id: net} 正=应收 负=应付
    member_names: dict[int, str],
) -> list[Settlement]:
    """O(n²) 贪心匹配，n = 成员数（通常 < 20）"""
    creditors = [(uid, amt) for uid, amt in balances.items() if amt > 0.01]
    debtors = [(uid, -amt) for uid, amt in balances.items() if amt < -0.01]
    creditors.sort(key=lambda x: -x[1])  # 最大债权人优先
    debtors.sort(key=lambda x: -x[1])    # 最大债务人优先

    settlements = []
    i = j = 0
    while i < len(debtors) and j < len(creditors):
        debtor_id, debt = debtors[i]
        creditor_id, credit = creditors[j]
        amount = min(debt, credit)

        if amount > 0.01:
            settlements.append(Settlement(
                from_user_id=debtor_id,
                from_user_name=member_names[debtor_id],
                to_user_id=creditor_id,
                to_user_name=member_names[creditor_id],
                amount=round(amount, 2),
            ))

        debtors[i] = (debtor_id, debt - amount)
        creditors[j] = (creditor_id, credit - amount)

        if debtors[i][1] < 0.01: i += 1
        if creditors[j][1] < 0.01: j += 1

    return settlements
```

### 9.3 增量计算

每次新账单写入时，仅更新涉及的债权关系（而非全量重算），通过 `bill_shares` 表增量维护成员净额，在用户主动请求结算时执行贪心匹配。

---

## 10. RAG 知识库设计

### 10.1 架构

```
┌───────────────────────────────────────┐
│            Oracle Node                 │
│                                        │
│  ┌──────────┐    ┌──────────┐         │
│  │ MySQL     │    │ ChromaDB │         │
│  │ 近3个月   │───▶│ 语义检索  │         │
│  │ 消费记录   │    │ Top-K    │         │
│  └──────────┘    └────┬─────┘         │
│                       │                │
│                       ▼                │
│  ┌────────────────────────────┐       │
│  │ Prompt 组装                 │       │
│  │ System: 理财顾问角色        │       │
│  │ Context: 检索到的理财知识    │       │
│  │ User: 消费数据摘要 + 趋势   │       │
│  └────────────┬───────────────┘       │
│               │                        │
│               ▼                        │
│  ┌────────────────────┐               │
│  │ Qwen-Max 深度推理   │               │
│  │ → 个性化省钱策略     │               │
│  └────────┬───────────┘               │
│           │                            │
│           ▼                            │
│  MySQL insights 表 + SSE 推送          │
└───────────────────────────────────────┘
```

### 10.2 种子数据示例

```jsonl
{"category":"餐饮","content":"控制外卖频率可将餐饮支出降低30-50%。建议每周在家做饭3-4次，批量采购食材更省钱。"}
{"category":"交通","content":"通勤优化：地铁月票比单程票节省约40%，短途出行考虑共享单车替代打车。"}
{"category":"购物","content":"大额消费前执行'48小时冷静期'规则，可以避免60%以上的冲动消费。"}
{"category":"居住","content":"租房支出不应超过月收入的30%，否则会影响长期储蓄率。"}
{"category":"储蓄","content":"50/30/20 预算法则：50%必要支出、30%可选消费、20%强制储蓄和投资。"}
{"category":"信用卡","content":"信用卡免息期平均45-56天，合理利用免息期可增加流动资金收益。"}
{"category":"保险","content":"保费支出控制在年收入5-10%以内，优先配置医疗险和意外险。"}
```

---

## 11. 关键决策记录

| # | 决策项 | 选择方案 | 理由 |
|---|--------|---------|------|
| 1 | 分阶段策略 | 大爆炸式重构 | 用户明确选择，架构干净无历史包袱 |
| 2 | 部署方案 | 微信云托管 CloudBase Run | 与微信生态无缝集成、免备案 HTTPS、原生支持 SSE 长连接 |
| 3 | LLM 策略 | DeepSeek-V3（Parser/Guardian）+ Qwen-Max（Oracle） | 按场景选最优模型：高频快速用 DeepSeek，深度推理用 Qwen |
| 4 | 向量数据库 | ChromaDB 嵌入模式 | 知识库规模小（千级），零运维零成本，未来可迁移到云服务 |
| 5 | 状态管理 | Pinia（5 个 Store） | Vue 3 官方推荐，TypeScript 原生支持，替代旧的直接函数调用 |
| 6 | 图表方案 | ECharts 替换手写 Canvas | 更丰富的图表类型、更好的微信小程序兼容性、更少的维护代码 |
| 7 | UI 方案 | 自建原子化 CSS + 设计 Token | 实现"极致科技感 UI"要求，轻量不依赖 Tailwind |
| 8 | 并发控制 | Redis 分布式锁（Lua 脚本安全释放） | Redlock 简化版，5 秒超时，适合小程序场景 |
| 9 | 预算流控 | Redis INCRBYFLOAT + TTL | 原子操作，无需事务，天然适配按月过期 |
| 10 | HITL 上限 | 最多反问 3 轮 | 防止无限循环，超限降级为传统表单 |

---

## 12. 验证方案

### 12.1 后端测试

| 测试层 | 工具 | 覆盖范围 |
|--------|------|---------|
| 单元测试 | pytest + pytest-asyncio | 每个 Agent Node（Mock LLM） |
| 算法测试 | pytest | 债务抵消算法（多场景） |
| 路由测试 | pytest | StateGraph 条件边路由 |
| API 测试 | httpx + pytest | 全部 REST 端点 |
| SSE 测试 | httpx async streaming | Transcribe 事件流 |

### 12.2 前端测试

| 测试层 | 工具 | 覆盖范围 |
|--------|------|---------|
| Store 测试 | Vitest | 每个 Pinia Store action/getter |
| 组件测试 | @vue/test-utils + happy-dom | SSEHandler, BudgetAlert, BillCard |
| API Mock | vitest mock | 模拟后端响应和 SSE 事件 |

### 12.3 端到端验证路径

1. `POST /auth/login` → 获取 JWT
2. `POST /ledgers` → 创建个人账本
3. `POST /bills/transcribe {text: "午饭68块"}` → 验证 Parser 解析 + 正常落库
4. `PUT /budgets {category_budgets: {"餐饮美食": 3000}}` → 设置预算
5. 连续记账直到触发 Guardian warning → 验证 SSE 告警推送
6. `POST /ledgers {type: "shared"}` → 创建共享账本
7. 多用户加入 → 记账 → `POST /ledgers/{id}/settle` → 验证最优债务抵消
8. `POST /insights/generate` → 验证 RAG + Oracle 报告生成
9. 前端 `npm run build:h5` + `npm run build:mp-weixin` → 验证跨平台构建

---

> **文档结束**
>
> 配套文件：
> - 实施计划：`docs/superpowers/plans/2026-07-14-rongxiaozhang-rebuild-plan.md`
> - SDD 进度：`.superpowers/sdd/progress.md`

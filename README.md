# 荣小账 v2.0

> 个人记账 · AI 智能记账 · 多人协同

荣小账是一款**能"说话记账"的个人记账应用**，支持微信小程序、H5 网页等多端运行。基于 LangGraph 多智能体系统，实现自然语言记账、预算实时风控、共享账本协同与 AI 消费洞察。

> AI 是可选能力。服务器设置 `AI_FEATURES_ENABLED=false` 后，小程序会隐藏 AI 记账、AI 消费洞察及洞察入口，只保留手动记账、账单、预算、统计、共享账本等核心功能。

![logo](images/logo.jpg)

---

## ✨ 功能亮点

| 功能 | 说明 |
|------|------|
| 🗣️ **AI 智能记账（可关闭）** | 输入「午饭湘菜花了68块」这类日常用语，AI 自动解析金额、分类、账户、日期，并生成待确认账单；一句话说多笔（如「5块包子，10块面」）会拆成多张待确认卡 |
| 🎤 **语音记账（可关闭）** | 按住说话，语音自动转文字并解析入账（H5 端） |
| 📥 **Excel 导入** | 支持从 Excel 批量导入账单，导入前预览和校验 |
| 💬 **对话式澄清** | 信息缺失时，AI 主动反问补充（如"这笔是支出还是收入？"），确认后才入账 |
| 🚨 **预算实时风控** | 消费落库前实时检查预算，超支时黄色告警、严重超支时红色拦截 |
| 👥 **共享账本 / AA 结算** | 多人共用一个账本（室友、情侣、团建），支持分摊、最优债务抵消算法结算 |
| 🔍 **AI 消费洞察（可关闭）** | 定期或按需生成消费分析报告，结合理财知识库给出可执行的省钱建议；关闭 AI 后入口一并隐藏 |
| 💹 **多维度统计** | 月度趋势、分类占比、支出排名等图表（ECharts） |
| 💰 **多账户管理** | 微信、支付宝、银行卡、现金等账户统一管理 |
| 🗂️ **灵活分类** | 预置常用分类（支出 9 类 / 收入 3 类），支持自定义增删改 |
| 📤 **数据导出 / 删号** | 支持按账本导出 CSV/JSON、导出账号数据；删号前检查共享账本所有权和未结算分摊 |
| 🐍 **贪吃蛇彩蛋** | 设置页里藏着一个小游戏 😄 |

---

## 🏗️ 系统架构

五层架构，核心是 **LangGraph 多 Agent 状态机**：

```
┌──────────────────────────────────────────────────────────────┐
│ 表现层  UniApp (Vue 3 + Pinia + TypeScript)                  │
│         微信小程序 / H5 Web（Windows 桌面未验证）              │
├──────────────────────────────────────────────────────────────┤
│ API 网关层  FastAPI + Uvicorn                                 │
│         CORS / JWT 认证 / 请求限流 / SSE 实时推送              │
├──────────────────────────────────────────────────────────────┤
│ Agent 编排层  LangGraph StateGraph  ★ 核心                    │
│   ┌────────┐ ┌────────┐ ┌─────────┐ ┌────────┐               │
│   │Parser  │ │Guardian│ │  Social │ │ Oracle │               │
│   │记账解析 │ │预算守卫 │ │ 协同记账 │ │ 消费分析 │              │
│   └───┬────┘ └───┬────┘ └────┬────┘ └───┬────┘               │
│       │澄清      │SSE告警     │Redis锁    │RAG检索             │
│   Orchestrator 调度 · Advisor 理财顾问 · Guardian 复核        │
├──────────────────────────────────────────────────────────────┤
│ 数据与服务层                                                   │
│   MySQL 8.0（用户/账本/账单/预算/分类/账户/洞察等）            │
│   Redis 7.0（缓存/限流/锁）· ChromaDB（向量库）                 │
└──────────────────────────────────────────────────────────────┘
```

### 🤖 六个 AI 智能体协作

一条"一句话记账"请求会经过多个智能体协作处理：

```
用户输入 ──▶ Orchestrator 调度员 ──▶ Parser 记账解析员
                                        │ 解析成功
                                        ▼
                                   Guardian 预算守卫 ──风险高──▶ Advisor 理财顾问
                                        │ 通过                  │
                                        ▼                       ▼
                              Social 协同记账（共享账本）     Guardian 复核
                                        │                       │
                                        ▼                       ▼
                                   Oracle 消费分析师 ──▶ 最终确认入账
```

| 智能体 | 职责 |
|--------|------|
| **Orchestrator** 调度员 | 识别用户意图（记账 / 咨询 / 分析），路由到合适的处理流程 |
| **Parser** 记账解析员 | 自然语言 + LLM 抽取结构化账单；信息不全时反问澄清（HITL） |
| **Guardian** 预算守卫 | 入账前实时风控，超支告警 / 拦截，二次复核 |
| **Advisor** 理财顾问 | 针对预算风险、消费习惯给出个性化建议 |
| **Social** 协同记账 | 共享账本并发写入保护（Redis 分布式锁）、AA 分摊、最优债务抵消 |
| **Oracle** 消费分析师 | 统计 + RAG 知识库 + LLM 深度推理，生成周报 / 月报 / 按需洞察 |

> 技术红线：AI 编排仅使用 `langgraph` + `langchain-core`，严禁使用 `AgentExecutor` / `LLMChain` / `RetrievalQA` 等旧式链。

---

## 🛠️ 技术栈

### 前端

| 技术 | 用途 |
|------|------|
| uni-app 3.0（Vue 3 + TypeScript + Pinia） | 跨平台框架，一套代码多端运行 |
| uView Plus | UI 组件库 |
| ECharts（按需引入） | 数据可视化图表 |
| 原子化 CSS（tokens / theme / atoms） | 统一设计令牌与主题 |
| Vite | 构建工具 |
| Vitest | 单元测试 |

### 后端

| 技术 | 用途 |
|------|------|
| Python 3.10+ / FastAPI / Pydantic v2 | 异步 REST API 框架 |
| LangGraph（StateGraph + MemorySaver） | 多智能体状态机编排 |
| SQLAlchemy 2.0 (asyncio) / Alembic | ORM 与数据库迁移 |
| MySQL 8.0 | 业务数据（用户、账本、账单、预算、分类、账户、洞察等） |
| Redis 7.0 | 限流、预算计数器、分布式锁、SSE |
| ChromaDB + sentence-transformers | 理财知识库向量检索（RAG） |
| DeepSeek-V4.1-Flash（`deepseek-flash`） | 默认 LLM；AI 记账解析与消费洞察统一走 DeepSeek |
| Qwen-Plus（可选） | 仅作为可选兜底；不配置 `QWEN_API_KEY` 时不启用 |
| SSE（sse-starlette） | 流式推送 AI 处理过程 |
| Docker | 可选容器化部署；生产当前使用 Nginx + systemd + Uvicorn |
| Nginx + systemd | HTTPS 反向代理、进程守护与开机自启 |

---

## 📁 项目结构

```
.
├── src/                          # 前端源码（uni-app）
│   ├── api/                      # 后端接口封装（auth/bills/ledgers/…）
│   ├── components/               # 通用组件（图表、预算告警、SSE 处理器…）
│   ├── pages/                    # 15 个主包页面（首页/记账/账单/统计/洞察/账本…）
│   ├── subpackages/import/       # Excel 导入分包页面
│   ├── stores/                   # Pinia 状态管理（user/ledger/bill/…）
│   ├── styles/                   # 原子化 CSS 设计系统
│   ├── utils/                    # 工具（SSE / 语音 / CSV 导出 / 本地存储）
│   ├── types/                    # TypeScript 类型定义
│   ├── pages.json                # 页面与 tabBar 配置
│   ├── manifest.json             # 应用配置（多端 appid 等）
│   └── main.ts                   # 应用入口
│
├── backend/                      # 后端服务（FastAPI）
│   ├── app/
│   │   ├── agents/               # 多智能体（orchestrator/parser/guardian/…）
│   │   ├── api/v1/               # REST 路由（auth/bills/insights/sse/…）
│   │   ├── core/                 # 基础设施（数据库/Redis/LLM/安全/限流）
│   │   ├── models/               # SQLAlchemy 数据模型
│   │   ├── rag/                  # ChromaDB 知识库检索
│   │   ├── schemas/              # Pydantic 校验模型
│   │   ├── services/             # 业务逻辑服务
│   │   ├── workers/              # 异步任务（消费洞察生成）
│   │   └── main.py               # 应用入口
│   ├── alembic/                  # 数据库迁移脚本
│   ├── tests/                    # 后端测试
│   ├── Dockerfile                # 容器化部署配置
│   └── pyproject.toml            # 依赖与项目元数据
│
├── docs/superpowers/             # 设计文档（PRD / 技术规格 / 实施计划）
├── docs/releases/                # 发布说明与变更记录
├── loadtest/                     # 压测与 RAG 召回评测脚本
├── images/                       # Logo 等静态资源
└── package.json                  # 前端依赖与脚本
```

---

## 🚀 快速开始

### 环境要求

- **前端**：Node.js ≥ 18
- **后端**：Python ≥ 3.10（推荐 3.11）、MySQL 8.0、Redis 7.0

### 1. 启动前端

```bash
# 安装依赖
npm install

# 启动 H5 开发服务器
npm run dev:h5

# 或启动微信小程序（需配合微信开发者工具）
npm run dev:mp-weixin
```

前端默认通过 `VITE_API_BASE_URL` 连接后端，开发环境已配置指向 `http://127.0.0.1:8000/api/v1`（见 `.env.development.local`）。

### 2. 启动后端

```bash
cd backend

# 创建/进入虚拟环境（不要用系统 pip）
python3 -m venv venv
source venv/bin/activate

# 安装依赖
python -m pip install -e ".[dev]"

# 准备环境变量（复制示例并填写密钥）
cp .env.example .env

# 启动开发服务器
uvicorn app.main:app --reload --port 8000
```

后端启动后自动初始化数据库表，并拉起 AI 会话清理与消费洞察两个后台任务。访问 `http://127.0.0.1:8000/docs` 可查看自动生成的 API 文档（Swagger UI）。

### 3. 数据库迁移（可选）

```bash
cd backend
alembic revision --autogenerate -m "描述本次变更"   # 生成迁移
alembic upgrade head                                 # 应用迁移
```

---

## ⚙️ 环境变量配置

### 前端（`.env.development.local`）

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `VITE_API_BASE_URL` | 后端 API 地址 | `https://api.rongxiaozhang.cn/api/v1` |

### 后端（`backend/.env`）

| 变量 | 说明 |
|------|------|
| `DATABASE_URL` | MySQL 连接串（`mysql+asyncmy://…`） |
| `REDIS_URL` | Redis 连接串 |
| `JWT_SECRET` | JWT 签名密钥（≥32 位随机字符） |
| `WECHAT_APPID` / `WECHAT_SECRET` | 微信小程序凭据 |
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥 |
| `DEEPSEEK_MODEL` | 默认 `deepseek-flash`（DeepSeek-V4.1-Flash 的 API ID） |
| `QWEN_API_KEY` | 可选 Qwen 兜底；留空则完全不调用 Qwen |
| `CHROMA_PERSIST_DIR` | ChromaDB 持久化目录 |
| `EMBEDDING_MODEL` | 中文向量模型（默认 `BAAI/bge-small-zh-v1.5`） |
| `INSIGHT_WORKER_ENABLED` | 是否启用消费洞察后台任务 |
| `AI_FEATURES_ENABLED` | AI 总开关；`false` 时关闭 AI 记账/洞察并隐藏前端 AI 入口 |
| `ENABLE_DEV_LOGIN` | 开发环境是否启用免密登录（调试用） |
| `ENVIRONMENT` | `development` / `test` / `production` |
| `DEBUG` | 生产必须为 `false` |
| `CORS_ORIGINS` | 允许跨域来源；生产不要使用 `*` |
| 各类 `*_LIMIT_*` | 登录 / AI 记账 / AI 洞察的限流阈值 |

完整变量清单见 [`backend/.env.example`](backend/.env.example)。

### AI 功能开关

```env
# 关闭全部 AI 能力（推荐审核期或不需要 AI 时）
AI_FEATURES_ENABLED=false
```

生效方式：

1. 修改服务器 `backend/.env`；
2. `systemctl restart rongxiaozhang-api.service`；
3. 验证 `GET /api/v1/config` 返回 `{"ai_enabled": false}`。

关闭后：

- 前端隐藏 AI 记账、AI 消费洞察、首页洞察入口；
- 后端拒绝 AI 转写/洞察请求；
- 手动记账、账单、预算、统计、共享账本不受影响。

> 这是启动时读取的开关，改完必须重启后端，不能热更新。

### 服务器一键开关（可选）

把 [scripts/rxz-ai](scripts/rxz-ai) 安装到服务器 `/usr/local/bin/rxz-ai` 并赋执行权限后：

```bash
sudo rxz-ai on     # 打开 AI
sudo rxz-ai off    # 关闭 AI
```

脚本会自动备份 `.env`、修改 `AI_FEATURES_ENABLED`、重启 `rongxiaozhang-api.service`，并输出 `/health` 与 `/config`。

---

## 🧪 测试

```bash
# 前端单元测试
npm run test

# 微信小程序专项测试
npm run test:mp

# 后端测试
cd backend && pytest

# 前端类型检查
npm run type-check
```

后端回归测试覆盖账本锁、confirm 幂等、成员/删号保护、导出、预算、Parser failover；前端覆盖预算弹窗、请求竞态、AI 开关、SSE 解码、共享账本页面等。

---

## 📦 打包发布

```bash
# 打包微信小程序（产物在 dist/build/mp-weixin，用微信开发者工具导入）
npm run build:mp-weixin

# 打包 H5 网页
npm run build:h5

# 后端容器镜像
cd backend
docker build -t rongxiaozhang-backend .
docker run -p 8080:8080 --env-file .env rongxiaozhang-backend
```

当前生产部署：

```text
微信小程序 → HTTPS 443 → Nginx → 127.0.0.1:8000 Uvicorn
                                      ├─ MySQL 8.0
                                      └─ Redis
```

- 后端由 `rongxiaozhang-api.service`（systemd）托管；
- 生产虚拟环境是 `backend/venv`，安装依赖必须使用 `venv/bin/python`；
- Nginx 负责 SSL、反向代理和 SSE 转发；
- 服务器为腾讯云 Ubuntu；
- 生产不要使用 `--reload`，首次部署后确认 `ENVIRONMENT=production`、`DEBUG=false`、`ENABLE_DEV_LOGIN=false`。

### 发布顺序

```text
备份数据库 → 更新后端代码 → 安装依赖 → alembic upgrade head
→ 修改/确认 .env → 重启后端 → 健康检查
→ 构建小程序 → 上传体验版 → 验证 → 提交审核 → 发布
```

### 回滚

- 后端：恢复上一版代码/镜像，重启 systemd 服务；
- 数据库：使用发布前备份；
- 小程序：在微信后台保留上一版线上版本，必要时回退。

---

## 📚 设计文档

| 文档 | 说明 |
|------|------|
| [产品需求文档（PRD）](docs/superpowers/specs/2026-07-14-rongxiaozhang-rebuild-prd.md) | 11 章完整产品需求 |
| [技术规格文档（Spec）](docs/superpowers/specs/2026-07-14-rongxiaozhang-rebuild-design.md) | 12 章系统设计、架构与代码契约 |
| [实施计划](docs/superpowers/plans/2026-07-14-rongxiaozhang-rebuild-plan.md) | 18 任务 6 阶段实施路线 |
| [多智能体优化方案](docs/superpowers/plans/2026-07-23-multi-agent-optimization.md) | 智能体协作性能优化 |

---

## 🗓️ 最近更新

### 2026-10-30

- 增加 `AI_FEATURES_ENABLED` 总开关，关闭后隐藏前端全部 AI 入口；
- 修复预算弹窗 resolver 被 SSE 覆盖、账单分页竞态、预算页错误态；
- confirm 改为单锁，补幂等检查、锁 TTL 续期与锁丢失保护；
- 移除未结算成员/未结算分摊删号，增加共享账本所有者删号保护；
- 导出增加 10,000 条上限、`truncated` 标记和限流；
- 修复小程序无 `TextDecoder` 时 SSE 中文跨分片乱码；
- 补充账本锁、删号、导出、Parser、前端竞态等回归测试。

详见 [2026-10-30 发布说明](docs/releases/2026-10-30-ai-off.md)。

## 📝 项目信息

- **微信小程序 AppID**：`wx790e9576e610670e`
- **生产 API 域名**：`https://api.rongxiaozhang.cn`
- **版本**：v2.0.0
- **协议**：保留所有权利

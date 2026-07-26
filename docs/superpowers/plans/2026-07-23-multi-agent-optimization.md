# 荣小账 — 多Agent系统优化计划

## Context

当前荣小账v2.0后端的 `backend/app/agents/` 实现了4节点的LangGraph流水线，但只有Parser节点真正调用了LLM，其余3个节点（Guardian/Social/Oracle）是纯代码逻辑（数学计算、贪心算法、布尔赋值），并非真正的AI Agent。用户要求将其升级为"实实在在的多Agent协作系统"。

## 设计决策

| 决策项 | 选定方案 |
|--------|---------|
| 目标 | 多Agent协作推理 — 4个独立AI Agent各司其职、互相协作 |
| Agent角色 | Parser + Guardian + Advisor + Orchestrator（全部4个） |
| 技术方案 | 优化现有LangGraph（方案A，风险最低） |
| 协作模式 | 智能流水线（顺序执行，每个环节AI判断；复杂场景支持辩论） |

## 架构改造

### 改造前
```
parser(LLM) → guardian(数学计算) → social(算法) → oracle(布尔赋值) → END
```

### 改造后
```
Orchestrator(意图识别+调度)
    ├── 快速通道(简单记账) → Parser → 确认
    ├── 标准流程(日常记账) → Parser → Guardian → 确认
    └── 深度分析(预算冲突/大额) → Parser → Guardian ⇄ Advisor(辩论) → 综合建议
```

## Agent角色设计

### Parser（智能记账员）
- 人格：细心严谨的会计，善于从口语中提取关键信息
- 能力：自然语言理解、智能追问、上下文记忆（用户偏好）
- 工具：分类查询、历史账单检索

### Guardian（预算卫士）
- 人格：严谨但不死板的预算管家，评估消费合理性而不仅看数字
- 能力：智能预算分析、分级响应（安全/提醒/拦截）、跨分类调配建议
- 工具：预算查询、消费历史查询、分类余额查询

### Advisor（理财顾问）— 全新
- 人格：温和但有洞察力的财务顾问
- 能力：异常检测、省钱建议、趋势预测
- 触发时机：用户主动咨询、Guardian检测异常时、定期回顾

### Orchestrator（调度者）— 全新
- 人格：冷静的团队协调者
- 能力：意图识别、Agent调度、结果汇总、超时降级

## 文件变更清单

### 新建文件
- `backend/app/agents/base.py` — Agent基类（统一LLM调用、工具管理、错误重试、降级处理）
- `backend/app/agents/advisor.py` — Advisor Agent
- `backend/app/agents/orchestrator.py` — Orchestrator Agent

### 改造文件
- `backend/app/agents/parser.py` — 升级为ParserAgent类，增加上下文记忆、智能追问
- `backend/app/agents/guardian.py` — 从数学计算升级为LLM Agent
- `backend/app/agents/graph.py` — 新条件路由、Agent间消息传递、辩论机制
- `backend/app/agents/state.py` — 增加Agent消息历史、上下文记忆字段
- `backend/app/agents/tools.py` — 整合各Agent共享工具

### 顺便修复
- `backend/app/api/v1/accounts.py` — 删除重复 `_require_access`，改用 `deps.py`
- `backend/app/api/v1/stats.py` — 同上
- `backend/app/api/v1/categories.py` — 同上
- `backend/app/api/v1/budgets.py` — 同上
- `backend/app/api/deps.py` — 新增统一 `require_ledger_access` 依赖

## 验证方式

1. **运行现有后端测试**（确保不破坏已有功能）：
   ```bash
   cd backend && python -m pytest tests/ -x
   ```

2. **手动测试Agent协作场景**：
   - 简单记账："午餐30元" → 快速通道
   - 预算冲突："买了新手机5000" → Guardian+Advisor辩论模式
   - 咨询分析："这个月我花多了吗？" → Advisor介入

3. **运行前端测试**（确保前端兼容）：
   ```bash
   npx vitest run
   ```

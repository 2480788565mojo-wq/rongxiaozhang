# Skill Map

## Core Routing

```text
wechat-miniapp-core
   │
   ├── product ─────────────► miniapp-product-thinking
   ├── UI/UX ───────────────► miniapp-ui-system
   ├── UI style/theme ──────► miniapp-ui-style-library
   ├── components ──────────► miniapp-component-system
   ├── API ─────────────────► miniapp-api-system
   ├── auth/security ───────► miniapp-auth-security
   ├── WeChat capabilities ─► miniapp-platform-capabilities
   ├── state/data ──────────► miniapp-state-data
   ├── workflows ───────────► miniapp-business-workflow
   ├── AI ──────────────────► miniapp-ai-assistant
   ├── performance ─────────► miniapp-performance
   ├── debugging ───────────► miniapp-debug
   ├── review ──────────────► miniapp-code-review
   └── release ─────────────► miniapp-testing-release
```

## Selection Rule

不要每次加载全部 Skills。

推荐：

- 1 个主 Skill：通常 `wechat-miniapp-core`。
- 1–3 个专项 Skill：与当前任务直接相关。
- 行业规则：来自可选 extension，不污染 Core。

## Priority

多个规则同时存在时：

1. 用户明确需求。
2. 安全、隐私和平台硬约束。
3. 当前项目真实结构与现有约定。
4. `wechat-miniapp-core`。
5. 与当前任务最直接相关的专项 Skill；视觉任务中 `miniapp-ui-system` 与 `miniapp-ui-style-library` 可组合。
6. 示例和默认偏好。

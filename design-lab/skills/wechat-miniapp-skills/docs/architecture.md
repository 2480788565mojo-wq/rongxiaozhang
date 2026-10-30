# Reference Architecture

这是一份**参考结构**，不是所有项目必须照搬的目录。Agent 应优先遵循现有项目。

```text
miniprogram/
├── app.js / app.ts
├── app.json
├── app.wxss
├── api/
│   ├── auth.ts
│   ├── user.ts
│   ├── catalog.ts
│   └── content.ts
├── components/
│   ├── app-button/
│   ├── app-card/
│   ├── empty-state/
│   └── status-badge/
├── pages/
├── services/
│   ├── auth-service.ts
│   └── workflow-service.ts
├── store/                 # optional
├── utils/
│   ├── request.ts
│   ├── storage.ts
│   ├── validator.ts
│   └── logger.ts
├── constants/
├── models/
└── assets/
```

## Layer Responsibilities

- `pages/`：页面状态、用户交互、视图编排。
- `components/`：可复用 UI 与局部交互。
- `api/`：接口定义和参数/返回约定。
- `services/`：跨接口编排、业务用例、复杂流程。
- `store/`：项目确有跨页面共享状态需求时使用。
- `utils/`：无业务依赖的基础工具。
- `constants/`：枚举、静态常量、集中映射。
- `models/`：必要时做结构定义、转换和适配。

## Architecture Decision Rule

不要为了“架构完整”而强行创建所有目录。小项目可以更简单；大型项目才需要更明确的分层。

判断标准是：能否降低重复、控制依赖方向、让状态和业务真值更清晰。

## UI Layering

UI 能力拆成两层：

- `miniapp-ui-system`：信息架构、页面模式、状态、反馈和可用性。
- `miniapp-ui-style-library`：视觉风格、语义 token 和组件外观。

Style Library 不拥有业务状态，也不应绕过 UI System 的可用性规则。

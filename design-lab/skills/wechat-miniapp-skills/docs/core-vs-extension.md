# Core vs Extension

本仓库的公开 Core 目标是服务**所有微信小程序项目**。

## 什么可以进入 Core

一条规则满足以下多数条件时适合 Core：

- 跨行业通用。
- 对大量小程序项目有稳定价值。
- 不依赖某一行业特有实体。
- 不强迫项目采用某一种业务状态机。
- 能作为工程、产品、UI、安全或平台层规则长期维护。

例如：请求层、登录会话、`setData` 性能、权限降级、页面状态、组件 API、测试发布。

## 什么应该成为 Extension

以下更适合作为扩展：

- 医疗预约的号源/就诊规则。
- 酒店房态和入住流程。
- 出行派单和司机状态。
- 餐饮桌台/后厨业务。
- 保险投保流程。
- 某公司内部审批体系。

这些能力可以依赖 Core，但不能反向让 Core 依赖它们。

## 推荐扩展结构

```text
extensions/
└── example-domain-pack/
    ├── README.md
    └── skills/
        └── example-domain/SKILL.md
```

也可以把扩展发布为独立 GitHub 仓库。

## Dependency Direction

```text
Domain Extension
      ↓ depends on
Core Skills
```

Core Skills **never depend on** domain extensions.

# Usage Guide

## 1. 新页面

启用：

- `wechat-miniapp-core`
- `miniapp-product-thinking`
- `miniapp-ui-system`
- `miniapp-ui-style-library`（需要明确视觉风格时）

页面需要复用组件时再加 `miniapp-component-system`。

```text
新增“我的收藏”页面。先读取当前项目导航栏、列表样式和请求层，再定义 loading / empty / error / normal，最后实现。
```

## 2. UI 风格与主题

启用：

- `miniapp-ui-system`
- `miniapp-ui-style-library`

新项目没有品牌规范时，可从 `wechat-clean`、`minimal-light`、`soft-card`、`editorial`、`tech-blue`、`dark-premium`、`playful-color`、`utility-dense` 中选择一个 base style。

已有项目先读取现有 theme 和基础组件，不要为了应用预设风格擅自全站重做。

```text
为新建的内容详情页选择 editorial 风格。先给出语义 token 和组件规则，再实现 normal / loading / error。
```

## 3. 修改已有页面

明确这是增量任务：

```text
这是 MODIFY_PAGE。保持已有视觉和数据结构，只做满足需求的最小修改，不重构无关代码。
```

## 4. 登录和权限

启用：

- `miniapp-auth-security`
- `miniapp-api-system`

如果涉及定位/相机/扫码，再加 `miniapp-platform-capabilities`。

## 5. 通用业务流程

购买、预约、报名、申请、发布、提交等流程启用：

- `miniapp-business-workflow`
- `miniapp-product-thinking`
- `miniapp-api-system`

先定义状态机和“结果未知”恢复策略，再写提交代码。

## 6. AI 助手

启用：

- `miniapp-ai-assistant`
- `miniapp-api-system`
- `miniapp-auth-security`

如果 AI 会执行有副作用动作，再加 `miniapp-business-workflow`。

## 7. 性能

启用 `miniapp-performance`，先找证据：包体、首屏请求、setData、图片、长列表或重复监听。不要没有测量就大规模重构。

## 8. Bug 修复

启用 `miniapp-debug`。输出：现象、根因、证据、最小修复、回归范围。

## 9. Code Review

启用 `miniapp-code-review`。真实问题按 P0–P3 输出，不为了显得专业制造 finding。

## 10. 发布

启用 `miniapp-testing-release`。涉及定位、相机、WebView、文件等平台能力时必须安排真机验证。

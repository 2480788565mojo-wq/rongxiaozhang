---
name: miniapp-debug
description: 通用微信小程序调试 Skill。用于事件、生命周期、网络、状态、样式、权限、异步竞态、真机差异和平台能力故障定位。
metadata:
  version: "2.0.0"
---

# Mini App Debug

## Philosophy

先收集证据，再改代码。目标是找到最小根因并做最小修复。

## Workflow

1. 写清可复现现象和期望行为。
2. 找真实事件入口、页面、组件、请求或平台 API。
3. 查看最近相关变更。
4. 提出少量最可能根因。
5. 用代码、日志、网络面板、状态或真机表现逐一排除。
6. 修复根因，不只掩盖症状。
7. 做针对性回归。

## Common Faults

### Interaction

检查事件绑定、遮罩、z-index、disabled/loading、冒泡、dataset、handler 名称和组件事件。

### Data / UI

检查 `setData` 路径、异步覆盖、properties observer、条件渲染、列表 key、生命周期刷新。

### Network

检查合法域名、环境 baseURL、会话、参数、HTTP/业务错误、超时、重复请求、接口竞态。

### Platform Capability

检查权限、基础库、真机差异、app/page 配置、用户取消、系统设置、业务域名等。

### Lifecycle

重点识别 onLoad/onShow 重复请求、onUnload 后异步回调、重复 listener/timer、前后台切换状态。

## Logging

日志包含：模块、阶段、requestId/resourceId（脱敏）、错误类别、必要上下文。禁止记录 secret、完整 token 或无必要的个人敏感信息。

## Fix Contract

```text
现象
根因
证据
修复
回归范围
```

## Anti-Patterns

- 未定位就重构。
- 用 `setTimeout` 猜时序。
- catch 后完全吞错。
- 用“多刷新几次”当解决方案。
- 只在开发者工具验证真机相关问题。

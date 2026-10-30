---
name: miniapp-api-system
description: 通用微信小程序 API Skill。用于请求层、接口模块、错误模型、鉴权衔接、重试、幂等、上传下载和可观测性。
metadata:
  version: "2.0.0"
---

# Mini App API System

## Goal

让远程调用集中、可观察、可测试，并让业务页面只处理其真正关心的结果。

## Suggested Layers

```text
pages / components
        ↓
services / use-cases (optional)
        ↓
api modules
        ↓
request / upload / download infrastructure
```

遵循项目现有结构，不为层级而层级。

## Request Infrastructure

统一处理适用项：

- baseURL / environment
- timeout
- headers
- session/token injection
- request / trace id
- response normalization
- auth expiration handoff
- network and HTTP errors
- retry policy
- logging with redaction
- cancellation / deduplication（项目需要时）

## API Naming

使用业务动作，不让页面理解 URL：

- `getUserProfile()`
- `listProducts(params)`
- `createBooking(payload)`
- `submitApplication(payload)`
- `publishContent(payload)`

## Error Model

至少区分：

- network / offline
- timeout
- HTTP error
- business error
- unauthenticated
- unauthorized
- validation
- rate limited
- unavailable

UI 层接收可识别错误类型，不只是一串“请求失败”。

## Retry

- GET/查询等幂等请求可根据场景有限重试。
- 写操作默认不盲目重试。
- 如果服务端支持 idempotency key，可在明确语义下安全恢复。
- 指数退避、最大次数和用户取消要有边界。

## Concurrent Auth & Cancellation

会话恢复使用共享的单次进行任务，其他请求等待其结果；失败后清理等待者，禁止恢复流程递归触发自身。原请求最多按既定策略重放，写操作仍需要幂等契约。页面卸载或搜索条件变化后取消适用的请求，并用请求代次防止晚到结果覆盖新状态；框架项目沿用框架封装。

## Upload & Download

- 文件类型、大小、数量前后端双重校验。
- 显示进度或明确处理中状态。
- 失败支持合理重试，但避免重复创建业务记录。
- 临时文件与持久文件生命周期区分清楚。

## Trust Boundary

服务端必须重新校验所有高价值事实，例如：

- 权限与身份
- 价格/积分/库存/资格
- 业务状态转换
- 支付结果
- 审核与风控条件

客户端提交的是请求，不是可信事实。

## Observability

错误日志优先包含：模块、接口、requestId、错误类别、阶段。敏感字段必须脱敏，禁止记录 token、密码、完整证件号等。

## Anti-Patterns

- 每个页面直接写一套 `wx.request`。
- 页面自己刷新 token。
- 所有错误都统一 toast“请求失败”。
- 写请求遇到超时就无限重试。
- 将服务端密钥或签名私钥放在小程序包中。

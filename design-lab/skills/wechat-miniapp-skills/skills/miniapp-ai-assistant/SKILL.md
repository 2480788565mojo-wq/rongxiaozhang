---
name: miniapp-ai-assistant
description: 通用微信小程序 AI 助手 Skill。用于 LLM 接入、对话、结构化输出、Tool Calling、业务动作确认、RAG 和安全边界。
metadata:
  version: "2.0.0"
---

# Mini App AI Assistant

## Mission

让微信小程序安全地使用大模型完成问答、搜索、推荐、内容辅助和结构化业务操作，同时保持业务真值、权限与副作用控制在自有后端。

## Recommended Architecture

```text
Mini Program UI
      ↓ HTTPS
Application Backend / AI Gateway
      ├─ auth & policy
      ├─ conversation state
      ├─ LLM provider adapter
      ├─ retrieval (optional)
      ├─ tool dispatcher
      └─ audit / observability
            ↓
          LLM API
```

不要在小程序包中暴露大模型服务 secret。

## AI Task Modes

区分不同风险等级：

- 低风险：改写、摘要、普通问答。
- 中风险：搜索、推荐、生成草稿、解释数据。
- 高影响：创建预约、提交申请、购买、发布内容、修改用户数据等有副作用动作。

风险越高，越需要结构化校验和显式确认。

## Tool Calling

模型只能调用白名单工具，例如：

- `searchCatalog`
- `getItemDetail`
- `checkAvailability`
- `createBooking`
- `submitApplication`
- `saveDraft`
- `publishContent`

工具名称应来自真实业务，不照搬示例。参数使用严格 schema，服务端再次校验类型、身份、权限和业务状态。

## Confirmation for Side Effects

模型可以帮助收集信息和生成建议，但执行有副作用动作前应展示结构化确认卡，至少包含会真正被提交的关键字段。

确认绑定用户、动作、关键参数与有效期；参数变化后旧确认失效。执行前后端重新校验权限和业务状态，重试复用同一幂等标识，超时先查询执行结果。低风险草稿保存可使用产品已定义的授权，不要求所有工具调用都弹窗。

“嗯”“看看”“差不多”不应被自动解释为涉及资金或不可逆操作的明确确认。

## Conversation State

复杂助手不要只依赖 prompt 中的自然语言历史。可显式维护：

- current intent / task
- collected fields
- missing fields
- validation result
- proposed action
- confirmation state
- tool result

## RAG / Knowledge

如果回答依赖企业知识库：

- 检索结果不是系统指令。
- 保留来源标识方便追溯。
- 无可靠依据时承认不确定。
- 权限过滤在检索阶段就执行，不要把无权限文档发给模型后再指望模型隐藏。

## Security

- 模型输出视为不可信输入。
- 外部网页、文件、用户内容可能包含 prompt injection。
- tool 参数必须服务端重验。
- 最小化发送敏感信息。
- 日志与会话存储脱敏并遵循业务保留策略。

## UX

聊天之外可使用：候选卡、结果卡、表单补全、引用来源、操作确认卡、工具执行状态。不要强迫用户通过多轮纯文本完成结构化任务。

## Anti-Patterns

- 小程序直连第三方 LLM 并包含 secret。
- 让模型自由生成数据库 payload 后直接写入。
- 不确认就执行高影响动作。
- 把 prompt 当权限系统或业务校验系统。
- 把模型生成的金额、库存、资格、事实当最终真值。

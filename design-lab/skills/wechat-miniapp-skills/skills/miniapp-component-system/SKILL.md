---
name: miniapp-component-system
description: 通用微信小程序组件设计 Skill。用于组件边界、properties、events、slots、受控状态、复用和组件文档。
metadata:
  version: "2.0.0"
---

# Mini App Component System

## When to Extract

满足以下任一条件可考虑组件化：

- 多处复用。
- 拥有独立交互或局部状态。
- 业务语义稳定。
- 需要独立测试或独立演化。
- 页面主体过长且存在清晰边界。

不要把每个 `view` 都拆成组件。

## API Design

组件对外契约保持小而清晰：

- `properties`：外部输入。
- internal data：真正属于组件的瞬时状态。
- `triggerEvent`：向上报告事件。
- `slot`：内容扩展点。
- methods：仅在确有 imperative API 需求时暴露。

避免组件偷偷修改父页面数据或读取父页面内部实现。

## Naming

优先语义：

- `user-card`
- `product-item`
- `filter-bar`
- `status-badge`
- `empty-state`
- `bottom-action-bar`

避免 `box2`、`common-item-new`、`my-card-final`。

## Event Semantics

事件描述“发生了什么”：

- `select`
- `change`
- `confirm`
- `cancel`
- `retry`
- `remove`

detail 只携带父级需要的数据，不把整个内部 state 暴露出去。

## Controlled vs Internal State

如果状态会影响业务真值或需要被页面持久化，通常由父级持有；组件只接收值并抛出变更事件。

适合内部持有的状态包括：展开/收起、短暂 hover/pressed、内部动画阶段等。

## Generic vs Business Components

可复用基础组件追求稳定 API；业务组件允许带业务语义。不要为了“通用”做一个拥有几十个 property 的万能卡片。

## Documentation

复杂组件至少记录：

```text
Purpose
Properties
Events
Slots
States
Example
Edge cases
```

## Anti-Patterns

- 20+ properties 的万能组件。
- 组件内部直接编排多个不相关业务 API。
- 父级依赖子组件私有 data。
- 纯粹因为文件长就机械拆组件。
- 复制粘贴同一种稳定 UI 而不复用。

---
name: miniapp-state-data
description: 微信小程序状态与数据管理 Skill。用于 setData、派生状态、缓存、分页、刷新、并发请求、离线与跨页面同步。
metadata:
  version: "2.0.0"
---

# Mini App State & Data

## Goal

保持页面状态可预测、更新成本可控，并避免“接口返回顺序决定 UI 真相”的竞态问题。

## State Ownership

- 页面局部展示状态：页面持有。
- 可复用组件局部交互：组件持有。
- 跨页面共享且生命周期更长的数据：使用项目既有全局 store/service/cache。
- 服务端真值：通过 API 获取，客户端缓存只是一份副本。

不要为了方便把所有东西放到全局变量。

## setData Discipline

- 只更新必要路径。
- 避免频繁传输大对象、大数组、不可见字段。
- 高频事件需要节流/合并更新时要有明确理由。
- 不将无需渲染的数据全部放进 view data。

## Derived State

能由源数据稳定计算出的状态，尽量不要维护第二份容易失同步的副本。例如 `hasMore` 可以根据分页响应语义维护，但不要同时维护多个相互推导的重复字段。

## Async & Race Conditions

常见处理：

- 搜索关键字快速变化：只接受最新请求结果或取消旧请求。
- 页面切换：异步回来时确认上下文仍有效。
- 并发刷新：避免旧响应覆盖新数据。
- 重复进入：明确 onLoad/onShow 谁负责刷新。

## Pagination

明确：

- page/pageSize 或 cursor 模式。
- refreshing 与 loadingMore 分离。
- 去重策略。
- 到底条件。
- 首屏失败与加载更多失败不同处理。

## Cache

缓存前定义：

- key 范围（是否与 userId/tenantId 绑定）。
- TTL / 失效条件。
- schema/version 变化如何处理。
- 是否允许展示 stale 数据并后台刷新。
- 退出登录时哪些缓存必须清理。

## Storage

本地存储适合：轻量偏好、非敏感草稿、可重新获取的缓存。避免长期保存不必要的敏感数据和大体量对象。

## Anti-Patterns

- 所有数据都塞 `app.globalData`。
- 搜索请求后返回的旧结果覆盖新结果。
- 每次输入都把整个页面大对象 `setData`。
- 分页只判断 `list.length > 0` 而无明确结束协议。
- 缓存 key 不区分账号导致串数据。

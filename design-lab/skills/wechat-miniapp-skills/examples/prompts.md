# Prompt Examples

## 新增列表页面

```text
使用 wechat-miniapp-core、miniapp-product-thinking、miniapp-ui-system、miniapp-state-data。

在当前项目新增“我的收藏”页面。
先分析现有目录、主题 token、列表组件和请求层。
需要支持 loading / empty / error / normal、下拉刷新和分页。
只修改必要文件，完成后列出验收点。
```

## 电商商品详情

```text
使用 wechat-miniapp-core、miniapp-ui-system、miniapp-business-workflow、miniapp-api-system。

完善商品详情页的规格选择和加入购物车流程。
前端不要自行判断最终库存或价格，处理重复点击、接口超时和商品状态变化。
```

## 预约服务

```text
使用 miniapp-product-thinking、miniapp-business-workflow、miniapp-api-system。

设计预约流程：选择服务、日期、时段、联系人、确认、提交。
先给出状态机、接口依赖、失败恢复和验收标准，再实现。
```

## 定位能力

```text
使用 wechat-miniapp-core、miniapp-platform-capabilities、miniapp-auth-security。

给门店列表增加“附近门店”。
只在用户点击“查看附近”后请求定位权限；拒绝时允许手动选城市。
需要说明真机验证点和配置要求。
```

## 内容发布

```text
使用 miniapp-business-workflow、miniapp-state-data、miniapp-api-system。

实现图文草稿和发布流程。
失败时保留草稿；上传图片与发布动作分阶段；不要因为一次网络失败丢失用户内容。
```

## AI 助手

```text
使用 miniapp-ai-assistant、miniapp-api-system、miniapp-auth-security、miniapp-business-workflow。

设计一个小程序 AI 助手：可以查询业务信息，也可以通过 Tool Calling 创建预约和提交申请。
输出工具 schema 设计原则、确认机制、会话状态、安全边界和异常恢复。
```

## 性能优化

```text
使用 miniapp-performance 和 miniapp-state-data。

首页首屏慢。先检查主包体积、首屏请求、图片、setData 和重复 onShow 请求，给出有证据的瓶颈后再修改，不要无测量重构。
```

## Bug 修复

```text
使用 wechat-miniapp-core 和 miniapp-debug。

搜索页快速输入关键词时结果偶尔跳回旧内容。
先定位异步竞态，证明根因后做最小修复，并说明回归范围。
```

## Code Review

```text
使用 miniapp-code-review 审查本次 PR。
重点检查：重复提交、越权、旧响应覆盖、页面卸载后的异步回调、敏感日志和平台权限失败分支。
```

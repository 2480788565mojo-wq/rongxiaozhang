# Generic AI Action Flow Example

这个例子故意不绑定特定行业。

## 用户输入

> 帮我预约周六下午 3 点的服务，如果有空位就先告诉我价格和地点。

## 推荐流程

```text
用户消息
  ↓
识别任务: BOOK_SERVICE
  ↓
抽取字段
  date = Saturday
  time = 15:00
  service = unresolved
  ↓
询问/检索缺失字段
  ↓
checkAvailability tool
  ↓
getQuoteOrDetail tool
  ↓
结构化结果卡片
  ↓
用户明确确认
  ↓
createBooking tool
  ↓
服务端权限 + 幂等 + 业务校验
  ↓
返回业务结果
```

## 可迁移到其他场景

同一模式可以用于：

- 电商：搜索商品 → 确认规格 → 创建订单。
- 企业：收集字段 → 校验 → 提交申请。
- 内容：生成草稿 → 用户修改 → 明确确认 → 发布。
- 活动：查询场次 → 填报名信息 → 提交报名。

## 关键原则

- LLM 不成为业务真值来源。
- Tool 必须白名单 + 严格 schema。
- 高影响动作需要明确确认。
- 服务端重新校验权限、状态和关键字段。
- 超时或结果未知时先查询真实结果，避免重复创建。

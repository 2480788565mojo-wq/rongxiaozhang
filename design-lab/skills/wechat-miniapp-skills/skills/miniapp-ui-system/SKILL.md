---
name: miniapp-ui-system
description: 通用微信小程序 UI/UX Skill。用于视觉层级、移动端交互、设计 token、状态页、表单、列表、详情与跨页面一致性。
metadata:
  version: "2.1.0"
---

# Mini App UI System

## Goal

让界面具有真实移动端小程序体验，而不是缩小的桌面网页。修改已有项目时，现有设计系统优先于本 Skill 的默认值。

本 Skill 负责信息层级、交互模式、状态和可用性；需要新增或迁移视觉风格时，按需读取 `miniapp-ui-style-library`；沿用已有主题的局部修改无需加载风格库。

## Visual Style Routing

- 已有品牌设计系统：复用现有系统，不自动换风格。
- 用户指定视觉风格：组合 `miniapp-ui-style-library` 并落到统一 token。
- 新项目且没有品牌规范：默认从 `wechat-clean` 起步，再按产品目标选择其他预设。
- 不要把视觉风格选择与业务行业强绑定。

## Design Tokens

没有现成 token 时可参考：

- spacing：8 / 16 / 24 / 32 / 40 / 48rpx
- page horizontal padding：32rpx
- radius：12 / 16 / 24rpx
- title：36–40rpx / 600
- section title：30–34rpx / 600
- body：28–30rpx
- secondary：24–26rpx
- helper：22–24rpx

这些是起点，不是强制品牌规范。

## Layout Principles

- 优先 Flex/Grid-like layout 能力和小程序支持的 CSS 子集。
- 重要内容靠近用户当前任务，不用大面积装饰性 Hero 挤占首屏。
- 长列表采用移动端列表，不模拟桌面表格。
- 底部固定操作区考虑 safe-area。
- 点击区域足够大，不让图标本身成为唯一可点击区域。
- 通过层级、文案、图标、位置共同表达状态，不只依赖颜色。

## Common Page Patterns

### List

```text
导航/筛选
↓
列表主体
↓
加载更多 / 到底 / 空状态
```

### Detail

```text
核心状态或标题
↓
最重要信息
↓
分组详情
↓
关联内容
↓
主操作
```

### Form

```text
标题/说明
↓
字段分组
↓
校验与帮助
↓
主提交按钮
```

### Search

```text
搜索输入
↓
历史/建议/筛选
↓
结果
↓
空结果 / 加载 / 错误
```

## Feedback

按动作选择：

- 按钮 loading：提交中的短操作。
- 局部 skeleton：结构稳定的内容加载。
- 页面 loading：首屏关键数据完全依赖网络。
- toast：轻量结果反馈，不承载需要用户认真阅读的重要信息。
- modal：真正需要确认的高影响动作，避免滥用。

## Forms

- 标签和输入含义明确。
- 错误尽量靠近字段。
- 键盘类型与输入类型匹配。
- 提交失败后保留用户已填内容。
- 超长表单考虑分步、折叠或渐进披露。

## Accessibility & Readability

- 关键文字保持可读对比度。
- 重要操作不要只靠颜色区分。
- 图标按钮提供可理解的文本语义或辅助说明。
- 支持系统字体缩放/长文本时，避免固定高度导致裁切。

## Existing Project Priority

优先复用：

- theme variables / design tokens
- navbar / tabbar
- button / input / card / dialog
- icons
- empty / error / skeleton

不要因为“更好看”创建第二套视觉语言。

## Anti-Patterns

- Hero Banner + Feature Grid + Footer 的网页模板感。
- 一页塞大量桌面 Dashboard 卡片。
- 过度渐变、玻璃拟态、重阴影。
- 同一页面使用大量强调色。
- 用 toast 展示长错误说明。
- 固定底部按钮遮挡安全区或输入法。

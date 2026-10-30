---
name: miniapp-ui-style-library
description: 微信小程序视觉风格库 Skill。用于选择、定义和落地统一的小程序视觉语言，提供多套领域无关风格、语义化设计 token、组件映射和风格迁移规则。
metadata:
  version: "1.0.0"
---

# Mini App UI Style Library

## Goal

把“做得像小程序”进一步落实为可选择、可复用、可扩展的视觉风格，而不是每次由 Agent 临时发明颜色、圆角、阴影和卡片样式。

本 Skill 只负责 **visual language**。页面信息架构、可用性、状态设计仍由 `miniapp-ui-system` 负责；组件拆分仍由 `miniapp-component-system` 负责。

## Style Selection Priority

选择风格时按以下优先级：

1. 用户明确指定的品牌规范或视觉风格。
2. 当前项目已经存在的 theme、组件库和页面视觉语言。
3. 当前产品属性、内容密度和主要交互目标。
4. 本 Skill 的预设风格。
5. 无足够信息时默认 `wechat-clean`，不要随机混搭。

修改已有项目时，**禁止因为本 Skill 提供了更漂亮的模板就擅自重做全站视觉**。

## Built-in Styles

本库提供 8 套领域无关预设：

| Style | 中文定位 | 适合 |
|---|---|---|
| `wechat-clean` | 微信原生感 / 中性清爽 | 通用入口、服务、账户、表单、工具 |
| `minimal-light` | 极简留白 | 品牌官网型、作品、轻内容、展示 |
| `soft-card` | 柔和卡片 | 生活服务、会员、个人中心、轻社区 |
| `editorial` | 编辑阅读 | 内容、资讯、知识、课程、长文本 |
| `tech-blue` | 科技数据 | AI、效率工具、数据、B2B、控制台 |
| `dark-premium` | 深色高级 | 展示、影音、品牌、沉浸式体验 |
| `playful-color` | 活泼品牌 | 年轻化、活动、互动、游戏化体验 |
| `utility-dense` | 高效工具 | 高频操作、管理、内部工具、复杂表单 |

先读取 [风格索引](references/style-index.md)，仅在需要选择风格时使用。确定风格后只读取相应文件：

- [wechat-clean](references/wechat-clean.md)
- [minimal-light](references/minimal-light.md)
- [soft-card](references/soft-card.md)
- [editorial](references/editorial.md)
- [tech-blue](references/tech-blue.md)
- [dark-premium](references/dark-premium.md)
- [playful-color](references/playful-color.md)
- [utility-dense](references/utility-dense.md)

预设描述是设计起点，实际 token 值沿用项目或根据页面确定。复杂主题迁移可使用 [风格简报](templates/style-brief.md)，局部改色无需生成完整简报。

## Style Decision

新页面在没有既有设计系统时，先判断：

- 任务是“阅读”还是“操作”？
- 内容密度是低、中还是高？
- 是否需要品牌情绪？
- 是否存在大量表单、状态和数据？
- 是否需要长时间阅读？
- 是否适合深色背景？

推荐映射：

```text
高频操作 / 高密度 ───────► utility-dense
阅读优先 ───────────────► editorial
中性通用 ───────────────► wechat-clean
轻品牌 / 强留白 ─────────► minimal-light
柔和亲和 ───────────────► soft-card
科技 / AI / 数据 ────────► tech-blue
沉浸 / 高级展示 ─────────► dark-premium
年轻 / 活动 / 游戏化 ────► playful-color
```

这只是视觉起点，不是行业绑定规则。

## Semantic Tokens

无论采用哪套风格，都优先使用语义 token，而不是在页面里散落具体值：

```text
color.bg.page
color.bg.surface
color.bg.elevated
color.text.primary
color.text.secondary
color.text.muted
color.border.default
color.brand.primary
color.brand.onPrimary
color.status.success
color.status.warning
color.status.danger

space.xs / sm / md / lg / xl
radius.sm / md / lg / pill
shadow.low / medium
font.pageTitle / sectionTitle / body / caption
```

如果项目已有 token 命名，沿用项目命名，不强制替换。

## Component Mapping

主题设计检查实际涉及的高频组件；局部需求只改受影响组件，不扩大到全站：

- navigation / tab bar
- primary / secondary / text button
- input / textarea / picker
- card / list item
- tag / badge / status
- dialog / sheet / toast visual treatment
- empty / error / skeleton
- bottom action bar

页面新增局部视觉时应从这些基础组件继承，不创建“一页一个风格”。

## Style Mixing Rules

允许：

- `editorial` 页面使用少量 `minimal-light` 留白原则。
- `tech-blue` 使用 `utility-dense` 的高密度布局。
- 品牌色覆盖预设 primary color。

禁止：

- 同页混用两套完全不同的圆角、阴影和按钮系统。
- 深色页面里突然出现未适配的白底原生控件块。
- 为“高级感”同时叠加渐变、玻璃、发光、重阴影。
- 每个卡片使用不同强调色。

## Dark Mode

只有在产品明确需要或当前项目已经支持时才设计 dark mode。

深色模式不是简单颜色取反：

- 重新定义 surface 层级。
- 降低大面积纯黑与纯白的视觉疲劳。
- 检查图片、图标、边框和 disabled 状态。
- 保证输入框、弹层、导航栏与系统区域一致。

## Existing Project Migration

若用户要求“把现有项目改成某种风格”：

1. 先盘点现有 token 和基础组件。
2. 先改 token / primitives，再改页面。
3. 建立 1–2 个代表页面作为迁移样板。
4. 检查 normal / loading / empty / error / disabled。
5. 不在一次改动中同时重构无关业务逻辑。

## Deliverable Contract

设计或实现视觉风格时优先输出：

```text
Selected Style
- style-name

Style Rationale
- ...

Tokens
- colors
- spacing
- radius
- typography
- elevation

Component Rules
- button
- input
- card/list
- feedback

Pages Affected
- ...

Consistency Check
- ...
```

## Anti-Patterns

- 把“UI 风格”理解为只换一个主色。
- 一边声称统一设计，一边页面内硬编码几十个视觉值。
- 将 PC Dashboard、Landing Page 或后台模板直接缩到手机宽度。
- 没有读取当前项目就替换全局主题。
- 只设计正常状态，忽略空、错、加载、禁用和提交中状态。
- 用过度渐变、玻璃拟态、发光和重阴影堆砌所谓高级感。
- 强制所有业务使用同一套品牌色或某一行业视觉。

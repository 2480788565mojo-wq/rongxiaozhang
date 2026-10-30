# UI Style Index

## How to use

每次只选择一个 **base style**。品牌色、字体和局部组件可以在 base style 上覆盖，但要保持 token 和组件行为一致。

| Style | Density | Emotion | Radius | Shadow | Primary Use |
|---|---:|---|---|---|---|
| wechat-clean | 中 | 中性、可信 | 中 | 很轻 | 默认通用 |
| minimal-light | 低 | 克制、精品 | 小~中 | 极轻 | 展示、轻内容 |
| soft-card | 中 | 温和、亲近 | 大 | 轻 | 服务、会员、社区 |
| editorial | 中 | 专注、阅读 | 小 | 少 | 内容、知识 |
| tech-blue | 中~高 | 理性、科技 | 中 | 轻 | AI、数据、工具 |
| dark-premium | 低~中 | 沉浸、高级 | 中 | 层级光感 | 影音、品牌展示 |
| playful-color | 中 | 活力、年轻 | 大 | 轻 | 活动、互动 |
| utility-dense | 高 | 高效、直接 | 小~中 | 极少 | 高频操作、管理 |

## Default fallback

如果项目没有品牌规范、用户也没有指定风格：

1. 默认选择 `wechat-clean`。
2. 内容阅读型页面可选择 `editorial`。
3. 高频操作工具可选择 `utility-dense`。
4. 不因为产品与 AI 有关就自动选择深色或霓虹风。

## Files

- `wechat-clean.md`
- `minimal-light.md`
- `soft-card.md`
- `editorial.md`
- `tech-blue.md`
- `dark-premium.md`
- `playful-color.md`
- `utility-dense.md`

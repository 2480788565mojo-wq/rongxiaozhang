# Mini Program UI Style Guide

## Why a separate style library?

`miniapp-ui-system` 解决的是 **结构与可用性**：信息层级、状态、表单、列表、反馈和移动端交互。

`miniapp-ui-style-library` 解决的是 **视觉语言**：颜色、surface、圆角、阴影、字体气质、组件外观和跨页面一致性。

分开之后，同一套业务结构可以安全切换视觉风格，而不需要重写交互逻辑。

## Built-in Styles

### 1. wechat-clean

最稳妥的默认风格。中性、清楚、可信，适合多数新项目作为起点。

### 2. minimal-light

留白更大、装饰更少，强调排版、图片和品牌内容。

### 3. soft-card

圆角和柔和 surface 更明显，适合希望界面更亲和的产品。

### 4. editorial

阅读优先，减少卡片和阴影，让标题、正文、图片和元信息形成节奏。

### 5. tech-blue

适合复杂状态、数据和 AI 工具，但明确避免“AI = 霓虹紫蓝”的模板化设计。

### 6. dark-premium

用于产品明确需要的深色沉浸体验，不默认应用于所有项目。

### 7. playful-color

强调活力和品牌记忆点，同时限制颜色数量和装饰密度。

### 8. utility-dense

高频、高密度任务优先，让扫描和操作效率高于装饰。

## Selection Examples

```text
“做一个新的通用设置页”
→ wechat-clean

“做一个阅读体验很好的文章详情”
→ editorial

“做一个高频使用的库存录入工具”
→ utility-dense

“已有品牌色和 UI 组件”
→ 不选新风格，继承现有设计系统
```

## Recommended Skill Combinations

视觉设计：

```text
wechat-miniapp-core
miniapp-ui-system
miniapp-ui-style-library
```

把视觉落到复用组件：

```text
miniapp-ui-system
miniapp-ui-style-library
miniapp-component-system
```

现有项目视觉升级：

```text
wechat-miniapp-core
miniapp-ui-system
miniapp-ui-style-library
miniapp-code-review
```

## Brand Customization

预设风格不是固定皮肤。推荐顺序：

1. 选 base style。
2. 用品牌色覆盖 `brand.primary`。
3. 继承品牌图标和插图方向。
4. 保持 spacing、radius、surface、button、input 的一致规则。
5. 在 1–2 个代表页面验证后再扩展全局。

## Contribution Rule

新的 UI 风格如果满足以下条件，可以进入 Core Style Library：

- 是视觉语言，不依赖某个行业实体。
- 与现有风格有明确差异。
- 有完整 token、组件和 anti-pattern 说明。
- 能覆盖 normal / loading / empty / error 等状态。
- 不是简单换主色或复制某个品牌。

行业专属主题应放到 `extensions/`。

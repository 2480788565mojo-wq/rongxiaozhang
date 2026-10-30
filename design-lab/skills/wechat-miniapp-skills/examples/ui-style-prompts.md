# UI Style Prompt Examples

## Create a new page with a preset style

```text
使用 wechat-miniapp-core、miniapp-ui-system、miniapp-ui-style-library。

新增一个反馈中心页面。
当前项目没有设计系统，采用 wechat-clean。
先定义页面状态和语义 token，再实现页面。
不要加入营销 Banner，不要使用重阴影。
```

## Ask the agent to choose a style

```text
使用 miniapp-ui-system 和 miniapp-ui-style-library。

我要做一个以长文章和图片阅读为主的小程序。
请先从内置 UI Styles 中选择一个 base style，并说明理由，
然后给出颜色、字号、间距、圆角、卡片和按钮规则。
```

## Restyle an existing project safely

```text
使用 wechat-miniapp-core、miniapp-ui-system、miniapp-ui-style-library。

把当前小程序的视觉统一为 soft-card，但不要修改业务逻辑。
先读取已有 theme、button、input、card 和 navbar，
优先改 token 和基础组件，再选择两个代表页面迁移。
不要一次性重写所有页面。
```

## High-density tool

```text
使用 miniapp-ui-system、miniapp-ui-style-library、miniapp-component-system。

设计一个高频数据录入页，采用 utility-dense。
信息密度可以高，但点击区域、字号和错误提示不能为了紧凑而牺牲可用性。
```

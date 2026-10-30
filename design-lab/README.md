# 荣小账 · UI 方向实验室

这是为了“先选风格、再开工”临时搭的样稿区，**不是小程序源码**，也不会被打进小程序包。

## 怎么看

- 打开 `index.html`：5 套首页并排预览。
- 或单独打开：
  - `a-wechat.html` — 微信原生清爽
  - `b-apple.html` — Apple 浅色卡片
  - `c-editorial.html` — 中文账本 / 编辑
  - `d-dark.html` — 深色数据
  - `e-soft.html` — 柔和亲和
- 每套都是 375×812 的首页样稿；同一个内容，只换视觉规则，方便对比。

## 这些样稿分别用了什么规则

| 方向 | 主要规则来源 | 对应组合 | 适合 | 代价 |
|---|---|---|---|---|
| A 微信原生清爽 | `wechat-miniapp-skills` 的 `wechat-clean` + 微信官方设计规范 | 组合 2 | 最稳、最像原生小程序、审核风险最低 | 辨识度低，容易“普通” |
| B Apple 浅色卡片 | 现有荣小账 token + `refactoring-ui` 的层级/间距规则 | 组合 1 | 现有界面平滑升级，用户不需要重新适应 | 变化不够“惊艳” |
| C 中文账本 / 编辑 | `miniapp-ui-style-library` 的 `editorial` + 微信官方规范 | 组合 2 变体 | 最有“账本”气质，品牌辨识度最高 | 需要接受宋体/纸感，年轻用户可能觉得老派 |
| D 深色数据 | `miniapp-ui-style-library` 的 `dark-premium` + `tech-blue` | 组合 2 变体 | 统计页、夜间、数据感 | 日常记账偏重，长期看容易疲劳 |
| E 柔和亲和 | `miniapp-ui-style-library` 的 `soft-card` | 组合 3 | 亲和、适合养成记账习惯 | 圆角/珊瑚色用多了会偏“轻”，要控制 |

补充：
- 全部样稿都对照了 `wechat-miniprogram-designUI` 的基础规范：rpx 栅格、24rpx 最小字号、TabBar 5 个、胶囊避让、审核红线。
- `ui-ux-pro-max` 也实际跑了，但它给记账 App 推荐的是 **Glassmorphism + Caveat/Quicksand 手写字体**，明显不适合微信小程序；这正说明“高星通用 skill 必须经过小程序规则过滤”，所以我们没有照搬。
- `uview-skills` 暂时没用在 HTML 上，它会在落地阶段用于“这个样式对应 uView 哪个组件”。
- `launch-wechat-miniprogram` 提供的是全流程和“3 套 UI 方向 → WXML/WXSS”的方法，落地阶段才会用到。

## 已选定：B · Apple 浅色卡片

2026-10-28 已选定 B。保留下面的 skill，其余已删除：

- `refactoring-ui-skill` — 层级、间距、字阶
- `wechat-miniprogram-designUI` — 微信官方 rpx / 颜色 / 胶囊 / 审核红线
- `wechat-miniapp-skills` — `miniapp-ui-system` 与 `miniapp-ui-style-library`
- `uview-skills` — 后续落到 uView 组件时用

已删除：`ui-ux-pro-max-skill`（推荐 Glassmorphism/手写字体，不适合记账小程序）、`launch-wechat-miniprogram`（B 不需要全流程）、`uni-helper-skills`（本次未用到）。

候选 skill 仍放在 `design-lab/skills/` 试用区，**没有**装进正式的 `.agents/skills/`；等页面改完再决定是否移入。

## B 的第一轮落地（2026-10-28）

已改真实代码，范围控制在“全局 token + 首页 + 悬浮按钮”：

- `src/styles/tokens.css`：大圆角 40rpx → 36rpx；阴影改为更轻的 `0 12rpx 36rpx`，新增资产卡专用 `--shadow-card`
- `src/pages/index/index.vue`：资产卡改浅蓝渐变 + 细边；金额 62rpx → 64rpx；增加“预算已用”胶囊；指标卡/快捷入口/预算/最近记录统一为更轻的卡片节奏
- `src/components/FabBtn.vue`：蓝色渐变 + 更柔和的投影
- `tsconfig.json`：把两个 vitest setup 文件加入 include，修复 Vitest 4 的 TS 配置解析（不影响业务代码）

验证结果：

- 前端单元测试：172 项通过
- `npm run type-check`：通过
- `npm run build:mp-weixin`：通过，包体约 1.46MB
- `npm run build:h5`：通过

## 全站铺开（第二轮）

已把 B 的卡片节奏铺到全部页面：

- 统计、账单列表、账单详情
- 记账（AI 对话）、预算、账户
- 分类、设置、账本、成员、AA 结算
- 消费洞察列表/报告
- 手动记账、Excel 导入

主要统一项：页面左右 28rpx、卡片圆角 36rpx、轻阴影、标题 30rpx/正文 26–28rpx、列表行高 86–100rpx、主按钮高度 80–84rpx。
账本成员页改成“整块卡片 + 行分隔”，避免每行阴影造成条纹感。

最终验证：**172 项测试通过、type-check 通过、mp-weixin 构建通过（1.46MB）、H5 构建通过**。

## 交互与统一（第三轮）

- 全局 `.pressable` 按压反馈；按钮 active 改为更柔和的缩放/透明度
- 可点击卡片和行加 `hover-class`：首页导入/洞察/最近记录、统计排行、账单日期/账单行、账户行、账本行、设置菜单、洞察卡片
- uView 弹窗统一为 28rpx 圆角、30rpx 按钮字号
- 统计图表卡加细边；统计/账单/洞察的空状态与错误态统一
- 记账页气泡、结果卡加轻描边；账单日期组加圆点与浅渐变
- 没有新增账户/账本空状态（避免数据加载前闪现“还没有账户/账本”）；预算空状态保持不动

## 按钮规范（A · WeUI 标准）

- 主按钮：96rpx 高，32rpx/600，胶囊圆角；一屏只放一个，表单底部可全宽
- 中按钮：80rpx 高，28rpx/600，20rpx 圆角；用于分段、筛选、次级操作
- 小按钮：64rpx 高，24rpx/600，16rpx 圆角；用于行内编辑/删除/加载更多
- 图标按钮：80rpx 圆形
- uView 的 `u-button` 统一覆盖为 96rpx，避免和原生按钮高度不一致
- 按下缩放 0.98，禁用透明度 0.4；小程序用 `hover-class`，不用 `:hover`

## 蓝色动态背景

- 全站 `page` 使用 `#E8EFF8` 浅蓝底 + 两层蓝色光点，60s 漂移
- 漂移距离是 2 个平铺周期（320→640rpx、420→840rpx），幅度比最初版大一倍，循环仍然无缝
- 顶部保留一层淡蓝色光晕
- 原生导航栏同步为 `#E8EFF8`
- 账单页的 Excel 导入按钮、月份/分类筛选按钮保持白底 + `#e3eefb` 细边

## 性能与登录态（2026-10-28）

- dev 包 2.95MB（vendor 2.37MB），release 包 1.47MB；判断页面快慢要用 release，不要用 dev 包下结论
- 401 统一处理：清 token、回首页登录，避免退出后在账单页看到 “Not authenticated”
- 首页登录失败会提示，不再无反馈
- 粒子背景已回退，不再参与页面渲染

## 不要改的地方（用户明确要求）

- 顶部“荣小账”是微信小程序**原生导航栏标题**（`pages.json` 控制），不是页面内容，不要改成“首页”。
- 悬浮按钮可以拖动；不要改它的默认位置，也不要把“遮挡预算空状态”当成 bug 去改。
- 预算空状态保持原样，不要加“去设置”等引导。

## 怎么定

回复其中一种即可：

- `A` / `B` / `C` / `D` / `E`
- 或组合，例如：`B 的排版 + C 的配色`、`A 的底 + E 的圆角`
- 或“都不对，我想要……”，我按你的描述再出第 6 套。

数据都是示例，不是你的真实账本；顶部的微信胶囊是原生控件的占位。

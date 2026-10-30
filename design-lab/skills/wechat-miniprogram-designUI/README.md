# wechat-miniprogram-designUI

微信小程序官方设计规范 Skill —— 为 Claude Code 提供微信小程序 UI/UX 设计的标准规范顾问能力。

## 这是什么？

这是一个 Claude Code Skill，内置了微信小程序官方设计指南的完整规范知识库，包括：

- 组件尺寸标准（rpx 单位，750rpx = 全屏宽度）
- 完整颜色体系（hex/rgba 色值，明暗双模式）
- 导航规范（Navbar / Tabbar / 页面内 Tab / 页面栈限制）
- 基础控件（Button / Input / Radio / Checkbox / Switch / SearchBar）
- 反馈组件（Modal / 半屏弹窗 / ActionSheet / Toast / 骨架屏 / 空状态）
- 内容容器（Card / List / Grid / Accordion）
- 操作交互（手势热区 / 下拉刷新 / 上拉加载 / 横屏适配 / iPad 适配）
- 暗黑模式（完整颜色映射 + CSS 变量示例）
- 审核红线（12 项自查清单，隐私授权 / 仿系统 UI / 胶囊避让等）
- 官方图标资源（4 大渠道入口，图标尺寸规范）

## 安装

将整个目录复制到 Claude Code 的 skills 目录：

```bash
cp -r wechat-miniprogram-designUI ~/.claude/skills/
```

安装后即可通过 `/wechat-miniprogram-designUI` 调用，或在小程序设计相关对话中自动触发。

## 文件结构

```
wechat-miniprogram-designUI/
├── SKILL.md                          # 主 Skill 文件（核心规范速查 + 知识库索引）
├── README.md                         # 本文件
├── agents/
│   └── openai.yaml                   # Agent 接口配置
├── evals/
│   └── evals.json                    # 5 个评估用例
└── references/                       # 按主题拆分的详细规范
    ├── 01-基础规范.md                 # 布局/栅格/字体/颜色体系/暗黑模式/圆角阴影
    ├── 02-导航组件.md                 # Navbar/Tabbar/页面Tab/页面栈深度限制
    ├── 03-基础控件.md                 # Button/Input/Radio/Checkbox/Switch/SearchBar
    ├── 04-反馈组件.md                 # Modal/半屏弹窗/ActionSheet/Toast/骨架屏/空态
    ├── 05-内容容器.md                 # Card/List/Grid/Accordion
    ├── 06-操作交互.md                 # 手势/热区/下拉刷新/横屏/iPad适配
    └── 07-合规审核.md                 # 隐私授权/审核禁忌/12项自查清单
```

## 使用示例

### 组件数值查询
```
问：小程序通栏主按钮多高？圆角多少？
答：88rpx，圆角 8rpx，文字 28rpx。
```

### 审核合规检查
```
问：Tabbar 放 6 个能不能过审？
答：不能。Tabbar 必须 2-5 个，6 个直接审核不通过。
```

### 完整设计 Review
```
问：帮我 review 这个小程序首页设计稿
答：逐项对照 12 项自查清单，指出问题和正确做法。
```

### 暗黑模式适配
```
问：暗黑模式下品牌绿要不要调亮？
答：不要。品牌绿 #07C160 明暗模式不变，其他色值见映射表。
```

## 设计原则

1. **数值优先**：所有尺寸用 rpx，所有颜色给 hex/rgba
2. **红线优先**：审核合规问题先讲禁止项
3. **不杜撰**：官方未规定的明确说明，不编造数值
4. **可落地**：输出格式直接适配设计/前端自查

## 规范来源

本 Skill 严格依据以下微信官方源文件编制：

- [小程序官方设计指南](https://developers.weixin.qq.com/miniprogram/design/index.html)
- [WeUI 视觉 & 组件规范](https://weui.io/)
- [小程序 UI 审核规范](https://developers.weixin.qq.com/miniprogram/product/spec.html)

## 与原版 community skill 的差异

| 项目 | 原版 | 本版 |
|------|------|------|
| 间距体系 | 20/30/40 rpx | **16/24/32/48 rpx**（对齐官方 8px 栅格） |
| 颜色体系 | 无具体色值 | **完整 hex/rgba 色值表** + 暗黑映射 |
| 暗黑模式 | 一句提及 | **独立章节**，颜色映射 + CSS 变量示例 |
| 按钮/输入框 | 无状态色值 | **全部状态色值** + WeUI 类名 |
| 半屏弹窗/ActionSheet | 缺失 | **已补充** |
| 页面栈限制 | 缺失 | **10 层硬性限制 + 策略** |
| 横屏/iPad 适配 | 缺失 | **已补充** |
| 审核清单 | 8 项 | **12 项** |
| Eval 用例 | 3 个 | **5 个** |

## License

MIT

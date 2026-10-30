# 2.2.0

- 将技能版本迁移至 metadata，兼容标准技能校验。
- 按任务规模加载专项和风格参考，避免局部需求扩大为全站改造。
- 增加证据、外部内容、会话并发和 AI 动作确认边界。
- 安装增加 dry-run、路径防护与覆盖失败恢复；校验本地引用并增加回归测试。

# Changelog

## 2.1.0 - 2026-10-03

- 新增 `miniapp-ui-style-library`，将视觉风格与 UI/UX 结构规则解耦。
- 内置 `wechat-clean`、`minimal-light`、`soft-card`、`editorial`、`tech-blue`、`dark-premium`、`playful-color`、`utility-dense` 8 套通用风格。
- 每套风格增加 token、组件表现和 anti-pattern 指南。
- 新增 `docs/ui-style-guide.md`、`examples/ui-style-prompts.md` 和 Style Brief 模板。
- Core / Skill Map / Usage Guide 增加视觉风格路由。
- Core Skills 增加到 15 个。

## 2.0.0 - 2026-10-03

- 将仓库定位升级为“面向所有微信小程序项目”的领域无关 Core Skills。
- 移除用车平台和 AI 对话叫车作为核心依赖。
- 将 AI 能力重构为通用 `miniapp-ai-assistant`。
- 新增 `miniapp-auth-security`、`miniapp-platform-capabilities`、`miniapp-state-data`、`miniapp-business-workflow`、`miniapp-performance`。
- Core Skills 扩展到 14 个。
- 新增 Core / Extension 边界，行业专用能力统一进入可选扩展。
- 更新 README、架构、Skill Map、使用指南和通用示例。
- 加强 manifest/Skill 一致性校验。

## 1.0.0 - 2026-10-03

- 首次发布。
- 提供微信小程序开发 Skills、GitHub Actions、manifest、安装与校验脚本。

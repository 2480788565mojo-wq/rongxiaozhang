# Agent Instructions

本仓库的 canonical Skills 位于 `skills/`，且 Core 必须保持领域无关。

处理微信小程序任务时：

1. 优先读取 `skills/wechat-miniapp-core/SKILL.md`。
2. 先识别项目真实技术栈，不强迫原生/Taro/uni-app 互相迁移。
3. 根据任务读取最相关的专项 Skill；简单任务通常只需 0–1 个专项；复杂任务再增加。
4. 修改现有项目坚持最小必要变更。
5. 复杂需求先定义状态、数据、权限/API 和失败路径，再实现。
6. 完成后给出改动文件、验收点和未验证风险。
7. 不把行业特有实体或状态机写入 Core Skills。

## Routing

- 需求模糊 / 页面规划 → `miniapp-product-thinking`
- UI / WXSS / 交互 → `miniapp-ui-system`；新增/迁移风格时再读 `miniapp-ui-style-library`
- 自定义组件 → `miniapp-component-system`
- API / 网络 / 上传下载 → `miniapp-api-system`
- 登录 / 权限 / 隐私 / 安全 → `miniapp-auth-security`
- 定位 / 相机 / 扫码 / 分享 / 订阅消息 / WebView → `miniapp-platform-capabilities`
- `setData` / 缓存 / 分页 / 并发状态 → `miniapp-state-data`
- 提交 / 预约 / 购买 / 报名 / 发布 / 审批 → `miniapp-business-workflow`
- LLM / AI / RAG / Tool Calling → `miniapp-ai-assistant`
- 包体 / 首屏 / 渲染 / 网络性能 → `miniapp-performance`
- Bug → `miniapp-debug`
- PR 审查 → `miniapp-code-review`
- 测试 / 发布 → `miniapp-testing-release`

## Core Boundary

如果一条规则只适用于某个垂直行业，不应加入 `skills/`。将其放入 `extensions/` 或独立扩展仓库，并显式依赖 Core Skills。

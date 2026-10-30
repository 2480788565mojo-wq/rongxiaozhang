# WeChat Mini Program Skills

**让 AI 编码助手按项目实际情况开发微信小程序。**

15 个可组合的开发技能，覆盖需求、UI、组件、接口、登录、微信平台能力、状态管理、业务流程、AI 助手、性能、调试、审查与发布。保留现有技术栈和设计系统，按任务读取必要规则。

[![Validate Skills](https://github.com/wangleiofficial/wechat-miniapp-skills/actions/workflows/validate.yml/badge.svg)](https://github.com/wangleiofficial/wechat-miniapp-skills/actions/workflows/validate.yml)
[![Version](https://img.shields.io/badge/version-2.2.0-blue)](CHANGELOG.md)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

[快速开始](#快速开始) · [技能目录](#技能目录) · [视觉风格](#视觉风格) · [使用示例](#使用示例) · [文档](#文档)

## 适用场景

在现有小程序中新增页面、接入接口、实现业务流程，或修复登录失效、分页竞态、重复提交等问题。也适用于统一视觉风格、接入 AI 助手，以及代码审查和发布检查。

适用于微信原生、Taro、uni-app 等项目；实现遵循项目框架、版本与已有约定。核心规则不绑定行业，行业特有规则通过 [扩展机制](docs/core-vs-extension.md) 管理。

## 快速开始

### 1. 获取仓库

```bash
git clone https://github.com/wangleiofficial/wechat-miniapp-skills.git
cd wechat-miniapp-skills
```

### 2. 选择接入方式

**直接读取：** 将相关技能文件加入编码助手的上下文，或让具备本地文件读取能力的助手按路径读取：

```text
先读取 skills/wechat-miniapp-core/SKILL.md，
再按当前任务选择必要的专项技能。

在当前小程序新增“收藏列表”页面。
复用已有主题、组件和请求层，覆盖加载、空列表、失败和正常状态。
完成后说明修改文件和实际验证结果。
```

**复制安装：** 使用 Python 3 将技能目录复制到编码工具支持的目录。将下例中的目标路径替换为你的实际技能目录：

```bash
# 查看计划，不写入目标目录
python3 scripts/install_skills.py --target ../your-agent/skills --all --dry-run

# 安装全部技能
python3 scripts/install_skills.py --target ../your-agent/skills --all

# 或只安装主入口与当前需要的专项
python3 scripts/install_skills.py --target ../your-agent/skills \
  wechat-miniapp-core miniapp-ui-system miniapp-api-system
```

不同工具的技能发现目录和加载方式不同，复制后仍需按工具要求启用，见 [平台接入说明](docs/platform-adapters.md)。使用引用资源的技能时，保留整个技能目录。

已有同名目录默认跳过；需要替换时加 `--force`。**覆盖会替换整个同名技能目录，包括本地自定义文件**，请先保留需要的修改。目标目录不得与源技能目录重叠。安装采用暂存复制和备份恢复，逐技能执行。

### 3. 按需组合

`wechat-miniapp-core` 负责项目识别和任务路由，专项技能负责具体问题。简单任务可能只需主入口或一个专项，复杂任务再增加；`recommended_with` 是建议，不会自动安装依赖。

| 当前任务 | 建议专项 |
| --- | --- |
| 新增页面、梳理需求 | `miniapp-product-thinking`、`miniapp-ui-system` |
| 局部 UI 修改 | `miniapp-ui-system` |
| 新增或迁移主题 | `miniapp-ui-system`、`miniapp-ui-style-library` |
| 接口、分页和刷新 | `miniapp-api-system`、`miniapp-state-data` |
| 登录、授权 | `miniapp-auth-security`、`miniapp-api-system` |
| 定位、扫码、相机等 | `miniapp-platform-capabilities`；涉及权限时增加 `miniapp-auth-security` |
| 提交、购买、预约等 | `miniapp-business-workflow`、`miniapp-api-system` |
| AI 助手 | `miniapp-ai-assistant`；涉及业务写入时增加 `miniapp-business-workflow` |
| Bug / 性能 / 审查 / 发布 | 分别选择对应专项 |

## 技能目录

| 技能 | 解决的问题 |
| --- | --- |
| [wechat-miniapp-core](skills/wechat-miniapp-core/SKILL.md) | 技术栈识别、任务范围、最小改动、验证与技能路由 |
| [miniapp-product-thinking](skills/miniapp-product-thinking/SKILL.md) | 需求、信息架构、状态和可观察的验收标准 |
| [miniapp-ui-system](skills/miniapp-ui-system/SKILL.md) | 移动端布局、交互、表单、反馈和可读性 |
| [miniapp-ui-style-library](skills/miniapp-ui-style-library/SKILL.md) | 8 套视觉预设、语义 token 与主题迁移 |
| [miniapp-component-system](skills/miniapp-component-system/SKILL.md) | 组件边界、属性、事件、插槽与复用 |
| [miniapp-api-system](skills/miniapp-api-system/SKILL.md) | 请求封装、错误分类、重试、幂等、文件传输 |
| [miniapp-auth-security](skills/miniapp-auth-security/SKILL.md) | 登录、会话、授权、隐私与服务端权限边界 |
| [miniapp-platform-capabilities](skills/miniapp-platform-capabilities/SKILL.md) | 定位、扫码、媒体、分享、订阅消息、WebView 与降级 |
| [miniapp-state-data](skills/miniapp-state-data/SKILL.md) | setData、缓存、分页、并发与跨页面同步 |
| [miniapp-business-workflow](skills/miniapp-business-workflow/SKILL.md) | 状态机、重复提交、超时后的结果查询与恢复 |
| [miniapp-ai-assistant](skills/miniapp-ai-assistant/SKILL.md) | LLM、RAG、工具调用、确认与安全边界 |
| [miniapp-performance](skills/miniapp-performance/SKILL.md) | 包体、启动、渲染、网络、图片与内存 |
| [miniapp-debug](skills/miniapp-debug/SKILL.md) | 用证据定位生命周期、网络、权限与竞态问题 |
| [miniapp-code-review](skills/miniapp-code-review/SKILL.md) | 正确性、安全、性能和回归风险审查 |
| [miniapp-testing-release](skills/miniapp-testing-release/SKILL.md) | 按风险选择测试、真机验证与发布检查 |

## 视觉风格

已有项目优先复用品牌规范和设计系统。需要新建或迁移风格时，从以下预设选择起点，只读取选中风格的参考文件。

| 预设 | 视觉方向 |
| --- | --- |
| `wechat-clean` | 中性清爽，通用服务、账户与表单 |
| `minimal-light` | 克制留白，品牌与作品展示 |
| `soft-card` | 柔和卡片，亲和与轻服务 |
| `editorial` | 阅读优先，内容和长文本 |
| `tech-blue` | 科技、数据与效率工具 |
| `dark-premium` | 深色沉浸，影音与品牌展示 |
| `playful-color` | 活力、活动与互动体验 |
| `utility-dense` | 高密度、高频操作与复杂表单 |

预设是文字规则与设计建议，不包含现成页面模板或组件代码。详见 [风格索引](skills/miniapp-ui-style-library/references/style-index.md) 和 [UI 风格指南](docs/ui-style-guide.md)。

## 使用示例

**修复分页竞态**

```text
使用 wechat-miniapp-core、miniapp-debug 和 miniapp-state-data。
列表切换筛选后偶尔出现上一筛选的结果。
先查请求顺序和状态更新证据，再做最小修复，验证旧响应不覆盖新状态。
```

**实现可靠提交**

```text
使用 miniapp-business-workflow 和 miniapp-api-system。
完善当前表单提交：防止重复点击，失败保留输入，超时后处理结果未知。
先检查后端是否已有幂等与结果查询契约，不虚构接口能力。
```

**迁移视觉风格**

```text
使用 miniapp-ui-system 和 miniapp-ui-style-library。
将指定的内容详情页调整为 editorial 风格。
先读取现有 token 和基础组件，只修改该页涉及的样式，检查长文本和异常状态。
```

更多例子：[通用任务](examples/prompts.md) · [视觉风格](examples/ui-style-prompts.md) · [AI 动作流程](examples/ai-action-flow.md)。

## 校验与测试

校验和安装脚本使用 Python 3 标准库，无额外运行依赖：

```bash
python3 scripts/validate_skills.py
python3 -m unittest discover -s tests
```

也可执行 `make validate`、`make test`；GitHub Actions 在 push 和 pull request 时执行上述检查。

仓库校验检查元数据、命名、manifest 一致性和技能正文中的本地引用。6 项回归测试覆盖安装、跳过、覆盖、路径保护、试运行与失败恢复。技能版本位于 `metadata.version`，整包版本位于 `skill-manifest.json`。

这些检查验证结构与安装行为；实际开发效果需在真实项目中评估。实现时核对当前微信官方文档和项目版本，平台能力按需做真机验证。

## 文档

| 文档 | 内容 |
| --- | --- |
| [使用指南](docs/usage-guide.md) | 按任务选择技能 |
| [技能地图](docs/skill-map.md) | 能力划分与组合 |
| [架构说明](docs/architecture.md) | 核心组织方式 |
| [平台接入](docs/platform-adapters.md) | 不同编码工具与项目接入 |
| [Core 与扩展](docs/core-vs-extension.md) | 通用规则和行业规则的边界 |
| [更新记录](CHANGELOG.md) | 版本变化 |

仓库以 `skills/<name>/SKILL.md` 为技能源文件，`docs/` 提供使用说明，`examples/` 提供任务示例，`scripts/` 和 `tests/` 维护安装与校验行为。

## 参与贡献

欢迎改进通用规则、补充真实失败案例与回归测试。行业专用能力放入 `extensions/` 或独立仓库。提交前请阅读 [贡献指南](CONTRIBUTING.md)，安全问题见 [安全说明](SECURITY.md)。

## 许可证

[MIT](LICENSE)。

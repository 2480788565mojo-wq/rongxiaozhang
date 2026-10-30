# Platform Adapters

本仓库使用 `skills/<skill-name>/SKILL.md` 作为 canonical source，避免把规则锁死在单一 AI Coding Agent。

## 通用接入

1. 选择任务相关 Skill。
2. 将对应 `SKILL.md` 放入工具支持的 skill/instructions 目录，或显式加入上下文。
3. 通常以 `wechat-miniapp-core` 为主，再叠加 1–3 个专项 Skill。

## 不复制多套内容

不同 Agent 的自动发现目录、front matter 和命名方式会变化。仓库保持一份规范源文件，再通过安装脚本、软链接或 adapter 转换，可避免多份规则逐渐漂移。

## Git Submodule 用法

```text
my-miniapp/
├── miniprogram/
└── .agent-skills/
    └── wechat-miniapp-skills/   # git submodule
```

团队指令只需要约定：微信小程序任务先读 core，再按任务路由到专项 Skill。

## Framework Note

Skills 关注微信小程序工程原则，不假设所有项目都是原生。Agent 应先识别当前项目是原生、Taro、uni-app 或其他既有方案，再按项目语法落地规则。

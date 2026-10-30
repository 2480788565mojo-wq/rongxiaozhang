# Contributing

欢迎共同建设面向所有微信小程序项目的通用 Skills。

## Core 原则

`skills/` 中的 Skill 必须尽量领域无关。一个规则如果只服务某个行业，应进入 `extensions/` 或单独仓库。

## 新 Skill 最低要求

路径：

```text
skills/<skill-name>/SKILL.md
```

front matter：

```yaml
---
name: skill-name
description: 一句话描述适用范围
metadata:
  version: "1.0.0"
---
```

至少包含：

- 清晰目标或 Mission
- 可执行规则/工作流
- 边界和异常情况
- `## Anti-Patterns`

## 命名

- kebab-case。
- 一个 Skill 解决一个稳定问题域。
- 不把互不相关规则塞进同一 Skill。
- 名称不要绑定单个公司、项目或客户。

## 修改 Core 时请检查

- 是否无意引入了某个行业的专用实体/状态机？
- 是否与微信平台真实约束一致？
- 是否会强迫所有项目采用某个框架或目录？
- 是否能转化成 Agent 可以执行的规则？
- 是否与其他 Skill 重复或冲突？

## Pull Request

提交前运行：

```bash
python scripts/validate_skills.py
```

PR 请说明：问题、改动、为什么适合 Core、验证方式。

<div align="center">

# uview-skills

**uView UI framework skills — uView 2.x, uView Pro for uni-app**

[![GitHub](https://img.shields.io/badge/github-full--stack--skills%2Fuview-skills-green.svg)](https://github.com/full-stack-skills/uview-skills)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Agent Skills](https://img.shields.io/badge/Agent%20Skills-Compatible-purple.svg)](https://agentskills.io)

English | [简体中文](./README.zh-CN.md)

[Introduction](#-introduction) · [Install](#-install) · [Skills](#-skills) · [Supported Agents](#-supported-agents) · [Ecosystem](#-ecosystem)

</div>

---

## 📖 Introduction

**uView UI Skills** is a curated collection of Agent Skills for AI coding agents, part of the [Full Stack Skills](https://github.com/partme-ai/full-stack-skills) ecosystem maintained by [PartMe.AI](https://github.com/partme-ai).

This package includes **2 skills**. Each skill is a self-contained `SKILL.md` file that AI agents load on-demand.

## 📦 Install

```bash
npx skills add full-stack-skills/uview-skills
```

Or install specific skills: `npx skills add full-stack-skills/uview-skills --skill <skill-name>`

## 🎯 Skills (2)

| Skill | Description |
|-------|-------------|
| `uview-pro-vue3` | Provides comprehensive guidance for uView Pro Vue 3 component library including components, tools, layouts, and templ... |
| `uview-vue2` | Provides comprehensive guidance for uView Vue 2 component library including components, tools, and layouts. Use when ... |

## 🤖 Supported Agents

Works with [Claude Code](https://code.claude.com), [Codex](https://developers.openai.com/codex), [Cursor](https://cursor.com), [OpenCode](https://opencode.ai), [Gemini CLI](https://geminicli.com), [GitHub Copilot](https://github.com/features/copilot), [Windsurf](https://codeium.com/windsurf), and [70+ others](https://agentskills.io/clients).

### Claude Code Installation

**Option 1: npx skills CLI (Recommended)**

```bash
npx skills add full-stack-skills/uview-skills
```

**Option 2: Manual Installation**

```bash
git clone https://github.com/full-stack-skills/uview-skills.git
cp -r uview-skills/skills/* .claude/skills/
```

For more details, see the [Claude Code Skills Guide](https://code.claude.com/docs/en/skills) and [Agent Skills Spec](https://agentskills.io/).

## 🌐 Ecosystem

| Resource | Link |
|----------|------|
| **Full Stack Skills** | [github.com/partme-ai/full-stack-skills](https://github.com/partme-ai/full-stack-skills) |
| **All Skill Groups** | [github.com/full-stack-skills](https://github.com/full-stack-skills) |
| **Agent Skills Spec** | [agentskills.io](https://agentskills.io) |
| **Skills CLI** | [github.com/vercel-labs/skills](https://github.com/vercel-labs/skills) |

## 📄 License

Apache 2.0 — see [LICENSE](LICENSE).

Third-party attribution notices: see [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md).

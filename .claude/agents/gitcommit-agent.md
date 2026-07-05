---
name: gitcommit-agent
description: 执行单元测试和质量检查，全部通过后颁发通行证，随后 git commit 会被 pre-commit hook 自动拦截放行
model: opus
tools:
  - Agent
  - Bash
  - Read
  - Write
  - Glob
  - Grep
---
# Git Commit Agent — 通行证颁发代理

执行质量门禁检查。全部通过后颁发**通行证**，之后执行 `git commit` 时 pre-commit hook 会检测通行证并放行。

---

## 工作流程

```
① 清理旧通行证 → ② 并行检查（tester + quality-engineer） → ③ 轮询等待 → ④ 判定
    → 都通过 → 颁发通行证（.claude/checks/pass），用户可以提交
    → 有失败 → 给出失败原因，不颁发通行证
```

---

## 第一步：清理旧通行证

执行 `rm -f .claude/checks/*`，清除上次运行留下的所有标记文件（包括旧通行证）。

确保 `.claude/checks/` 目录存在（`mkdir -p .claude/checks`）。

---

## 第二步：并行启动检查

通过 Agent 工具同时启动两个子代理（使用 `run_in_background: true`）：

| 代理 | 任务 | 通过的标记文件 | 失败的标记文件 |
|------|------|---------------|---------------|
| `tester` | 执行 `npx vitest run` | `.claude/checks/test-passed` | `.claude/checks/test-failed` |
| `quality-engineer` | 安全审计 + 注释检查 + 代码规范 | `.claude/checks/quality-passed` | `.claude/checks/quality-failed` |

---

## 第三步：轮询等待标记文件

每 5 秒检查一次，最长等待 10 分钟：

| 检查条件 | 说明 |
|---------|------|
| 同时存在 test-passed / test-failed 之一 | tester 已完成 |
| 同时存在 quality-passed / quality-failed 之一 | quality-engineer 已完成 |

---

## 第四步：判定结果

### ✅ 全部通过

同时存在 `.claude/checks/test-passed` **和** `.claude/checks/quality-passed`：

1. 读取两个标记文件内容，获取评分详情
2. **颁发通行证** → 写入 `.claude/checks/pass`，内容格式：
   ```
   PASS
   单元测试: 45 项全部通过 ✅
   质量检查: 83 分 ✅
   颁发时间: 2026-07-04 18:00
   ```
3. 输出提示给用户：通行证已颁发，可以执行 `git commit` 或使用 `git-save` 存档了
4. **不直接提交**，由 pre-commit hook 放行

### ❌ 有失败

存在 `.claude/checks/test-failed` 或 `.claude/checks/quality-failed`：

1. 读取失败标记文件内容
2. 输出失败报告给用户，列出具体问题和修复建议
3. **不颁发通行证**，用户修复后需重新运行 gitcommit-agent

### ⏱ 超时

1. 输出超时错误信息
2. 清理标记文件

---

## 通行证说明

通行证文件 `.claude/checks/pass` 被 `.gitignore` 排除，不会被提交到仓库。

**生命周期：**
1. `gitcommit-agent` 检查通过后 → 创建
2. 执行 `git commit` 时，`pre-commit` hook 检查通行证 → 有则放行、无则拒绝（不删除通行证）
3. 执行 `git push` 成功后，`pre-push` hook 自动删除通行证
4. 一张通行证在 push 之前可多次使用，推送后自动失效，下轮需重新获取

---

## 输出格式

### 通过时

```
╔══════════════════════════════════════╗
║   🟢 质量门禁通过，通行证已颁发      ║
╠══════════════════════════════════════╣
║  单元测试: 45 项全部通过 ✅          ║
║  质量检查: 83 分 ✅                   ║
║                                       ║
║  现在可以执行 git-save 或 git commit  ║
║  pre-commit hook 会自动放行           ║
╚══════════════════════════════════════╝
```

### 拒绝时

```
╔══════════════════════════════════════╗
║   🔴 质量门禁未通过，拒绝颁发通行证  ║
╠══════════════════════════════════════╣
║  单元测试: 3 项失败 ❌               ║
║    → store.test.ts → 删除不存在的记录 ║
║                                       ║
║  请修复上述问题后重新运行             ║
║  gitcommit-agent                      ║
╚══════════════════════════════════════╝
```

---

## 关键要求

- ❌ **不向用户提问任何问题**（完全自动化）
- ✅ 子代理使用 `run_in_background: true` 并行运行
- ✅ 使用轮询而非睡眠等待，每 5 秒检查一次
- ✅ 只颁发通行证，不执行 git commit，commit 交给 pre-commit hook 处理
- ✅ 失败时给出具体原因和修复建议

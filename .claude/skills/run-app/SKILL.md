---
name: run-app
description: 快速启动 UniApp(Vue3)+Vite 项目。自动检测环境、安装依赖、启动开发服务器并输出访问地址。使用当用户想启动项目时。
---

# Run UniApp Project

充当资深前端工程师，自动分析整个启动过程。遇到错误先定位根因，再给出修复方案。不要把 Deprecation Warning 误判为 Error。

## 第一步：检查运行环境

自动检测以下项，缺一不可。任何一项不满足则停止执行并说明原因：

- **Node.js** — 运行 `node -v`，如果报错则提示"Node.js 未安装，请前往 https://nodejs.org 下载安装"
- **npm** — 运行 `npm -v`，如果报错则提示"npm 不可用"
- **package.json** — 检查当前目录是否存在 `package.json`，如果不存在则提示"当前目录不是 UniApp 项目，未找到 package.json"
- **UniApp 项目特征** — 检查 `package.json` 中是否包含 `@dcloudio` 相关依赖，如果没有则提示"当前目录可能不是 UniApp 项目"

## 第二步：检查依赖

检查 `node_modules` 目录是否存在：

- 如果**不存在** → 执行 `npm install`，等待完成
  - 如果 `npm install` 失败 → 分析具体错误（网络问题、权限问题、版本冲突）并给出修复建议
- 如果**已存在** → 跳过，告知用户"依赖已安装，跳过 npm install"

## 第三步：检测端口

使用 `netstat` 或 `curl` 检测默认端口 5173 是否被占用：
- 如果被占用 → **不要报错**，直接执行 `npm run dev:h5`，让 Vite 自动切换到可用端口
- 如果未被占用 → 正常启动

## 第四步：启动项目

执行 `npm run dev:h5`。等待输出中出现以下标志：
- `Local:`
- `Network:`
- `Compiler version`
- `ready in`
- 或者 Vite 的 `Local:` 地址行

提取最终访问地址（如 `http://localhost:5174`）。

**注意：** 如果输出中包含 `uni-app 有新版本发布` 的升级提示，这是正常消息，不是错误。

## 第五步：错误诊断

如果启动失败，自动分析错误类型并给出解决方案：

| 错误特征 | 根因 | 解决方案 |
|----------|------|---------|
| `npm ERR!` `ENOENT` `ERR!` | npm install 失败 | 检查网络、npm 源是否可用（尝试 `npm config set registry https://registry.npmmirror.com`）|
| `Module not found` `Cannot find module` | 缺少依赖 | 执行 `npm install` 或 `npm install <缺失的包>` |
| `Preprocessor dependency "sass" not found` | 缺少 sass | 执行 `npm install -D sass` |
| `port is in use` `EADDRINUSE` | 端口冲突 | 告知用户端口被占用，Vite 会自动分配新端口，无需手动干预 |
| `SyntaxError` `Unexpected token` | package.json 语法错误 | 检查 package.json 的 JSON 格式 |
| `Node version` `engine` | Node.js 版本不兼容 | 检查 package.json 中的 engines 字段，建议使用 LTS 版本 |
| `vite.config.ts` 相关错误 | Vite 配置错误 | 检查 vite.config.ts 语法和插件配置 |

## 第六步：忽略无关 Warning

以下输出内容属于 Warning 级别，**不视为启动失败**：

- `Deprecation Warning`
- `legacy-js-api`
- `Sass @import` 或 `@import is deprecated`
- `uview-plus` 相关的 deprecation 警告
- `The CJS build of Vite's Node API is deprecated`

检测到这些时，告知用户：
> 项目已正常运行。这些是 Sass/依赖库的未来版本废弃警告，不影响当前开发和调试。

## 第七步：最终输出

格式如下：

```
Project Status
-------------------------
Status    : ✅ Startup Successful / ❌ Failed
URL       : http://localhost:5174
Compiler  : Vue3 + Vite
Errors    : None / <具体错误>
Warnings  : None / Sass Deprecation Warning (Safe to Ignore)

Ready for Development.
```

按照实际情况填写各字段。如果启动失败，URL 字段写 `N/A` 并在 Errors 中写明原因和修复步骤。

---
name: rebuild-app
description: 将荣小账 APP 重新打包构建。支持 H5 网页版和微信小程序版的生产环境构建，输出最终可部署文件。
---

# Rebuild UniApp Project

充当资深前端工程师，自动完成 UniApp 项目的生产环境打包构建。遇到错误先定位根因，再给出修复方案。

## 第一步：检查运行环境

自动检测以下项，缺一不可：

- **Node.js** — 运行 `node -v`，如果报错则提示"Node.js 未安装，请前往 https://nodejs.org 下载安装"
- **npm** — 运行 `npm -v`，如果报错则提示"npm 不可用"
- **package.json** — 检查当前目录是否存在 `package.json`
- **UniApp 项目特征** — 检查 `package.json` 中是否包含 `@dcloudio` 相关依赖
- **node_modules** — 检查依赖是否已安装，未安装则先执行 `npm install`

## 第二步：确认构建目标

询问用户要构建哪个平台：

| 序号 | 平台 | 构建命令 | 输出目录 |
|------|------|---------|---------|
| 1 | H5 网页版 | `npm run build:h5` | `dist/build/h5/` |
| 2 | 微信小程序 | `npm run build:mp-weixin` | `dist/build/mp-weixin/` |
| 3 | 全部构建（H5 + 微信小程序） | 依次执行两个命令 | 两者都有 |

列出选项供用户选择。

## 第三步：执行构建

1. 根据用户选择执行对应的构建命令
2. 构建过程中实时输出进度
3. 等待构建完成

## 第四步：输出结果

构建完成后，输出以下信息：

```
Build Status
-------------------------
Platform     : H5 / WeChat Mini Program / All
Status       : ✅ Build Successful / ❌ Failed
Output Dir   : dist/build/h5/  /  dist/build/mp-weixin/
Build Time   : ~X seconds
Size         : Total / Gzipped (如有工具支持)

Ready for Deployment.
```

## 第五步：错误诊断

如果构建失败，自动分析错误类型并给出解决方案：

| 错误特征 | 根因 | 解决方案 |
|----------|------|---------|
| `Module not found` `Cannot find module` | 缺少依赖 | 执行 `npm install` 安装缺失的包 |
| `TypeScript error` `TS2322` | 类型错误 | 运行 `npm run type-check` 查看具体类型错误 |
| `SyntaxError` | 代码语法错误 | 检查提示的具体文件和行号 |
| `Sass` 相关错误 | Sass 编译错误 | 检查 scss 文件语法 |
| `Build failed with errors` | 构建编译错误 | 分析具体错误提示并定位原因 |
| `Out of memory` `JS stack` | 内存不足 | 尝试 `NODE_OPTIONS="--max-old-space-size=4096"` 增加内存 |

## 第六步：最终提示

告知用户构建产物所在目录，以及如何部署：
- **H5 版**：将 `dist/build/h5/` 目录部署到 Web 服务器即可
- **微信小程序**：用微信开发者工具打开 `dist/build/mp-weixin/` 目录，上传发布

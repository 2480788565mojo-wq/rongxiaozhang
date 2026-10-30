---
name: miniapp-auth-security
description: 微信小程序身份、授权、隐私与客户端安全 Skill。用于 wx.login、会话、用户授权、敏感数据、权限边界和安全审查。
metadata:
  version: "2.0.0"
---

# Mini App Auth & Security

## Scope

处理“用户是谁、能做什么、哪些数据可以在客户端出现、何时请求微信权限”。不把前端限制当作真正安全控制。

## Login Architecture

常见流程：

```text
wx.login()
  ↓ code
own backend
  ↓ exchange / verify with WeChat server
application session
  ↓
mini program stores only appropriate session credential
```

不要在小程序里保存微信服务端密钥或直接实现本应由后端完成的凭据交换。

## Session Rules

- session 获取、过期、刷新集中处理。
- 多请求同时遇到登录失效时避免并发触发多次登录流程。
- token / session 不写普通日志。
- 退出登录清理与当前账号相关的敏感缓存。
- 切换账号后避免复用上一账号的页面缓存。

## Authorization

前端可以隐藏不可用入口以改善体验，但后端必须再次校验权限。角色、会员等级、资源归属、管理员能力等都不能只靠客户端布尔值决定。

## Permission Request UX

定位、相册、相机等能力遵循：

1. 用户触发相关功能。
2. 解释为什么需要。
3. 请求权限。
4. 拒绝时提供可用替代路径或设置入口（若业务允许）。

避免启动即索取与当前任务无关的权限。

## Privacy & Sensitive Data

- 最小化收集。
- 仅在必要页面展示。
- 日志脱敏。
- 本地存储敏感数据前先判断是否真的需要。
- 用户退出或数据失效后清理不再需要的本地副本。
- 隐私协议和实际调用的平台能力保持一致。

## Client Security

永远假设客户端代码和请求可以被观察或修改。以下规则必须由服务端执行：

- 最终权限
- 业务资格
- 价格/库存/额度
- 防重复关键动作
- 支付结果
- 风控决策

## Input & Content

对用户输入、富文本、外部 URL、文件名等做必要校验。不要把外部文本直接拼接为内部命令、查询表达式或可信 HTML 语义。

## Security Review Output

发现问题时说明：攻击面、影响、前端缓解、服务端必须做的校验、验证方式。

## Anti-Patterns

- 把 `isAdmin=true` 存本地后当作授权依据。
- 在前端仓库放服务端 secret。
- 把完整 token、手机号、证件号写日志。
- 无上下文地在首次启动请求所有权限。
- 认为按钮 disabled 就能防止重复交易或越权。

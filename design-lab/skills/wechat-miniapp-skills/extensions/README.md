# Extensions

这里用于放置**可选行业/业务扩展包**。

Core `skills/` 必须保持领域无关。医疗、酒店、出行、餐饮、保险、企业内部业务等专用 Skill 应放在这里，或维护为独立仓库。

扩展可以依赖 Core，例如：

```text
my-domain-skill
  depends on:
  - wechat-miniapp-core
  - miniapp-api-system
  - miniapp-business-workflow
```

Core 不应反向依赖任何 Extension。

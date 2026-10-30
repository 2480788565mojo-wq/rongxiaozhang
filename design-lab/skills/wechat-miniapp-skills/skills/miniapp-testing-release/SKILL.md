---
name: miniapp-testing-release
description: 通用微信小程序测试与发布 Skill。用于测试矩阵、真机验证、回归、隐私权限、版本检查、灰度和上线风险管理。
metadata:
  version: "2.0.0"
---

# Mini App Testing & Release

## Test Layers

按项目已有能力选择：

1. lint / typecheck / static checks
2. unit tests
3. API/service tests
4. component/page interaction tests
5. integration / E2E
6. real-device verification

不要为了规则强行引入当前项目没有维护能力的测试框架；核心目标是覆盖风险。

## Generic Regression Matrix

至少根据改动检查：

- 首次进入
- 正常数据
- 空数据
- 慢网络
- 请求失败
- 登录失效/无权限
- 重复点击
- 返回再进入
- 下拉刷新/分页（如有）
- 前后台切换
- 小屏/大屏/长文本
- iOS/Android 真机差异（涉及平台能力时）

## High-Impact Action Matrix

购买、提交、预约、发布、删除等流程额外验证：

- 重复提交
- 中途取消
- 网络超时后真实结果
- 后端状态已变化
- 提交失败后数据是否保留
- 成功页/返回路径是否正确

## Pre-Release

- 环境和 API 域名正确。
- 无测试账号、debug 开关、secret。
- 隐私声明与实际权限调用一致。
- 分包、资源、配置符合发布限制。
- 错误监控/日志可追踪且脱敏。
- 核心功能至少完成目标真机验证。
- 版本说明和回滚/关闭方案符合风险等级。

## Rollout

高风险改动优先考虑功能开关、灰度、指标观察和快速回退。低风险 UI 修复不必机械套用重型发布流程。

## Output

```text
已验证
- ...

未验证
- ...

阻断项
- ...

上线后观察
- ...
```

## Anti-Patterns

- 只在开发者工具验证涉及系统能力的功能。
- 把“编译通过”当功能测试。
- 发布前第一次连接真实环境。
- 高影响流程完全没有重复提交/超时回归。
- 不区分低风险与高风险改动，所有版本都用同一套机械流程。

import { api } from "./client";

/** 后端公开配置，由服务端开关控制，决定 AI 相关功能是否对用户展示 */
export interface AppConfig {
  ai_enabled: boolean;
}

/** 拉取客户端配置（免登录接口，App 启动时调用） */
export function getAppConfig() {
  return api<AppConfig>("/config");
}

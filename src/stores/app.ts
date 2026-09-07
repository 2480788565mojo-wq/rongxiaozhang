import { ref } from "vue";
import { defineStore } from "pinia";
import { getAppConfig } from "@/api/app";

/**
 * 应用级功能开关 store。
 * aiEnabled 默认 false（安全侧）：只有后端明确返回 true 才展示 AI 功能，
 * 避免网络抖动或审核期开关关闭时闪现 AI 入口。
 */
export const useAppStore = defineStore("app", () => {
  const aiEnabled = ref(false);
  const configLoaded = ref(false);

  async function fetchConfig() {
    try {
      const config = await getAppConfig();
      aiEnabled.value = config.ai_enabled === true;
    } catch {
      // 拉取失败保持默认隐藏：服务不可用时整个 App 也无法登录，不引入额外问题
      aiEnabled.value = false;
    } finally {
      configLoaded.value = true;
    }
  }

  return { aiEnabled, configLoaded, fetchConfig };
});

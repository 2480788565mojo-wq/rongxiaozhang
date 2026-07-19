// 导入 Vue 框架和 UI 组件库
import { createSSRApp } from "vue";
import { createPinia } from "pinia";
import App from "./App.vue";
import uviewPlus from "uview-plus";

// 创建 uni-app 应用实例，注册 uview-plus UI 组件库
export function createApp() {
  const app = createSSRApp(App);
  app.use(createPinia());
  app.use(uviewPlus);
  return {
    app,
  };
}

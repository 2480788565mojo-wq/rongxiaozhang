<script setup lang="ts">
import { watch } from "vue";
import { onLaunch } from "@dcloudio/uni-app";
import { useSSEStore } from "@/stores/sse";
import { useUserStore } from "@/stores/user";
import { useAppStore } from "@/stores/app";

const userStore = useUserStore();
const sseStore = useSSEStore();
const appStore = useAppStore();

// 任意页面 token 失效（退出、过期、切换账号）统一回首页登录，避免各页各自弹 401。
uni.$on("rxz:auth-expired", () => {
  userStore.logout();
  uni.showToast({ title: "登录已失效，请重新登录", icon: "none" });
  setTimeout(() => {
    uni.reLaunch({ url: "/pages/index/index" });
  }, 350);
});

// App.vue 的模板不会在微信小程序端渲染，因此全局连接必须由应用生命周期维护。
watch(
  () => userStore.token,
  (token) => {
    if (token) sseStore.connect(token);
    else sseStore.disconnect();
  },
);

onLaunch(async () => {
  // 功能开关是免登录接口，先拉取；失败时 store 内部默认隐藏 AI，不阻塞启动
  appStore.fetchConfig();
  await userStore.restore();
  // token 从本地存储恢复时值可能没有变化，watch 不会触发，需要主动连接一次。
  if (userStore.token) sseStore.connect(userStore.token);
  else sseStore.disconnect();
});
</script>

<style lang="scss">
@import "uview-plus/index.scss";
@import "@/styles/tokens.css";
@import "@/styles/atoms.css";
@import "@/styles/theme.css";
</style>

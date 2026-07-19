<script setup lang="ts">
import { watch } from "vue";
import { onLaunch } from "@dcloudio/uni-app";
import { useSSEStore } from "@/stores/sse";
import { useUserStore } from "@/stores/user";

const userStore = useUserStore();
const sseStore = useSSEStore();

// App.vue 的模板不会在微信小程序端渲染，因此全局连接必须由应用生命周期维护。
watch(
  () => userStore.token,
  (token) => {
    if (token) sseStore.connect(token);
    else sseStore.disconnect();
  },
);

onLaunch(async () => {
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

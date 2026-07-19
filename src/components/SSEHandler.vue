<template><view class="sse-handler" aria-hidden="true" /></template>

<script setup lang="ts">
import { onMounted, onUnmounted, watch } from "vue";
import { useSSEStore } from "@/stores/sse";
import { useUserStore } from "@/stores/user";

const userStore = useUserStore();
const sseStore = useSSEStore();

watch(
  () => userStore.token,
  (token) => {
    if (token) sseStore.connect(token);
    else sseStore.disconnect();
  },
);

onMounted(() => {
  if (userStore.token) sseStore.connect(userStore.token);
});
onUnmounted(() => sseStore.disconnect());
</script>

<style scoped>
.sse-handler { display: none; }
</style>

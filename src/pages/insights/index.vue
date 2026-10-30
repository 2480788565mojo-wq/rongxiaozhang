<template>
  <view class="page" v-if="appStore.aiEnabled">
    <button class="generate" :loading="generating" @click="generate">生成本月洞察</button>
    <view v-for="item in insights" :key="item.id" class="insight" hover-class="pressable" @click="open(item.id)">
      <view class="insight-head">
        <text class="insight-type">{{ reportName(item.report_type) }}</text>
        <text class="insight-date">{{ item.generated_at.slice(0, 10) }}</text>
      </view>
      <text class="insight-content">{{ item.content }}</text>
    </view>
    <view v-if="!insights.length" class="empty">暂无洞察报告</view>
</view>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { onShow } from "@dcloudio/uni-app";
import { generateInsight, getInsights } from "@/api/insights";
import { useLedgerStore } from "@/stores/ledger";
import { useAppStore } from "@/stores/app";
import type { Insight } from "@/types";

const ledgerStore = useLedgerStore();
const appStore = useAppStore();
const insights = ref<Insight[]>([]);
const generating = ref(false);
onShow(async () => {
  // AI 功能关闭时直接返回，避免通过历史入口进入
  if (!appStore.aiEnabled) { uni.navigateBack(); return; }
  if (!ledgerStore.currentId) await ledgerStore.fetchLedgers();
  if (ledgerStore.currentId) insights.value = (await getInsights(ledgerStore.currentId)).items;
});
async function generate() {
  if (!ledgerStore.currentId) return;
  generating.value = true;
  try {
    await generateInsight(ledgerStore.currentId, "monthly");
    uni.showToast({ title: "已开始生成", icon: "none" });
  } finally { generating.value = false; }
}
function open(id: number) { uni.navigateTo({ url: `/pages/insights/report?id=${id}` }); }
function reportName(type: Insight["report_type"]) { return type === "monthly" ? "月度报告" : type === "weekly" ? "周报" : "专项洞察"; }
</script>

<style scoped>
.page { min-height: 100vh; padding: 28rpx; box-sizing: border-box; }
.generate { width: 100%; height: var(--button-height-lg); border: 0; color: #fff; background: var(--color-primary); border-radius: var(--radius-pill); font-size: var(--button-font-lg); font-weight: 600; line-height: var(--button-height-lg); }
.insight { margin-top: 16rpx; padding: 26rpx; border-radius: var(--radius-lg); background: var(--color-surface); box-shadow: var(--shadow-sm); }
.insight-head { display: flex; align-items: center; justify-content: space-between; }
.insight-type { padding: 7rpx 13rpx; border-radius: var(--radius-pill); color: var(--color-primary); background: var(--color-primary-soft); font-size: 24rpx; font-weight: 600; }
.insight-date { color: var(--color-text-secondary); font-size: 22rpx; }
.insight-content { display: -webkit-box; margin-top: 14rpx; overflow: hidden; color: var(--color-text-secondary); font-size: 27rpx; line-height: 1.65; -webkit-box-orient: vertical; -webkit-line-clamp: 2; }
.empty { margin-top: 16rpx; padding: 120rpx 24rpx; border-radius: var(--radius-lg); color: var(--color-text-secondary); background: var(--color-surface); box-shadow: var(--shadow-sm); font-size: 24rpx; line-height: 1.6; text-align: center; }
</style>

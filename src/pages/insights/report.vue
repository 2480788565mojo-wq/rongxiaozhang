<template>
  <view class="page" v-if="report">
    <view class="report-card">
      <text class="title">{{ reportName }}</text>
      <text class="date">{{ report.generated_at.slice(0, 10) }}</text>
      <text class="content">{{ report.content }}</text>
    </view>
    <view v-if="report.key_findings?.length" class="section">
      <text class="section-title">主要发现</text>
      <text v-for="(item, index) in report.key_findings" :key="index" class="list-item"><text class="index">{{ index + 1 }}</text>{{ item }}</text>
    </view>
    <view v-if="report.suggested_actions?.length" class="section action-section">
      <text class="section-title">行动建议</text>
      <text v-for="(item, index) in report.suggested_actions" :key="index" class="list-item"><text class="index success">{{ index + 1 }}</text>{{ item }}</text>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { onLoad } from "@dcloudio/uni-app";
import { getInsight } from "@/api/insights";
import type { Insight } from "@/types";

const report = ref<Insight | null>(null);
const reportName = computed(() => report.value?.report_type === "monthly" ? "月度消费洞察" : report.value?.report_type === "weekly" ? "每周消费小结" : "消费专项洞察");
onLoad(async (query) => { report.value = await getInsight(Number(query?.id)); });
</script>

<style scoped>
.page { min-height: 100vh; padding: 28rpx 30rpx 80rpx; box-sizing: border-box; }
.report-card, .section { padding: 32rpx; border-radius: var(--radius-lg); background: var(--color-surface); box-shadow: var(--shadow-sm); }
.title { display: block; font-size: 40rpx; font-weight: 700; }
.date { display: block; margin-top: 10rpx; color: var(--color-text-secondary); font-size: 24rpx; }
.content { display: block; margin-top: 28rpx; color: var(--color-text); font-size: 29rpx; line-height: 1.85; white-space: pre-wrap; }
.section { margin-top: 18rpx; }
.section-title { display: block; margin-bottom: 20rpx; font-size: 32rpx; font-weight: 600; }
.list-item { display: flex; align-items: flex-start; gap: 14rpx; margin-top: 16rpx; line-height: 1.7; }
.index { display: inline-flex; align-items: center; justify-content: center; width: 42rpx; height: 42rpx; flex: none; border-radius: 14rpx; color: var(--color-primary); background: var(--color-primary-soft); font-size: 22rpx; line-height: 42rpx; text-align: center; }
.index.success { color: var(--color-success); background: #eaf8ee; }
</style>

<template>
  <view class="page">
    <view v-if="bill" class="detail">
      <view class="amount-block">
        <text class="type-label">{{ bill.type === "expense" ? "支出" : "收入" }}</text>
        <text class="amount" :class="bill.type">{{ bill.type === "expense" ? "-" : "+" }}¥{{ bill.amount.toFixed(2) }}</text>
        <text class="category">{{ bill.category }}{{ bill.subcategory ? ` · ${bill.subcategory}` : "" }}</text>
      </view>
      <view class="rows">
        <view class="row"><text>日期</text><text>{{ bill.bill_date }}</text></view>
        <view class="row"><text>账户</text><text>{{ bill.account || "未设置" }}</text></view>
        <view class="row"><text>备注</text><text>{{ bill.note || "无" }}</text></view>
        <view class="row"><text>录入方式</text><text>{{ bill.ai_parsed ? "AI 记账" : "手动记账" }}</text></view>
      </view>
      <view v-if="bill.shares.length" class="shares">
        <text class="section-title">AA 分摊</text>
        <view v-for="share in bill.shares" :key="share.user_id" class="share-row">
          <text>用户{{ share.user_id }}</text>
          <text>¥{{ share.share_amount.toFixed(2) }}</text>
          <text :class="share.settled ? 'settled' : 'pending'">{{ share.settled ? "已结算" : "待结算" }}</text>
        </view>
      </view>
    </view>
    <view v-else class="loading">{{ loading ? "加载中" : "账单不存在" }}</view>
  </view>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { onLoad } from "@dcloudio/uni-app";
import { getBill } from "@/api/bills";
import type { Bill } from "@/types";

const bill = ref<Bill | null>(null);
const loading = ref(true);

onLoad(async (query) => {
  try {
    bill.value = await getBill(Number(query?.id));
  } catch (error) {
    uni.showToast({ title: error instanceof Error ? error.message : "加载失败", icon: "none" });
  } finally {
    loading.value = false;
  }
});
</script>

<style scoped>
.page { min-height: 100vh; padding: 28rpx; box-sizing: border-box; }
.detail { overflow: hidden; border-radius: var(--radius-lg); background: var(--color-surface); box-shadow: var(--shadow-sm); }
.amount-block { display: flex; flex-direction: column; align-items: center; padding: 52rpx 24rpx 40rpx; border-bottom: 1rpx solid var(--color-border-muted); }
.type-label { color: var(--color-text-secondary); font-size: 24rpx; }
.amount { margin-top: 12rpx; font-family: var(--font-mono); font-size: 58rpx; font-weight: 700; }
.amount.expense { color: var(--color-danger); }
.amount.income { color: var(--color-success); }
.category { margin-top: 14rpx; color: var(--color-text); }
.rows, .shares { padding: 12rpx 28rpx; }
.row, .share-row { display: flex; align-items: center; justify-content: space-between; min-height: 88rpx; border-bottom: 1rpx solid var(--color-border-muted); }
.row text:first-child { color: var(--color-text-secondary); }
.section-title { display: block; padding: 24rpx 0 8rpx; font-size: 32rpx; font-weight: 600; }
.share-row { gap: 16rpx; }
.share-row text:nth-child(2) { margin-left: auto; }
.settled { color: var(--color-success); }
.pending { color: var(--color-warning); }
.loading { margin-top: 24rpx; padding: 140rpx 24rpx; border-radius: var(--radius-lg); color: var(--color-text-secondary); background: var(--color-surface); text-align: center; }
</style>

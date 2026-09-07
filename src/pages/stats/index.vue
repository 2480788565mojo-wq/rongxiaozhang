<template>
  <view class="page">
    <view class="header">
      <view><text class="title">收支统计</text><text class="subtitle">清晰了解每一笔变化</text></view>
      <view class="month-chip"><u-icon name="calendar" color="#4A90E2" size="15" /><text>{{ currentMonth }}</text></view>
    </view>

    <view class="balance-card card">
      <view class="balance-head"><text>本月结余</text><view class="balance-icon"><u-icon name="rmb-circle" color="#4A90E2" size="22" /></view></view>
      <text class="balance-value numeric">¥{{ overview.balance.toFixed(2) }}</text>
    </view>

    <view class="summary-grid">
      <view class="summary-card card expense-card">
        <text class="summary-label">本月支出</text>
        <text class="summary-value numeric">¥{{ overview.expense.toFixed(2) }}</text>
      </view>
      <view class="summary-card card income-card">
        <text class="summary-label">本月收入</text>
        <text class="summary-value numeric">¥{{ overview.income.toFixed(2) }}</text>
      </view>
    </view>

    <view class="chart-section card">
      <view class="section-heading"><view><text class="section-title">收支趋势</text><text class="section-subtitle">近 12 个月</text></view><view class="heading-icon blue"><u-icon name="level" color="#4A90E2" size="20" /></view></view>
      <TrendLine v-if="trend.length" :data="trend" />
      <view v-else class="empty-state"><u-icon name="level" color="#B0B0B5" size="28" /><text>暂无趋势数据</text></view>
    </view>

    <view class="chart-section card">
      <view class="section-heading"><view><text class="section-title">分类占比</text><text class="section-subtitle">本月支出构成</text></view><view class="heading-icon orange"><u-icon name="grid" color="#FF9F0A" size="20" /></view></view>
      <CategoryPie v-if="categories.length" :data="categories" />
      <view v-else class="empty-state"><u-icon name="grid" color="#B0B0B5" size="28" /><text>本月暂无支出</text></view>
    </view>

    <view class="ranking card">
      <view class="section-heading"><view><text class="section-title">分类排行</text><text class="section-subtitle">支出金额前五名</text></view><view class="heading-icon green"><u-icon name="list" color="#34C759" size="20" /></view></view>
      <view v-for="(item, index) in categories.slice(0, 5)" :key="item.category" class="rank-row">
        <view class="rank">{{ index + 1 }}</view>
        <text class="name">{{ item.category }}</text>
        <text class="rank-percent numeric">{{ item.percentage.toFixed(1) }}%</text>
        <text class="rank-amount numeric">¥{{ item.amount.toFixed(2) }}</text>
      </view>
      <view v-if="!categories.length" class="empty-state compact"><u-icon name="order" color="#B0B0B5" size="28" /><text>暂无分类排行</text></view>
    </view>

    <navigator v-if="appStore.aiEnabled" class="ai-card card" url="/pages/insights/index" hover-class="pressable">
      <view class="ai-icon"><u-icon name="chat" color="#7D6EE8" size="23" /></view>
      <view class="ai-copy"><text class="section-title">AI 消费分析</text><text class="section-subtitle">查看本月消费洞察</text></view>
      <u-icon name="arrow-right" color="#C7C7CC" size="18" />
    </navigator>
    <FabBtn />
  </view>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from "vue";
import { onShow } from "@dcloudio/uni-app";
import FabBtn from "@/components/FabBtn.vue";
import TrendLine from "@/components/charts/TrendLine.vue";
import CategoryPie from "@/components/charts/CategoryPie.vue";
import { getCategoryStats, getOverview, getTrend } from "@/api/stats";
import { useLedgerStore } from "@/stores/ledger";
import { useAppStore } from "@/stores/app";
import type { CategoryStat, TrendPoint } from "@/types";

const ledgerStore = useLedgerStore();
const appStore = useAppStore();
const year = ref(0);
const month = ref(0);
const currentMonth = computed(() => `${year.value}年${month.value}月`);
const overview = reactive({ expense: 0, income: 0, balance: 0 });
const trend = ref<TrendPoint[]>([]);
const categories = ref<CategoryStat[]>([]);

async function load() {
  const now = new Date();
  year.value = now.getFullYear();
  month.value = now.getMonth() + 1;
  if (!ledgerStore.currentId) await ledgerStore.fetchLedgers();
  if (!ledgerStore.currentId) return;
  const [summary, trendResponse, categoryResponse] = await Promise.all([
    getOverview(ledgerStore.currentId, year.value, month.value),
    getTrend(ledgerStore.currentId, 12),
    getCategoryStats(ledgerStore.currentId, year.value, month.value),
  ]);
  overview.expense = summary.expense;
  overview.income = summary.income;
  overview.balance = summary.balance;
  trend.value = trendResponse.items;
  categories.value = categoryResponse.items;
}
onShow(() => void load());
</script>

<style scoped>
.page { min-height: 100vh; padding: 24rpx 28rpx 160rpx; box-sizing: border-box; }
.card { border-radius: var(--radius-lg); background: var(--color-surface); box-shadow: var(--shadow-sm); }
.header, .month-chip, .balance-head, .section-heading, .ai-card { display: flex; align-items: center; }
.header, .balance-head, .section-heading { justify-content: space-between; }
.header > view:first-child, .section-heading > view:first-child { display: flex; min-width: 0; flex-direction: column; }
.title { font-size: 44rpx; font-weight: 600; }
.subtitle { margin-top: 6rpx; color: var(--color-text-secondary); font-size: 24rpx; }
.month-chip { gap: 8rpx; padding: 12rpx 16rpx; border-radius: var(--radius-pill); color: var(--color-primary); background: var(--color-primary-soft); font-size: 22rpx; }
.balance-card { margin-top: 32rpx; padding: 34rpx; }
.balance-head { color: var(--color-text-secondary); font-size: 26rpx; }
.balance-icon { display: flex; align-items: center; justify-content: center; width: 68rpx; height: 68rpx; border-radius: 22rpx; background: var(--color-primary-soft); }
.balance-value { display: block; margin-top: 24rpx; overflow: hidden; font-size: 58rpx; font-weight: 700; line-height: 1.2; text-overflow: ellipsis; white-space: nowrap; }
.summary-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16rpx; margin-top: 16rpx; }
.summary-card { display: flex; min-width: 0; min-height: 138rpx; padding: 26rpx; box-sizing: border-box; flex-direction: column; justify-content: space-between; }
.summary-label { color: var(--color-text-secondary); font-size: 24rpx; }
.summary-value { display: block; overflow: hidden; margin-top: 18rpx; font-size: 30rpx; font-weight: 700; text-overflow: ellipsis; white-space: nowrap; }
.expense-card .summary-value { color: var(--color-danger); }
.income-card .summary-value { color: var(--color-success); }
.chart-section, .ranking { margin-top: 16rpx; padding: 30rpx; }
.section-heading { margin-bottom: 16rpx; }
.section-title { display: block; font-size: 32rpx; font-weight: 600; }
.section-subtitle { margin-top: 5rpx; color: var(--color-text-secondary); font-size: 23rpx; }
.heading-icon { display: flex; align-items: center; justify-content: center; width: 64rpx; height: 64rpx; border-radius: 22rpx; }
.heading-icon.blue { background: var(--color-primary-soft); }
.heading-icon.orange { background: #fff4df; }
.heading-icon.green { background: #eaf8ee; }
.rank-row { display: grid; grid-template-columns: 54rpx minmax(0, 1fr) 90rpx 170rpx; align-items: center; min-height: 88rpx; border-bottom: 1rpx solid var(--color-border-muted); }
.rank-row:last-of-type { border-bottom: 0; }
.rank { display: flex; align-items: center; justify-content: center; width: 40rpx; height: 40rpx; border-radius: 14rpx; color: var(--color-primary); background: var(--color-primary-soft); font-size: 22rpx; font-weight: 600; }
.name { overflow: hidden; font-size: 26rpx; text-overflow: ellipsis; white-space: nowrap; }
.rank-percent { color: var(--color-text-secondary); font-size: 23rpx; text-align: right; }
.rank-amount { overflow: hidden; margin-left: 12rpx; font-size: 25rpx; font-weight: 600; text-align: right; text-overflow: ellipsis; white-space: nowrap; }
.empty-state { display: flex; min-height: 360rpx; flex-direction: column; align-items: center; justify-content: center; gap: 14rpx; color: var(--color-text-secondary); font-size: 24rpx; }
.empty-state.compact { min-height: 150rpx; }
.ai-card { gap: 20rpx; margin-top: 16rpx; padding: 28rpx 30rpx; transition: transform var(--transition-fast), opacity var(--transition-fast); }
.ai-icon { display: flex; align-items: center; justify-content: center; width: 70rpx; height: 70rpx; flex: none; border-radius: 24rpx; background: var(--color-accent-soft); }
.ai-copy { display: flex; min-width: 0; flex: 1; flex-direction: column; }
.pressable { opacity: .82; transform: scale(.97); }
</style>

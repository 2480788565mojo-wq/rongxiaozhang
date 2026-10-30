<template>
  <view class="page">
    <view class="header">
      <view><text class="title">收支统计</text><text class="subtitle">清晰了解每一笔变化</text></view>
      <view class="month-chip"><u-icon name="calendar" color="#4A90E2" size="15" /><text>{{ currentMonth }}</text></view>
    </view>

    <view v-if="loadError" class="load-error card"><text>{{ loadError }}</text><button class="retry-stats" :disabled="loading" @click="load">重新加载</button></view>
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
      <view class="section-heading ranking-toggle" role="button" :aria-expanded="rankingExpanded" hover-class="pressable" @click="rankingExpanded = !rankingExpanded">
        <view><text class="section-title">分类排行</text><text class="section-subtitle">支出金额前五名</text></view>
        <view class="ranking-toggle-label"><text>{{ rankingExpanded ? '收起' : '展开' }}</text><u-icon :name="rankingExpanded ? 'arrow-up' : 'arrow-down'" color="#8E8E93" size="16" /></view>
      </view>
      <view v-if="rankingExpanded" class="ranking-content">
        <view v-for="(item, index) in categories.slice(0, 5)" :key="item.category" class="rank-row">
          <view class="rank">{{ index + 1 }}</view>
          <text class="name">{{ item.category }}</text>
          <text class="rank-percent numeric">{{ item.percentage.toFixed(1) }}%</text>
          <text class="rank-amount numeric">¥{{ item.amount.toFixed(2) }}</text>
        </view>
        <view v-if="!categories.length" class="empty-state compact"><u-icon name="order" color="#B0B0B5" size="28" /><text>暂无分类排行</text></view>
      </view>
    </view>

    <navigator v-if="appStore.aiEnabled" class="ai-card card" url="/pages/insights/index" hover-class="pressable">
      <view class="ai-icon"><u-icon name="chat" color="#7D6EE8" size="23" /></view>
      <view class="ai-copy"><text class="section-title">AI 消费分析</text><text class="section-subtitle">查看本月消费洞察</text></view>
      <u-icon name="arrow-right" color="#C7C7CC" size="18" />
    </navigator>
    <FabBtn />
    <BudgetAlert />
</view>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from "vue";
import { onShow } from "@dcloudio/uni-app";
import BudgetAlert from "@/components/BudgetAlert.vue";
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
const rankingExpanded = ref(false);
const loadError = ref('');
const loading = ref(false);
let loadSequence = 0;

async function load() {
  const sequence = ++loadSequence;
  loading.value = true; loadError.value = '';
  const now = new Date(); year.value = now.getFullYear(); month.value = now.getMonth() + 1;
  try {
    if (!ledgerStore.currentId) await ledgerStore.fetchLedgers();
    if (!ledgerStore.currentId) { Object.assign(overview, { expense: 0, income: 0, balance: 0 }); trend.value = []; categories.value = []; return; }
    const ledgerId = ledgerStore.currentId;
    const [summary, trendResponse, categoryResponse] = await Promise.allSettled([
      getOverview(ledgerId, year.value, month.value), getTrend(ledgerId, 12), getCategoryStats(ledgerId, year.value, month.value),
    ]);
    if (sequence !== loadSequence || ledgerId !== ledgerStore.currentId) return;
    // 某一项统计失败时，其他已经成功的数据仍可显示。
    if (summary.status === 'fulfilled') Object.assign(overview, { expense: summary.value.expense, income: summary.value.income, balance: summary.value.balance });
    else Object.assign(overview, { expense: 0, income: 0, balance: 0 });
    trend.value = trendResponse.status === 'fulfilled' ? trendResponse.value.items : [];
    categories.value = categoryResponse.status === 'fulfilled' ? categoryResponse.value.items : [];
    if ([summary, trendResponse, categoryResponse].some(result => result.status === 'rejected')) loadError.value = '部分统计数据加载失败，请重新加载';
  } catch (error) { if (sequence === loadSequence) loadError.value = error instanceof Error ? error.message : '统计加载失败，请重试'; }
  finally { if (sequence === loadSequence) loading.value = false; }
}
onShow(() => void load());
</script>

<style scoped>
.page { min-height: 100vh; padding: 24rpx 28rpx 160rpx; box-sizing: border-box; }
.card { border-radius: var(--radius-lg); background: var(--color-surface); box-shadow: var(--shadow-sm); }
.header, .month-chip, .balance-head, .section-heading, .ai-card { display: flex; align-items: center; }
.header, .balance-head, .section-heading { justify-content: space-between; }
.header > view:first-child, .section-heading > view:first-child { display: flex; min-width: 0; flex-direction: column; }
.title { font-size: 40rpx; font-weight: 600; }
.subtitle { margin-top: 6rpx; color: var(--color-text-secondary); font-size: 22rpx; }
.month-chip { gap: 8rpx; padding: 10rpx 14rpx; border-radius: var(--radius-pill); color: var(--color-primary); background: var(--color-primary-soft); font-size: 22rpx; }
.balance-card {
  margin-top: 28rpx;
  padding: 32rpx;
  border: 1rpx solid #e3eefb;
  background: linear-gradient(135deg, #f4f9ff 0%, #ffffff 62%);
  box-shadow: var(--shadow-card);
}
.balance-head { color: var(--color-text-secondary); font-size: 24rpx; }
.balance-icon { display: flex; align-items: center; justify-content: center; width: 64rpx; height: 64rpx; border-radius: 20rpx; background: rgba(255, 255, 255, .72); }
.balance-value { display: block; margin-top: 22rpx; overflow: hidden; font-size: 56rpx; font-weight: 700; line-height: 1.2; text-overflow: ellipsis; white-space: nowrap; }
.summary-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14rpx; margin-top: 14rpx; }
.summary-card { display: flex; min-width: 0; min-height: 132rpx; padding: 24rpx; box-sizing: border-box; flex-direction: column; justify-content: space-between; border-radius: 28rpx; }
.summary-label { color: var(--color-text-secondary); font-size: 22rpx; }
.summary-value { display: block; overflow: hidden; margin-top: 16rpx; font-size: 28rpx; font-weight: 700; text-overflow: ellipsis; white-space: nowrap; }
.expense-card .summary-value { color: var(--color-danger); }
.income-card .summary-value { color: var(--color-success); }
.chart-section, .ranking { margin-top: 14rpx; padding: 28rpx; overflow: hidden; border: 1rpx solid #eef3fa; }
.section-heading { margin-bottom: 16rpx; }
.ranking-toggle { min-height: 84rpx; margin-bottom: 0; }
.ranking-toggle-label { display: flex; align-items: center; gap: 10rpx; flex: none; margin-left: 16rpx; color: var(--color-text-secondary); font-size: 23rpx; }
.ranking-content { margin-top: 14rpx; }
.section-title { display: block; font-size: 30rpx; font-weight: 600; }
.section-subtitle { margin-top: 5rpx; color: var(--color-text-secondary); font-size: 22rpx; }
.heading-icon { display: flex; align-items: center; justify-content: center; width: 60rpx; height: 60rpx; border-radius: 20rpx; }
.heading-icon.blue { background: var(--color-primary-soft); }
.heading-icon.orange { background: #fff4df; }
.heading-icon.green { background: #eaf8ee; }
.rank-row { display: grid; grid-template-columns: 50rpx minmax(0, 1fr) 86rpx 160rpx; align-items: center; min-height: 84rpx; border-bottom: 1rpx solid var(--color-border-muted); }
.rank-row:last-of-type { border-bottom: 0; }
.rank { display: flex; align-items: center; justify-content: center; width: 38rpx; height: 38rpx; border-radius: 13rpx; color: var(--color-primary); background: var(--color-primary-soft); font-size: 21rpx; font-weight: 600; }
.name { overflow: hidden; font-size: 26rpx; text-overflow: ellipsis; white-space: nowrap; }
.rank-percent { color: var(--color-text-secondary); font-size: 22rpx; text-align: right; }
.rank-amount { overflow: hidden; margin-left: 12rpx; font-size: 25rpx; font-weight: 600; text-align: right; text-overflow: ellipsis; white-space: nowrap; }
.empty-state { display: flex; min-height: 300rpx; flex-direction: column; align-items: center; justify-content: center; gap: 12rpx; color: var(--color-text-secondary); font-size: 24rpx; }
.empty-state.compact { min-height: 150rpx; }
.ai-card { gap: 18rpx; margin-top: 14rpx; padding: 26rpx 28rpx; transition: transform var(--transition-fast), opacity var(--transition-fast); }
.ai-icon { display: flex; align-items: center; justify-content: center; width: 66rpx; height: 66rpx; flex: none; border-radius: 21rpx; background: var(--color-accent-soft); }
.ai-copy { display: flex; min-width: 0; flex: 1; flex-direction: column; }
.pressable { opacity: .82; transform: scale(.97); }
.load-error { margin-top: 18rpx; padding: 22rpx; border: 1rpx solid #ffe0dd; border-radius: var(--radius-lg); color: var(--color-danger); background: #fff7f6; font-size: 24rpx; }
.retry-stats { margin-top: 12rpx; color: var(--color-primary); font-size: 24rpx; }
</style>

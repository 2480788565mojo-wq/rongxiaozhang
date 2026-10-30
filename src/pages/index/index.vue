<template>
  <view class="page">
    <view class="topbar">
      <view class="brand">
        <image class="brand-logo" src="/static/logo.jpg" mode="aspectFill" />
        <view class="brand-copy">
          <text class="brand-name">荣小账</text>
          <text class="brand-greeting">今天也要好好生活</text>
        </view>
      </view>
      <view class="ledger-chip">
        <u-icon name="bookmark" color="#4A90E2" size="16" />
        <text>{{ ledgerStore.current?.name || "未选择账本" }}</text>
      </view>
    </view>

    <view v-if="!userStore.isLoggedIn" class="login-card card">
      <view class="login-copy">
        <text class="login-title">欢迎使用荣小账</text>
        <text class="login-subtitle">登录后查看你的云端账本</text>
      </view>
      <button class="primary-button" :loading="userStore.loading" @click="login">微信登录</button>
    </view>

    <template v-else>
      <view class="asset-card card">
        <view class="asset-header">
          <view>
            <text class="eyebrow">总资产</text>
            <text class="period">{{ year }}年{{ month }}月</text>
          </view>
          <view class="asset-icon"><u-icon name="rmb-circle" color="#4A90E2" size="24" /></view>
        </view>
        <text class="asset-value numeric">¥{{ accountStore.totalBalance.toFixed(2) }}</text>
        <view class="asset-foot">
          <text class="asset-note">所有账户余额</text>
          <text v-if="overview.budget_used_percentage !== null" class="asset-pill">
            预算已用 {{ overview.budget_used_percentage }}%
          </text>
        </view>
      </view>

      <view class="summary-grid">
        <view class="metric-card card expense">
          <text class="metric-label">本月支出</text>
          <text class="metric-value numeric">¥{{ overview.expense.toFixed(2) }}</text>
        </view>
        <view class="metric-card card income">
          <text class="metric-label">本月收入</text>
          <text class="metric-value numeric">¥{{ overview.income.toFixed(2) }}</text>
        </view>
        <view class="metric-card card balance">
          <text class="metric-label">本月结余</text>
          <text class="metric-value numeric">¥{{ overview.balance.toFixed(2) }}</text>
        </view>
      </view>

      <view class="quick-links">
        <button class="quick-item card" @click="go('/pages/ledgers/index')">
          <view class="quick-icon blue"><u-icon name="bookmark" color="#4A90E2" size="22" /></view>
          <text>账本</text>
        </button>
        <button class="quick-item card" @click="go('/pages/accounts/index')">
          <view class="quick-icon green"><u-icon name="account" color="#34C759" size="22" /></view>
          <text>账户</text>
        </button>
        <button class="quick-item card" @click="go('/pages/budget/index')">
          <view class="quick-icon orange"><u-icon name="coupon" color="#FF9F0A" size="22" /></view>
          <text>预算</text>
        </button>
        <button v-if="appStore.aiEnabled" class="quick-item card" @click="go('/pages/insights/index')">
          <view class="quick-icon violet"><u-icon name="chat" color="#7D6EE8" size="22" /></view>
          <text>洞察</text>
        </button>
      </view>

      <view class="excel-import card" hover-class="pressable" @click="openImport">
        <view class="quick-icon blue"><u-icon name="file-text" color="#4A90E2" size="22" /></view>
        <view class="excel-copy">
          <text class="section-title">导入 Excel 账单</text>
          <text class="section-subtitle">从表格批量添加历史记录</text>
        </view>
        <u-icon name="arrow-right" color="#C7C7CC" size="18" />
      </view>

      <view class="section card budget-card" @click="go('/pages/budget/index')">
        <view class="section-head">
          <view>
            <text class="section-title">本月预算</text>
            <text class="section-subtitle">掌握分类消费进度</text>
          </view>
          <u-icon name="arrow-right" color="#C7C7CC" size="18" />
        </view>
        <view v-if="budgetStore.statuses.length" class="budget-list">
          <view v-for="item in budgetStore.statuses.slice(0, 3)" :key="item.category" class="budget-row">
            <view class="budget-copy">
              <text class="budget-name">{{ item.category }}</text>
              <text class="budget-detail numeric">{{ item.percentage.toFixed(1) }}% · 剩余 ¥{{ item.remaining.toFixed(2) }}</text>
            </view>
            <view class="track"><view class="fill" :class="item.risk_level" :style="{ width: `${Math.min(item.percentage, 100)}%` }" /></view>
          </view>
        </view>
        <view v-else class="empty-state">
          <view class="empty-icon"><u-icon name="coupon" color="#86868B" size="24" /></view>
          <text>尚未设置分类预算</text>
        </view>
      </view>

      <view v-if="appStore.aiEnabled" class="insight-card card" hover-class="pressable" @click="go('/pages/insights/index')">
        <view class="insight-icon"><u-icon name="chat" color="#7D6EE8" size="24" /></view>
        <view class="insight-copy">
          <text class="section-title">AI 消费洞察</text>
          <text class="section-subtitle">查看你的本月消费分析</text>
        </view>
        <u-icon name="arrow-right" color="#C7C7CC" size="18" />
      </view>

      <view class="section card recent-card">
        <view class="recent-toggle" role="button" :aria-expanded="recentExpanded" hover-class="pressable" @click="recentExpanded = !recentExpanded">
          <view class="recent-heading">
            <text class="section-title">最近记录</text>
            <text class="section-subtitle">本月最近 {{ recentBills.length }} 笔</text>
            <text v-if="recentBills.length" class="section-subtitle">支出 ¥{{ recentTotals.expense.toFixed(2) }} · 收入 ¥{{ recentTotals.income.toFixed(2) }}</text>
          </view>
          <view class="recent-action"><text>{{ recentExpanded ? '收起' : '展开' }}</text><u-icon :name="recentExpanded ? 'arrow-up' : 'arrow-down'" color="#86868B" size="14" /></view>
        </view>
        <view v-if="recentExpanded" class="recent-content">
        <view v-for="bill in recentBills" :key="bill.id" class="bill-row" hover-class="pressable" @click="openBill(bill.id)">
          <view class="category-mark">{{ bill.category.slice(0, 1) }}</view>
          <view class="bill-copy">
            <text class="bill-category">{{ bill.category }}</text>
            <text class="bill-note">{{ bill.note || bill.account || bill.bill_date }}</text>
          </view>
          <text class="bill-amount numeric" :class="bill.type">{{ bill.type === "expense" ? "-" : "+" }}¥{{ bill.amount.toFixed(2) }}</text>
        </view>
        <view v-if="!recentBills.length" class="empty-state compact">
          <view class="empty-icon"><u-icon name="order" color="#86868B" size="24" /></view>
          <text>本月还没有账单</text>
        </view>
        <button class="text-button" @click="openBills">查看全部账单</button>
        </view>
          </view>
    </template>
    <FabBtn />
    <BudgetAlert />
  </view>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from "vue";
import { onShow } from "@dcloudio/uni-app";
import BudgetAlert from "@/components/BudgetAlert.vue";
import FabBtn from "@/components/FabBtn.vue";
import { getOverview } from "@/api/stats";
import { useBillStore } from "@/stores/bill";
import { useBudgetStore } from "@/stores/budget";
import { useLedgerStore } from "@/stores/ledger";
import { useUserStore } from "@/stores/user";
import { useAppStore } from "@/stores/app";
import { useAccountStore } from "@/stores/account";

const userStore = useUserStore();
const ledgerStore = useLedgerStore();
const billStore = useBillStore();
const budgetStore = useBudgetStore();
const accountStore = useAccountStore();
const appStore = useAppStore();
const year = ref(0);
const month = ref(0);
const overview = reactive({
  expense: 0,
  income: 0,
  balance: 0,
  budget_used_percentage: null as number | null,
});
const recentBills = computed(() => billStore.bills.slice(0, 5));
const recentExpanded = ref(false);
const recentTotals = computed(() => recentBills.value.reduce((totals, bill) => {
  totals[bill.type] += bill.amount;
  return totals;
}, { expense: 0, income: 0 }));

function syncCurrentPeriod() {
  const now = new Date();
  year.value = now.getFullYear();
  month.value = now.getMonth() + 1;
}

async function login() {
  try {
    await userStore.login();
    await load();
  } catch (error) {
    uni.showToast({
      title: error instanceof Error ? error.message : "登录失败，请重试",
      icon: "none",
    });
  }
}

async function load() {
  syncCurrentPeriod();
  if (!userStore.isLoggedIn) return;
  if (!ledgerStore.currentId) {
    try {
      await ledgerStore.fetchLedgers();
    } catch (error) {
      uni.showToast({ title: error instanceof Error ? error.message : "账本加载失败", icon: "none" });
      return;
    }
  }
  if (!ledgerStore.currentId) return;
  const [statsResult, billsResult, budgetResult, accountsResult] = await Promise.allSettled([
    getOverview(ledgerStore.currentId, year.value, month.value),
    billStore.fetchBills(ledgerStore.currentId, true, { year: year.value, month: month.value }),
    budgetStore.fetchStatuses(ledgerStore.currentId, year.value, month.value),
    accountStore.fetchAccounts(ledgerStore.currentId),
  ]);
  if (statsResult.status === "fulfilled") {
    overview.expense = statsResult.value.expense;
    overview.income = statsResult.value.income;
    overview.balance = statsResult.value.balance;
    overview.budget_used_percentage = statsResult.value.budget_used_percentage ?? null;
  } else {
    overview.expense = 0;
    overview.income = 0;
    overview.balance = 0;
    overview.budget_used_percentage = null;
  }
  if (billsResult.status === "rejected") billStore.clear();
  if (budgetResult.status === "rejected") budgetStore.statuses = [];
  if (accountsResult.status === "rejected") accountStore.clear();
  if ([statsResult, billsResult, budgetResult, accountsResult].some((result) => result.status === "rejected")) {
    uni.showToast({ title: "部分首页数据加载失败，请稍后重试", icon: "none" });
  }
}

onShow(() => void load());
function go(url: string) { uni.navigateTo({ url }); }
function openBills() { uni.switchTab({ url: "/pages/bills/index" }); }
function openImport() { uni.navigateTo({ url: "/subpackages/import/index" }); }
function openBill(id: number) { uni.navigateTo({ url: `/pages/bills/detail?id=${id}` }); }
</script>

<style scoped>
.page { min-height: 100vh; padding: 24rpx 28rpx 160rpx; box-sizing: border-box; }
.card { border-radius: var(--radius-lg); background: var(--color-surface); box-shadow: var(--shadow-sm); }
.topbar, .brand, .ledger-chip, .asset-header, .section-head, .budget-copy, .insight-card, .bill-row { display: flex; align-items: center; }
.topbar, .asset-header, .section-head, .budget-copy { justify-content: space-between; }
.brand { min-width: 0; gap: 16rpx; }
.brand-logo { width: 68rpx; height: 68rpx; flex: none; border-radius: 18rpx; }
.brand-copy { display: flex; min-width: 0; flex-direction: column; }
.brand-name { color: var(--color-text); font-size: 32rpx; font-weight: 700; }
.brand-greeting { margin-top: 4rpx; color: var(--color-text-secondary); font-size: 22rpx; }
.ledger-chip { max-width: 230rpx; gap: 8rpx; padding: 10rpx 16rpx; border-radius: var(--radius-pill); color: var(--color-primary); background: var(--color-primary-soft); font-size: 22rpx; }
.ledger-chip text { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.login-card { display: flex; align-items: center; justify-content: space-between; gap: 24rpx; margin-top: 32rpx; padding: 32rpx; }
.login-copy { display: flex; min-width: 0; flex: 1; flex-direction: column; }
.login-title { font-size: 34rpx; font-weight: 600; }
.login-subtitle { margin-top: 8rpx; color: var(--color-text-secondary); font-size: 24rpx; }
.primary-button { width: 200rpx; height: var(--button-height-lg); margin: 0; border: 0; border-radius: var(--radius-pill); color: #fff; background: var(--color-primary); font-size: var(--button-font-lg); font-weight: 600; line-height: var(--button-height-lg); }
.asset-card {
  margin-top: 28rpx;
  padding: 34rpx 34rpx 30rpx;
  border: 1rpx solid #e3eefb;
  background: linear-gradient(135deg, #f4f9ff 0%, #ffffff 62%);
  box-shadow: var(--shadow-card);
  animation: card-enter var(--transition-standard) both;
}
.asset-header > view:first-child { display: flex; flex-direction: column; }
.eyebrow { color: var(--color-text-secondary); font-size: 24rpx; }
.period { margin-top: 6rpx; color: var(--color-text-secondary); font-size: 22rpx; }
.asset-icon { display: flex; align-items: center; justify-content: center; width: 68rpx; height: 68rpx; border-radius: 22rpx; background: rgba(255, 255, 255, .72); }
.asset-value { display: block; margin-top: 24rpx; overflow: hidden; color: var(--color-text); font-size: 64rpx; font-weight: 700; line-height: 1.2; text-overflow: ellipsis; white-space: nowrap; }
.asset-foot { display: flex; align-items: center; justify-content: space-between; gap: 16rpx; margin-top: 10rpx; }
.asset-note { color: var(--color-text-secondary); font-size: 22rpx; }
.asset-pill { flex: none; padding: 8rpx 14rpx; border: 1rpx solid #e3eefb; border-radius: var(--radius-pill); color: var(--color-primary); background: rgba(255, 255, 255, .78); font-size: 22rpx; }
.summary-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14rpx; margin-top: 14rpx; }
.metric-card { display: flex; min-width: 0; min-height: 124rpx; padding: 22rpx 16rpx; box-sizing: border-box; flex-direction: column; justify-content: space-between; border-radius: 28rpx; animation: card-enter var(--transition-standard) both; }
.metric-label { color: var(--color-text-secondary); font-size: 22rpx; }
.metric-value { display: block; overflow: hidden; margin-top: 14rpx; color: var(--color-text); font-size: 26rpx; font-weight: 700; text-overflow: ellipsis; white-space: nowrap; }
.metric-card.expense .metric-value { color: var(--color-danger); }
.metric-card.income .metric-value { color: var(--color-success); }
.metric-card.balance .metric-value { color: var(--color-text); }
.quick-links { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14rpx; margin-top: 14rpx; }
.excel-import { display: flex; align-items: center; gap: 18rpx; margin-top: 14rpx; padding: 22rpx 26rpx; }
.excel-copy { display: flex; min-width: 0; flex: 1; flex-direction: column; }
.quick-item { display: flex; min-width: 0; height: 136rpx; margin: 0; padding: 16rpx 8rpx; flex-direction: column; align-items: center; justify-content: center; border-radius: 28rpx; color: var(--color-text); font-size: 24rpx; line-height: 1; }
.quick-icon { display: flex; align-items: center; justify-content: center; width: 60rpx; height: 60rpx; margin-bottom: 12rpx; border-radius: 20rpx; }
.quick-icon.blue { background: var(--color-primary-soft); }
.quick-icon.green { background: #eaf8ee; }
.quick-icon.orange { background: #fff4df; }
.quick-icon.violet { background: var(--color-accent-soft); }
.section { margin-top: 14rpx; padding: 28rpx; }
.section-head { margin-bottom: 20rpx; }
.section-head > view { display: flex; min-width: 0; flex-direction: column; }
.recent-toggle { display: flex; align-items: center; justify-content: space-between; gap: 20rpx; min-height: 72rpx; }
.recent-heading { display: flex; min-width: 0; flex: 1; flex-direction: column; }
.recent-action { display: flex; flex: none; align-items: center; gap: 10rpx; color: var(--color-text-secondary); font-size: 24rpx; }
.recent-content { margin-top: 18rpx; }
.section-title { color: var(--color-text); font-size: 30rpx; font-weight: 600; }
.section-subtitle { margin-top: 6rpx; color: var(--color-text-secondary); font-size: 22rpx; }
.budget-row + .budget-row { margin-top: 20rpx; }
.budget-copy { gap: 18rpx; }
.budget-name { overflow: hidden; font-size: 26rpx; text-overflow: ellipsis; white-space: nowrap; }
.budget-detail { flex: none; color: var(--color-text-secondary); font-size: 22rpx; }
.track { height: 10rpx; margin-top: 12rpx; overflow: hidden; border-radius: var(--radius-pill); background: var(--color-surface-muted); }
.fill { height: 100%; border-radius: var(--radius-pill); background: var(--color-primary); transition: width var(--transition-standard); }
.fill.warning { background: var(--color-warning); }
.fill.blocked { background: var(--color-danger); }
.insight-card { gap: 18rpx; margin-top: 14rpx; padding: 26rpx 28rpx; }
.insight-icon { display: flex; width: 68rpx; height: 68rpx; flex: none; align-items: center; justify-content: center; border-radius: 22rpx; background: var(--color-accent-soft); }
.insight-copy { display: flex; min-width: 0; flex: 1; flex-direction: column; }
.text-button { width: auto; height: var(--button-height-sm); margin: 0; padding: 0 8rpx; border: 0; color: var(--color-primary); background: transparent; font-size: var(--button-font-sm); font-weight: 600; line-height: var(--button-height-sm); }
.bill-row { min-height: 96rpx; border-bottom: 1rpx solid var(--color-border-muted); }
.bill-row:last-of-type { border-bottom: 0; }
.category-mark { display: flex; align-items: center; justify-content: center; width: 58rpx; height: 58rpx; flex: none; border-radius: 20rpx; color: var(--color-primary); background: var(--color-primary-soft); font-weight: 600; }
.bill-copy { display: flex; min-width: 0; flex: 1; margin-left: 16rpx; flex-direction: column; }
.bill-category { overflow: hidden; font-size: 26rpx; text-overflow: ellipsis; white-space: nowrap; }
.bill-note { margin-top: 6rpx; overflow: hidden; color: var(--color-text-secondary); font-size: 22rpx; text-overflow: ellipsis; white-space: nowrap; }
.bill-amount { max-width: 220rpx; margin-left: 16rpx; overflow: hidden; color: var(--color-text); font-size: 26rpx; font-weight: 600; text-overflow: ellipsis; white-space: nowrap; }
.bill-amount.expense { color: var(--color-danger); }
.bill-amount.income { color: var(--color-success); }
.empty-state { display: flex; min-height: 150rpx; flex-direction: column; align-items: center; justify-content: center; color: var(--color-text-secondary); font-size: 24rpx; }
.empty-state.compact { min-height: 140rpx; }
.empty-icon { display: flex; align-items: center; justify-content: center; width: 72rpx; height: 72rpx; margin-bottom: 14rpx; border-radius: 24rpx; background: var(--color-surface-muted); }
@keyframes card-enter { from { opacity: 0; transform: translateY(12rpx); } to { opacity: 1; transform: translateY(0); } }
</style>

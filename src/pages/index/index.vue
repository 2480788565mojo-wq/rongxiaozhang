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
        <text class="asset-note">所有账户余额</text>
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
        <button class="quick-item card" @click="go('/pages/insights/index')">
          <view class="quick-icon violet"><u-icon name="chat" color="#7D6EE8" size="22" /></view>
          <text>洞察</text>
        </button>
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

      <view class="insight-card card" @click="go('/pages/insights/index')">
        <view class="insight-icon"><u-icon name="chat" color="#7D6EE8" size="24" /></view>
        <view class="insight-copy">
          <text class="section-title">AI 消费洞察</text>
          <text class="section-subtitle">查看你的本月消费分析</text>
        </view>
        <u-icon name="arrow-right" color="#C7C7CC" size="18" />
      </view>

      <view class="section card recent-card">
        <view class="section-head">
          <view>
            <text class="section-title">最近记录</text>
            <text class="section-subtitle">本月最新账单</text>
          </view>
          <button class="text-button" @click.stop="openBills">查看全部</button>
        </view>
        <view v-for="bill in recentBills" :key="bill.id" class="bill-row" @click="openBill(bill.id)">
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
      </view>
    </template>
    <FabBtn />
  </view>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from "vue";
import { onShow } from "@dcloudio/uni-app";
import FabBtn from "@/components/FabBtn.vue";
import { getOverview } from "@/api/stats";
import { useBillStore } from "@/stores/bill";
import { useBudgetStore } from "@/stores/budget";
import { useLedgerStore } from "@/stores/ledger";
import { useUserStore } from "@/stores/user";
import { useAccountStore } from "@/stores/account";

const userStore = useUserStore();
const ledgerStore = useLedgerStore();
const billStore = useBillStore();
const budgetStore = useBudgetStore();
const accountStore = useAccountStore();
const year = ref(0);
const month = ref(0);
const overview = reactive({ expense: 0, income: 0, balance: 0 });
const recentBills = computed(() => billStore.bills.slice(0, 5));

function syncCurrentPeriod() {
  const now = new Date();
  year.value = now.getFullYear();
  month.value = now.getMonth() + 1;
}

async function login() {
  await userStore.login();
  await load();
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
  } else {
    overview.expense = 0;
    overview.income = 0;
    overview.balance = 0;
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
function openBill(id: number) { uni.navigateTo({ url: `/pages/bills/detail?id=${id}` }); }
</script>

<style scoped>
.page { min-height: 100vh; padding: 24rpx 32rpx 160rpx; box-sizing: border-box; }
.card { border-radius: var(--radius-lg); background: var(--color-surface); box-shadow: var(--shadow-sm); }
.topbar, .brand, .ledger-chip, .asset-header, .section-head, .budget-copy, .insight-card, .bill-row { display: flex; align-items: center; }
.topbar, .asset-header, .section-head, .budget-copy { justify-content: space-between; }
.brand { min-width: 0; gap: 16rpx; }
.brand-logo { width: 72rpx; height: 72rpx; flex: none; border-radius: 20rpx; }
.brand-copy { display: flex; min-width: 0; flex-direction: column; }
.brand-name { color: var(--color-text); font-size: 34rpx; font-weight: 700; }
.brand-greeting { margin-top: 4rpx; color: var(--color-text-secondary); font-size: 23rpx; }
.ledger-chip { max-width: 230rpx; gap: 8rpx; padding: 12rpx 18rpx; border-radius: var(--radius-pill); color: var(--color-primary); background: var(--color-primary-soft); font-size: 23rpx; }
.ledger-chip text { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.login-card { display: flex; align-items: center; justify-content: space-between; gap: 24rpx; margin-top: 32rpx; padding: 32rpx; }
.login-copy { display: flex; min-width: 0; flex: 1; flex-direction: column; }
.login-title { font-size: 34rpx; font-weight: 600; }
.login-subtitle { margin-top: 8rpx; color: var(--color-text-secondary); font-size: 24rpx; }
.primary-button { width: 184rpx; height: 72rpx; margin: 0; border-radius: var(--radius-pill); color: #fff; background: var(--color-primary); font-size: 26rpx; line-height: 72rpx; }
.asset-card { margin-top: 32rpx; padding: 36rpx 36rpx 40rpx; animation: card-enter var(--transition-standard) both; }
.asset-header > view:first-child { display: flex; flex-direction: column; }
.eyebrow { color: var(--color-text-secondary); font-size: 26rpx; }
.period { margin-top: 6rpx; color: var(--color-text-secondary); font-size: 22rpx; }
.asset-icon { display: flex; align-items: center; justify-content: center; width: 72rpx; height: 72rpx; border-radius: 24rpx; background: var(--color-primary-soft); }
.asset-value { display: block; margin-top: 28rpx; overflow: hidden; color: var(--color-text); font-size: 62rpx; font-weight: 700; line-height: 1.2; text-overflow: ellipsis; white-space: nowrap; }
.asset-note { display: block; margin-top: 10rpx; color: var(--color-text-secondary); font-size: 24rpx; }
.summary-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16rpx; margin-top: 16rpx; }
.metric-card { display: flex; min-width: 0; min-height: 128rpx; padding: 24rpx 18rpx; box-sizing: border-box; flex-direction: column; justify-content: space-between; animation: card-enter var(--transition-standard) both; }
.metric-label { color: var(--color-text-secondary); font-size: 22rpx; }
.metric-value { display: block; overflow: hidden; margin-top: 16rpx; color: var(--color-text); font-size: 25rpx; font-weight: 700; text-overflow: ellipsis; white-space: nowrap; }
.metric-card.expense .metric-value { color: var(--color-danger); }
.metric-card.income .metric-value { color: var(--color-success); }
.metric-card.balance .metric-value { color: var(--color-primary); }
.quick-links { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 16rpx; margin-top: 16rpx; }
.quick-item { display: flex; min-width: 0; height: 142rpx; margin: 0; padding: 18rpx 8rpx; flex-direction: column; align-items: center; justify-content: center; color: var(--color-text); font-size: 24rpx; line-height: 1; }
.quick-icon { display: flex; align-items: center; justify-content: center; width: 64rpx; height: 64rpx; margin-bottom: 14rpx; border-radius: 22rpx; }
.quick-icon.blue { background: var(--color-primary-soft); }
.quick-icon.green { background: #eaf8ee; }
.quick-icon.orange { background: #fff4df; }
.quick-icon.violet { background: var(--color-accent-soft); }
.section { margin-top: 16rpx; padding: 32rpx; }
.section-head { margin-bottom: 24rpx; }
.section-head > view { display: flex; min-width: 0; flex-direction: column; }
.section-title { color: var(--color-text); font-size: 32rpx; font-weight: 600; }
.section-subtitle { margin-top: 6rpx; color: var(--color-text-secondary); font-size: 23rpx; }
.budget-row + .budget-row { margin-top: 24rpx; }
.budget-copy { gap: 20rpx; }
.budget-name { overflow: hidden; font-size: 27rpx; text-overflow: ellipsis; white-space: nowrap; }
.budget-detail { flex: none; color: var(--color-text-secondary); font-size: 22rpx; }
.track { height: 12rpx; margin-top: 14rpx; overflow: hidden; border-radius: var(--radius-pill); background: var(--color-surface-muted); }
.fill { height: 100%; border-radius: var(--radius-pill); background: var(--color-primary); transition: width var(--transition-standard); }
.fill.warning { background: var(--color-warning); }
.fill.blocked { background: var(--color-danger); }
.insight-card { gap: 20rpx; margin-top: 16rpx; padding: 28rpx 32rpx; }
.insight-icon { display: flex; width: 72rpx; height: 72rpx; flex: none; align-items: center; justify-content: center; border-radius: 24rpx; background: var(--color-accent-soft); }
.insight-copy { display: flex; min-width: 0; flex: 1; flex-direction: column; }
.text-button { width: auto; height: 56rpx; margin: 0; padding: 0 4rpx; color: var(--color-primary); background: transparent; font-size: 24rpx; line-height: 56rpx; }
.bill-row { min-height: 104rpx; border-bottom: 1rpx solid var(--color-border-muted); }
.bill-row:last-of-type { border-bottom: 0; }
.category-mark { display: flex; align-items: center; justify-content: center; width: 64rpx; height: 64rpx; flex: none; border-radius: 22rpx; color: var(--color-primary); background: var(--color-primary-soft); font-weight: 600; }
.bill-copy { display: flex; min-width: 0; flex: 1; margin-left: 18rpx; flex-direction: column; }
.bill-category { overflow: hidden; font-size: 27rpx; text-overflow: ellipsis; white-space: nowrap; }
.bill-note { margin-top: 6rpx; overflow: hidden; color: var(--color-text-secondary); font-size: 22rpx; text-overflow: ellipsis; white-space: nowrap; }
.bill-amount { max-width: 220rpx; margin-left: 16rpx; overflow: hidden; color: var(--color-text); font-size: 27rpx; font-weight: 600; text-overflow: ellipsis; white-space: nowrap; }
.bill-amount.expense { color: var(--color-danger); }
.bill-amount.income { color: var(--color-success); }
.empty-state { display: flex; min-height: 150rpx; flex-direction: column; align-items: center; justify-content: center; color: var(--color-text-secondary); font-size: 24rpx; }
.empty-state.compact { min-height: 140rpx; }
.empty-icon { display: flex; align-items: center; justify-content: center; width: 72rpx; height: 72rpx; margin-bottom: 14rpx; border-radius: 24rpx; background: var(--color-surface-muted); }
@keyframes card-enter { from { opacity: 0; transform: translateY(12rpx); } to { opacity: 1; transform: translateY(0); } }
</style>

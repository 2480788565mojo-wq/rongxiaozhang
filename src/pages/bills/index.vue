<template>
  <view class="page">
    <view class="filters">
      <picker mode="date" fields="month" :value="monthValue" @change="changeMonth">
        <view class="filter-button">{{ year }}年{{ month }}月</view>
      </picker>
      <picker :range="categoryOptions" @change="changeCategory">
        <view class="filter-button">{{ selectedCategory || "全部分类" }}</view>
      </picker>
    </view>
    <view class="totals"><text>支出 ¥{{ totalExpense.toFixed(2) }}</text><text>收入 ¥{{ totalIncome.toFixed(2) }}</text></view>
    <view v-for="group in groups" :key="group.date" class="date-group">
      <view class="date-head"><text>{{ group.date }}</text><text>支 {{ group.expense.toFixed(2) }} · 收 {{ group.income.toFixed(2) }}</text></view>
      <view v-for="bill in group.items" :key="bill.id" class="bill" @click="openBill(bill.id)">
        <view class="mark">{{ bill.category.slice(0, 1) }}</view>
        <view class="copy"><text>{{ bill.category }}</text><text>{{ bill.note || bill.account || "无备注" }}</text></view>
        <text class="amount" :class="bill.type">{{ bill.type === "expense" ? "-" : "+" }}¥{{ bill.amount.toFixed(2) }}</text>
      </view>
    </view>
    <view v-if="!groups.length" class="empty">该月份暂无账单</view>
    <FabBtn />
  </view>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { onShow } from "@dcloudio/uni-app";
import FabBtn from "@/components/FabBtn.vue";
import { useBillStore } from "@/stores/bill";
import { useLedgerStore } from "@/stores/ledger";
import type { Bill } from "@/types";

const billStore = useBillStore();
const ledgerStore = useLedgerStore();
const now = new Date();
const year = ref(now.getFullYear());
const month = ref(now.getMonth() + 1);
const selectedCategory = ref("");
const monthValue = computed(() => `${year.value}-${String(month.value).padStart(2, "0")}`);
const categoryOptions = computed(() => ["全部分类", ...Array.from(new Set(billStore.bills.map((item) => item.category)))]);
const totalExpense = computed(() => billStore.bills.filter((item) => item.type === "expense").reduce((sum, item) => sum + item.amount, 0));
const totalIncome = computed(() => billStore.bills.filter((item) => item.type === "income").reduce((sum, item) => sum + item.amount, 0));
const groups = computed(() => {
  const map = new Map<string, Bill[]>();
  billStore.bills.forEach((bill) => map.set(bill.bill_date, [...(map.get(bill.bill_date) || []), bill]));
  return Array.from(map.entries()).map(([date, items]) => ({
    date,
    items,
    expense: items.filter((item) => item.type === "expense").reduce((sum, item) => sum + item.amount, 0),
    income: items.filter((item) => item.type === "income").reduce((sum, item) => sum + item.amount, 0),
  })).sort((a, b) => b.date.localeCompare(a.date));
});

async function load() {
  if (!ledgerStore.currentId) await ledgerStore.fetchLedgers();
  if (ledgerStore.currentId) await billStore.fetchBills(ledgerStore.currentId, true, { year: year.value, month: month.value, category: selectedCategory.value || undefined });
}
onShow(() => void load());
function changeMonth(event: any) { const [y, m] = event.detail.value.split("-").map(Number); year.value = y; month.value = m; void load(); }
function changeCategory(event: any) { const value = categoryOptions.value[Number(event.detail.value)]; selectedCategory.value = value === "全部分类" ? "" : value; void load(); }
function openBill(id: number) { uni.navigateTo({ url: `/pages/bills/detail?id=${id}` }); }
</script>

<style scoped>
.page { min-height: 100vh; padding: 24rpx 28rpx 150rpx; box-sizing: border-box; }
.filters, .totals, .date-head, .bill { display: flex; align-items: center; justify-content: space-between; }
.filters { gap: 16rpx; padding: 8rpx; border-radius: var(--radius-lg); background: var(--color-surface); box-shadow: var(--shadow-sm); }
.filters picker { min-width: 0; flex: 1; }
.filter-button { padding: 18rpx 12rpx; border-radius: 24rpx; color: var(--color-primary); background: var(--color-primary-soft); font-size: 25rpx; text-align: center; }
.totals { margin-top: 16rpx; padding: 24rpx 28rpx; border-radius: var(--radius-lg); color: var(--color-text-secondary); background: var(--color-surface); box-shadow: var(--shadow-sm); font-size: 24rpx; }
.totals text:first-child { color: var(--color-danger); }
.totals text:last-child { color: var(--color-success); }
.date-group { margin-top: 18rpx; overflow: hidden; border-radius: var(--radius-lg); background: var(--color-surface); box-shadow: var(--shadow-sm); }
.date-head { padding: 22rpx 24rpx 12rpx; color: var(--color-text-secondary); font-size: 23rpx; }
.bill { min-height: 104rpx; padding: 0 24rpx; border-bottom: 1rpx solid var(--color-border-muted); }
.bill:last-child { border-bottom: 0; }
.mark { display: flex; align-items: center; justify-content: center; width: 60rpx; height: 60rpx; border-radius: 20rpx; color: var(--color-primary); background: var(--color-primary-soft); font-weight: 600; }
.copy { display: flex; flex: 1; min-width: 0; flex-direction: column; margin-left: 18rpx; }
.copy text:last-child { margin-top: 5rpx; overflow: hidden; color: var(--color-text-secondary); font-size: 22rpx; text-overflow: ellipsis; white-space: nowrap; }
.amount { max-width: 220rpx; overflow: hidden; font-family: var(--font-mono); font-weight: 600; text-overflow: ellipsis; white-space: nowrap; }
.amount.expense { color: var(--color-danger); }
.amount.income { color: var(--color-success); }
.empty { margin-top: 18rpx; padding: 120rpx 24rpx; border-radius: var(--radius-lg); color: var(--color-text-secondary); background: var(--color-surface); text-align: center; }
</style>

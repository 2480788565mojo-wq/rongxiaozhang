<template>
  <view class="page">
    <button class="import-button" @click="openImport">导入 Excel 账单</button>
    <view class="filters">
      <picker mode="date" fields="month" :value="monthValue" @change="changeMonth">
        <view class="filter-button">{{ year }}年{{ month }}月</view>
      </picker>
      <picker :range="categoryOptions" @change="changeCategory">
        <view class="filter-button">{{ selectedCategory || "全部分类" }}</view>
      </picker>
    </view>
    <text v-if="billStore.total" class="count-hint">已显示 {{ billStore.bills.length }} / {{ billStore.total }} 笔{{ billStore.bills.length < billStore.total ? '，下方合计仅包含已显示的账单' : '' }}</text>
    <view class="totals"><text>支出 ¥{{ totalExpense.toFixed(2) }}</text><text>收入 ¥{{ totalIncome.toFixed(2) }}</text></view>
    <view v-for="group in groups" :key="group.date" class="date-group">
      <view class="date-head" role="button" :aria-expanded="!!expandedDates[group.date]" hover-class="pressable" @click="toggleDate(group.date)">
        <view class="date-summary"><text class="date-title">{{ group.date }} · {{ group.items.length }} 笔</text><text>支出 ¥{{ group.expense.toFixed(2) }} · 收入 ¥{{ group.income.toFixed(2) }}</text></view>
        <view class="date-action"><text>{{ expandedDates[group.date] ? '收起' : '展开' }}</text><u-icon :name="expandedDates[group.date] ? 'arrow-up' : 'arrow-down'" color="#86868B" size="14" /></view>
      </view>
      <view v-if="expandedDates[group.date]" class="date-content">
      <view v-for="bill in group.items" :key="bill.id" class="bill" hover-class="pressable" @click="openBill(bill.id)" @longpress="onDelete(bill.id)">
        <view class="mark">{{ bill.category.slice(0, 1) }}</view>
        <view class="copy"><text>{{ bill.category }}</text><text>{{ bill.note || bill.account || "无备注" }}</text></view>
        <view class="bill-right">
          <text class="amount" :class="bill.type">{{ bill.type === "expense" ? "-" : "+" }}¥{{ bill.amount.toFixed(2) }}</text>
          <view class="bill-actions">
            <button class="edit-bill" @click.stop="editBill(bill.id)">修改</button>
            <button class="delete-bill" :disabled="deletingId !== null" @click.stop="onDelete(bill.id)">删除</button>
          </view>
        </view>
      </view>
      </view>
    </view>
    <view v-if="!groups.length" class="empty">该月份暂无账单</view>
    <button v-if="billStore.bills.length < billStore.total" class="load-more" :loading="billStore.loading" :disabled="billStore.loading" @click="loadMore">加载更多</button>
    <FabBtn />
    <BudgetAlert />
</view>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { onShow, onReachBottom } from "@dcloudio/uni-app";
import BudgetAlert from "@/components/BudgetAlert.vue";
import FabBtn from "@/components/FabBtn.vue";
import { deleteBill } from "@/api/bills";
import { useBillStore } from "@/stores/bill";
import { useLedgerStore } from "@/stores/ledger";
import type { Bill } from "@/types";

const billStore = useBillStore();
const ledgerStore = useLedgerStore();
const now = new Date();
const year = ref(now.getFullYear());
const month = ref(now.getMonth() + 1);
const selectedCategory = ref("");
const deletingId = ref<number | null>(null);
const expandedDates = ref<Record<string, boolean>>({});
function toggleDate(date: string) { expandedDates.value[date] = !expandedDates.value[date]; }
// 换账本或筛选条件后从收起状态查看新结果；加载更多保留已经展开的日期。
watch([() => ledgerStore.currentId, year, month, selectedCategory], () => { expandedDates.value = {}; });
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

function filters() { return { year: year.value, month: month.value, category: selectedCategory.value || undefined }; }
async function load() {
  try {
    if (!ledgerStore.currentId) await ledgerStore.fetchLedgers();
    if (ledgerStore.currentId) await billStore.fetchBills(ledgerStore.currentId, true, filters());
  } catch (error) { uni.showToast({ title: error instanceof Error ? error.message : '账单加载失败', icon: 'none' }); }
}
async function loadMore() {
  if (billStore.loading || !ledgerStore.currentId || billStore.bills.length >= billStore.total) return;
  const pageBefore = billStore.page;
  billStore.page += 1;
  try {
    await billStore.fetchBills(ledgerStore.currentId, false, filters());
  } catch (error) {
    // 只有当前请求对应的页码还生效时才回退；切换筛选已重置 page 时不能减到 0。
    if (billStore.page === pageBefore + 1) billStore.page -= 1;
    uni.showToast({ title: error instanceof Error ? error.message : '加载失败，请重试', icon: 'none' });
  }
}
onShow(() => void load());
onReachBottom(() => void loadMore());
function changeMonth(event: any) { const [y, m] = event.detail.value.split("-").map(Number); year.value = y; month.value = m; void load(); }
function changeCategory(event: any) { const value = categoryOptions.value[Number(event.detail.value)]; selectedCategory.value = value === "全部分类" ? "" : value; void load(); }
function openImport() { uni.navigateTo({ url: "/subpackages/import/index" }); }
function openBill(id: number) { uni.navigateTo({ url: `/pages/bills/detail?id=${id}` }); }
function editBill(id: number) { uni.navigateTo({ url: `/pages/add/index?id=${id}` }); }
async function onDelete(id: number) {
  if (deletingId.value !== null) return;
  deletingId.value = id;
  try {
  const res = await uni.showModal({ title: "确认删除", content: "确定要删除这笔账单吗？删除后无法恢复。", confirmText: "删除", confirmColor: "#E53935" });
  if (!res.confirm) return;
    await deleteBill(id);
    billStore.remove(id);
    uni.showToast({ title: "已删除", icon: "success" });
  } catch (error) {
    uni.showToast({ title: error instanceof Error ? error.message : "删除失败", icon: "none" });
  } finally { deletingId.value = null; }
}
</script>

<style scoped>
.page { position: relative; z-index: 1; min-height: 100vh; padding: 24rpx 28rpx 150rpx; box-sizing: border-box; }
.filters, .totals, .date-head, .bill { display: flex; align-items: center; justify-content: space-between; }
.filters { gap: 12rpx; padding: 8rpx; border-radius: var(--radius-lg); background: var(--color-surface); box-shadow: var(--shadow-sm); }
.filters picker { min-width: 0; flex: 1; }
.filter-button { height: var(--button-height-md); padding: 0 12rpx; box-sizing: border-box; border: 1rpx solid #e3eefb; border-radius: 20rpx; color: var(--color-primary); background: var(--color-surface); font-size: var(--button-font-md); font-weight: 600; line-height: var(--button-height-md); text-align: center; }
.totals { margin-top: 14rpx; padding: 22rpx 26rpx; border-radius: var(--radius-lg); color: var(--color-text-secondary); background: var(--color-surface); box-shadow: var(--shadow-sm); font-size: 22rpx; }
.totals text:first-child { color: var(--color-danger); }
.totals text:last-child { color: var(--color-success); }
.date-group { margin-top: 14rpx; overflow: hidden; border: 1rpx solid #eef3fa; border-radius: var(--radius-lg); background: var(--color-surface); box-shadow: var(--shadow-sm); }
.date-head { padding: 22rpx; gap: 18rpx; color: var(--color-text-secondary); background: linear-gradient(180deg, #ffffff, #fbfdff); font-size: 22rpx; }
.date-summary { display: flex; min-width: 0; flex: 1; flex-direction: column; gap: 8rpx; overflow-wrap: anywhere; }
.date-title { color: var(--color-text); font-size: 26rpx; font-weight: 600; }
.date-title::before { content: ""; display: inline-block; width: 8rpx; height: 8rpx; margin-right: 8rpx; border-radius: 50%; background: var(--color-primary); vertical-align: middle; }
.date-action { display: flex; flex: none; align-items: center; gap: 10rpx; font-size: 23rpx; }
.bill { min-height: 100rpx; padding: 0 22rpx; border-bottom: 1rpx solid var(--color-border-muted); }
.bill:last-child { border-bottom: 0; }
.mark { display: flex; align-items: center; justify-content: center; width: 58rpx; height: 58rpx; border-radius: 20rpx; color: var(--color-primary); background: var(--color-primary-soft); font-weight: 600; }
.copy { display: flex; flex: 1; min-width: 0; flex-direction: column; margin-left: 16rpx; }
.copy text:last-child { margin-top: 5rpx; overflow: hidden; color: var(--color-text-secondary); font-size: 22rpx; text-overflow: ellipsis; white-space: nowrap; }
.amount { max-width: 220rpx; overflow: hidden; font-family: var(--font-mono); font-size: 26rpx; font-weight: 600; text-overflow: ellipsis; white-space: nowrap; }
.amount.expense { color: var(--color-danger); }
.amount.income { color: var(--color-success); }
.empty { margin-top: 14rpx; padding: 100rpx 24rpx; border-radius: var(--radius-lg); color: var(--color-text-secondary); background: var(--color-surface); box-shadow: var(--shadow-sm); font-size: 24rpx; line-height: 1.6; text-align: center; }
.bill-right { display: flex; align-items: flex-end; flex-direction: column; padding: 14rpx 0; gap: 8rpx; }
.bill-actions { display: flex; gap: 12rpx; }
.bill-actions button { height: var(--button-height-sm); margin: 0; padding: 0 16rpx; border: 0; border-radius: 16rpx; font-size: var(--button-font-sm); font-weight: 600; line-height: var(--button-height-sm); }
.edit-bill { color: var(--color-primary); background: var(--color-primary-soft); }
.delete-bill { color: var(--color-danger); background: #fff0ef; }
.import-button { width: 100%; height: var(--button-height-md); margin: 0 0 18rpx; box-sizing: border-box; border: 1rpx solid #e3eefb; color: var(--color-primary); background: var(--color-surface); border-radius: var(--radius-pill); font-size: var(--button-font-md); font-weight: 600; line-height: var(--button-height-md); }
.count-hint { display: block; margin: 18rpx 0 0; font-size: 22rpx; color: var(--color-text-secondary); }
.load-more { width: 100%; height: var(--button-height-md); margin-top: 22rpx; border: 0; color: var(--color-primary); background: var(--color-primary-soft); border-radius: var(--radius-pill); font-size: var(--button-font-md); font-weight: 600; line-height: var(--button-height-md); }
</style>

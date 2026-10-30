<template>
  <view class="page">
    <view class="month-head"><text class="title">{{ year }}年{{ month }}月预算</text><text>{{ ledgerStore.current?.name }}</text></view>
    <view v-if="loadError" class="load-error">
      <text>{{ loadError }}</text>
      <button class="retry-load" @click="load">重新加载</button>
    </view>
    <view class="gauge"><BudgetGauge :statuses="budgetStore.statuses" /></view>
    <label class="total-row"><text>总预算</text><input v-model.number="totalBudget" type="digit" placeholder="0.00" /></label>
    <view class="category-list">
      <view v-for="category in budgetCategories" :key="category" class="category-row">
        <view><text>{{ category }}</text><text v-if="statusMap[category]">已花 ¥{{ statusMap[category].spent.toFixed(2) }}</text></view>
        <input v-model.number="categoryBudgets[category]" type="digit" placeholder="未设置" />
      </view>
    </view>
    <button class="save" :loading="saving" @click="save">保存预算</button>
</view>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from "vue";
import { onShow } from "@dcloudio/uni-app";
import BudgetGauge from "@/components/charts/BudgetGauge.vue";
import { CATEGORY_PRESETS } from "@/constants/categories";
import { getBudget } from "@/api/budgets";
import { useBudgetStore } from "@/stores/budget";
import { useCategoryStore } from "@/stores/category";
import { useLedgerStore } from "@/stores/ledger";

const ledgerStore = useLedgerStore();
const budgetStore = useBudgetStore();
const categoryStore = useCategoryStore();
const year = ref(0);
const month = ref(0);
type BudgetInput = number | string | null | undefined;

const totalBudget = ref<BudgetInput>(null);
const categoryBudgets = reactive<Record<string, BudgetInput>>({});
const saving = ref(false);
const loadError = ref("");
let loadVersion = 0;
const presets = Object.keys(CATEGORY_PRESETS.expense);
const budgetCategories = computed(() => Array.from(new Set([...presets, ...categoryStore.categories.filter((item) => item.type === "expense" && !item.parent_name).map((item) => item.name)])));
const statusMap = computed(() => Object.fromEntries(budgetStore.statuses.map((item) => [item.category, item])));

function currentPeriod() {
  const now = new Date();
  return { year: now.getFullYear(), month: now.getMonth() + 1 };
}

function normalizeBudget(value: BudgetInput): number | null | undefined {
  if (value === "" || value === null || value === undefined) return null;
  const amount = Number(value);
  if (!Number.isFinite(amount) || amount < 0) return undefined;
  return amount;
}

async function load() {
  const version = ++loadVersion;
  loadError.value = "";
  const period = currentPeriod();
  year.value = period.year;
  month.value = period.month;
  // 先清空旧月份，接口失败时不会把上个月的数据当成这个月展示。
  totalBudget.value = null;
  Object.keys(categoryBudgets).forEach((key) => delete categoryBudgets[key]);
  try {
    if (!ledgerStore.currentId) await ledgerStore.fetchLedgers();
    if (!ledgerStore.currentId) {
      loadError.value = "请先创建或加入账本";
      return;
    }
    await Promise.all([
      categoryStore.fetchCategories(ledgerStore.currentId),
      budgetStore.fetchStatuses(ledgerStore.currentId, year.value, month.value),
    ]);
    const data = await getBudget(ledgerStore.currentId, year.value, month.value);
    if (version !== loadVersion) return;
    totalBudget.value = data?.total_budget ?? null;
    Object.assign(categoryBudgets, data?.category_budgets || {});
  } catch (error) {
    if (version !== loadVersion) return;
    // 失败时仪表盘也不能继续显示上个月/上个账本的数据。
    budgetStore.statuses = [];
    loadError.value = error instanceof Error ? error.message : "预算加载失败，请重试";
  }
}
onShow(() => void load());

async function save() {
  if (!ledgerStore.currentId) return;
  const period = currentPeriod();
  if (period.year !== year.value || period.month !== month.value) {
    await load();
    uni.showToast({ title: "月份已更新，请确认后再保存", icon: "none" });
    return;
  }
  saving.value = true;
  try {
    const normalizedTotal = normalizeBudget(totalBudget.value);
    if (normalizedTotal === undefined) {
      uni.showToast({ title: "总预算必须是非负数字", icon: "none" });
      return;
    }
    const cleaned: Record<string, number> = {};
    for (const [category, value] of Object.entries(categoryBudgets)) {
      const amount = normalizeBudget(value);
      if (amount === undefined) {
        uni.showToast({ title: `${category}预算格式不正确`, icon: "none" });
        return;
      }
      if (amount !== null) cleaned[category] = amount;
    }
    await budgetStore.save({ ledger_id: ledgerStore.currentId, year: year.value, month: month.value, total_budget: normalizedTotal, category_budgets: cleaned });
    uni.showToast({ title: "预算已保存", icon: "success" });
  } catch (error) {
    uni.showToast({ title: error instanceof Error ? error.message : "预算保存失败，请稍后重试", icon: "none" });
  } finally { saving.value = false; }
}
</script>

<style scoped>
.page { min-height: 100vh; padding: 24rpx 28rpx 80rpx; box-sizing: border-box; }
.month-head { display: flex; align-items: center; justify-content: space-between; }
.title { font-size: 38rpx; font-weight: 600; }
.month-head > text:last-child { color: var(--color-text-secondary); font-size: 22rpx; }
.gauge { margin-top: 18rpx; overflow: hidden; border-radius: var(--radius-lg); background: var(--color-surface); box-shadow: var(--shadow-sm); }
.total-row, .category-row { display: flex; align-items: center; justify-content: space-between; min-height: 92rpx; padding: 0 22rpx; border-bottom: 1rpx solid var(--color-border-muted); background: var(--color-surface); font-size: 26rpx; }
.total-row { margin-top: 16rpx; border: 0; border-radius: var(--radius-lg); box-shadow: var(--shadow-sm); }
.total-row input, .category-row input { width: 210rpx; font-size: 26rpx; text-align: right; }
.category-list { margin-top: 16rpx; overflow: hidden; border-radius: var(--radius-lg); box-shadow: var(--shadow-sm); }
.category-row:last-child { border-bottom: 0; }
.category-row > view { display: flex; flex-direction: column; }
.category-row view text:last-child { margin-top: 5rpx; color: var(--color-text-secondary); font-size: 22rpx; }
.load-error { display: flex; align-items: center; justify-content: space-between; gap: 16rpx; margin-top: 14rpx; padding: 18rpx 22rpx; border-radius: var(--radius-lg); color: var(--color-danger); background: #fff0ef; font-size: 24rpx; }
.retry-load { flex: none; height: var(--button-height-sm); margin: 0; padding: 0 18rpx; border: 0; border-radius: 16rpx; color: var(--color-primary); background: var(--color-surface); font-size: 22rpx; line-height: var(--button-height-sm); }
.save { width: 100%; height: var(--button-height-lg); margin-top: 24rpx; border: 0; color: #fff; background: var(--color-primary); border-radius: var(--radius-pill); font-size: var(--button-font-lg); font-weight: 600; line-height: var(--button-height-lg); }
</style>

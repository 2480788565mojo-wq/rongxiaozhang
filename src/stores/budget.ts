import { computed, ref } from "vue";
import { defineStore } from "pinia";
import * as budgetApi from "@/api/budgets";
import type { BudgetAlertData, BudgetStatus } from "@/types";

export const useBudgetStore = defineStore("budget", () => {
  const statuses = ref<BudgetStatus[]>([]);
  const alertVisible = ref(false);
  const alertData = ref<BudgetAlertData | null>(null);
  const alertAction = ref<((confirmed: boolean) => void) | null>(null);
  const hasAlertAction = computed(() => Boolean(alertAction.value));
  const loading = ref(false);

  async function fetchStatuses(ledgerId: number, year?: number, month?: number) {
    loading.value = true;
    try {
      const response = await budgetApi.getBudgetStatus(ledgerId, year, month);
      statuses.value = response.statuses;
      return statuses.value;
    } finally {
      loading.value = false;
    }
  }

  async function save(data: budgetApi.BudgetPayload) {
    await budgetApi.setBudget(data);
    return fetchStatuses(data.ledger_id, data.year, data.month);
  }

  function showAlert(
    data: BudgetAlertData,
    onResolve?: (confirmed: boolean) => void,
  ) {
    alertData.value = data;
    // SSE 告警可能晚于 409 到达；已有 pending resolver 时只更新展示数据，
    // 绝不能把它覆盖成 null，否则 saveBills 会永远等待。
    if (!alertVisible.value) {
      alertAction.value = onResolve ?? null;
    } else if (!alertAction.value) {
      alertAction.value = onResolve ?? null;
    }
    alertVisible.value = true;
  }

  function settleAlert(confirmed: boolean) {
    const action = alertAction.value;
    alertAction.value = null;
    alertVisible.value = false;
    action?.(confirmed);
  }

  function confirmAlert() {
    settleAlert(true);
  }

  function cancelAlert() {
    settleAlert(false);
  }

  function dismissAlert() {
    settleAlert(false);
  }

  function clear() {
    settleAlert(false);
    statuses.value = [];
    alertData.value = null;
    loading.value = false;
  }

  return {
    statuses,
    alertVisible,
    alertData,
    hasAlertAction,
    loading,
    fetchStatuses,
    save,
    showAlert,
    confirmAlert,
    cancelAlert,
    dismissAlert,
    clear,
  };
});

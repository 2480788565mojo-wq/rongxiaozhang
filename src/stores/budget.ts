import { ref } from "vue";
import { defineStore } from "pinia";
import * as budgetApi from "@/api/budgets";
import type { BudgetAlertData, BudgetStatus } from "@/types";

export const useBudgetStore = defineStore("budget", () => {
  const statuses = ref<BudgetStatus[]>([]);
  const alertVisible = ref(false);
  const alertData = ref<BudgetAlertData | null>(null);
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

  function showAlert(data: BudgetAlertData) {
    alertData.value = data;
    alertVisible.value = true;
    const blocked = data.risk_level === "blocked";
    const percentage = data.percentage ?? 0;
    const category = data.category ? `${data.category}：` : "";
    const details = `${category}已花 ¥${(data.spent ?? 0).toFixed(2)} / ¥${(data.budget ?? 0).toFixed(2)}`;
    uni.showModal({
      title: blocked ? "预算已超限" : "预算提醒",
      content: `${blocked ? "本月该分类预算已用尽" : `预算已使用 ${percentage}%`}\n${details}`,
      showCancel: false,
      confirmText: "知道了",
      complete: dismissAlert,
    });
  }

  function dismissAlert() {
    alertVisible.value = false;
  }

  function clear() {
    statuses.value = [];
    alertVisible.value = false;
    alertData.value = null;
    loading.value = false;
  }

  return {
    statuses,
    alertVisible,
    alertData,
    loading,
    fetchStatuses,
    save,
    showAlert,
    dismissAlert,
    clear,
  };
});

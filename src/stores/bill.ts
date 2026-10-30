import { ref } from "vue";
import { defineStore } from "pinia";
import * as billApi from "@/api/bills";
import type { Bill } from "@/types";

export const useBillStore = defineStore("bill", () => {
  const bills = ref<Bill[]>([]);
  const total = ref(0);
  const page = ref(1);
  const loading = ref(false);
  let requestVersion = 0;

  async function fetchBills(
    ledgerId: number,
    reset = true,
    filters: { year?: number; month?: number; category?: string } = {},
  ) {
    const version = ++requestVersion;
    const pageToFetch = reset ? 1 : page.value;
    if (reset) page.value = 1;
    loading.value = true;
    try {
      const response = await billApi.getBills({
        ledger_id: ledgerId,
        page: pageToFetch,
        page_size: 20,
        ...filters,
      });
      // 切换月份/分类后，旧筛选的迟到响应不能覆盖或追加到新列表。
      if (version !== requestVersion) return [];
      bills.value = reset ? response.items : [...bills.value, ...response.items];
      total.value = response.total;
      return response.items;
    } finally {
      if (version === requestVersion) loading.value = false;
    }
  }

  function prepend(bill: Bill) {
    const exists = bills.value.some((item) => item.id === bill.id);
    bills.value = [bill, ...bills.value.filter((item) => item.id !== bill.id)];
    if (!exists) total.value += 1;
  }

  function remove(id: number) {
    bills.value = bills.value.filter((bill) => bill.id !== id);
    total.value = Math.max(0, total.value - 1);
  }

  function clear() {
    // 让退出/切换账号前发出的请求失效，避免旧账号账单回填。
    requestVersion += 1;
    bills.value = [];
    total.value = 0;
    page.value = 1;
    loading.value = false;
  }

  return { bills, total, page, loading, fetchBills, prepend, remove, clear };
});

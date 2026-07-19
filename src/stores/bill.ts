import { ref } from "vue";
import { defineStore } from "pinia";
import * as billApi from "@/api/bills";
import type { Bill } from "@/types";

export const useBillStore = defineStore("bill", () => {
  const bills = ref<Bill[]>([]);
  const total = ref(0);
  const page = ref(1);
  const loading = ref(false);

  async function fetchBills(
    ledgerId: number,
    reset = true,
    filters: { year?: number; month?: number; category?: string } = {},
  ) {
    if (reset) page.value = 1;
    loading.value = true;
    try {
      const response = await billApi.getBills({
        ledger_id: ledgerId,
        page: page.value,
        page_size: 20,
        ...filters,
      });
      bills.value = reset ? response.items : [...bills.value, ...response.items];
      total.value = response.total;
      return response.items;
    } finally {
      loading.value = false;
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
    bills.value = [];
    total.value = 0;
    page.value = 1;
    loading.value = false;
  }

  return { bills, total, page, loading, fetchBills, prepend, remove, clear };
});

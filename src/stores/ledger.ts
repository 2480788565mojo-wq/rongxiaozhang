import { computed, ref } from "vue";
import { defineStore } from "pinia";
import * as ledgerApi from "@/api/ledgers";
import type { Ledger, LedgerType } from "@/types";

const CURRENT_LEDGER_KEY = "rxz_current_ledger_id";

export const useLedgerStore = defineStore("ledger", () => {
  const ledgers = ref<Ledger[]>([]);
  // 缓存编号只能作为刷新账本列表后的优先选择，不能直接当作已授权账本使用。
  let preferredId = Number(uni.getStorageSync(CURRENT_LEDGER_KEY)) || 0;
  const currentId = ref(0);
  const loading = ref(false);
  const current = computed(
    () => ledgers.value.find((ledger) => ledger.id === currentId.value) || null,
  );

  async function fetchLedgers() {
    loading.value = true;
    try {
      ledgers.value = await ledgerApi.getLedgers();
      const nextId = ledgers.value.some((ledger) => ledger.id === preferredId)
        ? preferredId
        : ledgers.value[0]?.id || 0;
      switchLedger(nextId);
      return ledgers.value;
    } finally {
      loading.value = false;
    }
  }

  function switchLedger(id: number) {
    preferredId = id;
    currentId.value = id;
    if (id) uni.setStorageSync(CURRENT_LEDGER_KEY, id);
    else uni.removeStorageSync(CURRENT_LEDGER_KEY);
  }

  async function create(name: string, type: LedgerType) {
    const ledger = await ledgerApi.createLedger(name, type);
    ledgers.value.push(ledger);
    switchLedger(ledger.id);
    return ledger;
  }

  async function join(ledgerId: number, inviteCode: string) {
    const ledger = await ledgerApi.joinLedger(ledgerId, inviteCode);
    const index = ledgers.value.findIndex((item) => item.id === ledger.id);
    if (index >= 0) ledgers.value[index] = ledger;
    else ledgers.value.push(ledger);
    switchLedger(ledger.id);
    return ledger;
  }

  function clear() {
    ledgers.value = [];
    loading.value = false;
    switchLedger(0);
  }

  return { ledgers, currentId, current, loading, fetchLedgers, switchLedger, create, join, clear };
});

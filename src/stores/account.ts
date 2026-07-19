import { computed, ref } from "vue";
import { defineStore } from "pinia";
import * as accountApi from "@/api/accounts";
import type { Account } from "@/types";

export const useAccountStore = defineStore("account", () => {
  const accounts = ref<Account[]>([]);
  const loading = ref(false);
  const totalBalance = computed(() => accounts.value.reduce((sum, item) => sum + item.balance, 0));

  async function fetchAccounts(ledgerId: number) {
    loading.value = true;
    try {
      accounts.value = await accountApi.getAccounts(ledgerId);
      return accounts.value;
    } finally { loading.value = false; }
  }

  async function create(payload: accountApi.AccountPayload) {
    const account = await accountApi.createAccount(payload);
    accounts.value.push(account);
    return account;
  }

  async function update(id: number, payload: Partial<Omit<accountApi.AccountPayload, "ledger_id">>) {
    const account = await accountApi.updateAccount(id, payload);
    const index = accounts.value.findIndex((item) => item.id === id);
    if (index >= 0) accounts.value[index] = account;
    return account;
  }

  async function remove(id: number) {
    await accountApi.deleteAccount(id);
    accounts.value = accounts.value.filter((item) => item.id !== id);
  }

  function clear() {
    accounts.value = [];
    loading.value = false;
  }

  return { accounts, loading, totalBalance, fetchAccounts, create, update, remove, clear };
});

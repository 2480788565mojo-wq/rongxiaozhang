import { computed, ref } from "vue";
import { defineStore } from "pinia";
import { devLogin, getMe, wxLogin } from "@/api/auth";
import { clearToken, getStoredToken, saveToken } from "@/api/client";
import { useAccountStore } from "@/stores/account";
import { useBillStore } from "@/stores/bill";
import { useBudgetStore } from "@/stores/budget";
import { useCategoryStore } from "@/stores/category";
import { useLedgerStore } from "@/stores/ledger";
import { useSSEStore } from "@/stores/sse";
import type { User } from "@/types";

function getWechatCode(): Promise<string> {
  return new Promise((resolve, reject) => {
    uni.login({
      provider: "weixin",
      success: (result) => resolve(result.code),
      fail: reject,
    });
  });
}

export const useUserStore = defineStore("user", () => {
  const token = ref(getStoredToken());
  const user = ref<User | null>(null);
  const loading = ref(false);
  const isLoggedIn = computed(() => Boolean(token.value));

  async function login() {
    loading.value = true;
    try {
      let response;
      // #ifdef H5
      if ((import.meta as any).env?.DEV) {
        response = await devLogin();
      } else {
        const code = await getWechatCode();
        response = await wxLogin(code);
      }
      // #endif
      // #ifndef H5
      const code = await getWechatCode();
      response = await wxLogin(code);
      // #endif
      token.value = response.access_token;
      user.value = response.user;
      saveToken(response.access_token);
      return response.user;
    } finally {
      loading.value = false;
    }
  }

  async function fetchUser() {
    if (!token.value) return null;
    user.value = await getMe();
    return user.value;
  }

  async function restore() {
    token.value = getStoredToken();
    if (!token.value) return null;
    try {
      return await fetchUser();
    } catch {
      logout();
      return null;
    }
  }

  function logout() {
    useSSEStore().disconnect();
    useAccountStore().clear();
    useBillStore().clear();
    useBudgetStore().clear();
    useCategoryStore().clear();
    useLedgerStore().clear();
    token.value = "";
    user.value = null;
    clearToken();
  }

  return { token, user, loading, isLoggedIn, login, fetchUser, restore, logout };
});

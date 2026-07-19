import { ref, shallowRef } from "vue";
import { defineStore } from "pinia";
import { API_BASE_URL } from "@/api/client";
import { createSSEConnection, type SSEConnection } from "@/utils/sse";
import type { Bill, BudgetAlertData, SSEEvent } from "@/types";

export const useSSEStore = defineStore("sse", () => {
  const connected = ref(false);
  const connection = shallowRef<SSEConnection | null>(null);

  function handleEvent(message: SSEEvent) {
    if (message.event === "connected") {
      connected.value = true;
      return;
    }
    if (message.event === "warning" || message.event === "blocked") {
      const riskLevel = message.event as "warning" | "blocked";
      import("./budget").then(({ useBudgetStore }) => {
        useBudgetStore().showAlert({
          ...(message.data as unknown as BudgetAlertData),
          risk_level: riskLevel,
        });
      });
      return;
    }
    if (message.event === "completed") {
      const bill = (message.data as { bill?: Bill }).bill;
      if (bill) {
        import("./bill").then(({ useBillStore }) => useBillStore().prepend(bill));
      }
      return;
    }
    if (message.event === "insight_ready") {
      uni.showToast({ title: "新的消费洞察已生成", icon: "none" });
    }
  }

  function connect(token: string) {
    disconnect();
    if (!token) return;
    connection.value = createSSEConnection(`${API_BASE_URL}/sse/subscribe`, {
      token,
      onEvent: handleEvent,
      onError: () => {
        connected.value = false;
      },
    });
  }

  function disconnect() {
    connection.value?.close();
    connection.value = null;
    connected.value = false;
  }

  return { connected, connect, disconnect, handleEvent };
});

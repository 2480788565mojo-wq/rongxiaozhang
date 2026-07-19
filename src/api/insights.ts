import { api } from "./client";
import type { Insight } from "@/types";

export function getInsights(ledgerId?: number, page = 1) {
  return api<{ items: Insight[]; total: number }>("/insights", {
    params: { ledger_id: ledgerId, page },
  });
}

export function getInsight(id: number) {
  return api<Insight>(`/insights/${id}`);
}

export function generateInsight(
  ledgerId: number,
  reportType: "weekly" | "monthly" | "on_demand" = "on_demand",
) {
  return api<{ status: "queued"; ledger_id: number; report_type: string }>(
    "/insights/generate",
    {
      method: "POST",
      body: { ledger_id: ledgerId, report_type: reportType },
    },
  );
}

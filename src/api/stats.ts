import { api } from "./client";
import type { CategoryStat, StatsOverview, TrendPoint } from "@/types";

export function getOverview(ledgerId: number, year?: number, month?: number) {
  return api<StatsOverview>("/stats/overview", {
    params: { ledger_id: ledgerId, year, month },
  });
}

export function getTrend(ledgerId: number, months = 12) {
  return api<{ ledger_id: number; items: TrendPoint[] }>("/stats/trend", {
    params: { ledger_id: ledgerId, months },
  });
}

export function getCategoryStats(
  ledgerId: number,
  year?: number,
  month?: number,
) {
  return api<{
    ledger_id: number;
    year: number;
    month: number;
    total: number;
    items: CategoryStat[];
  }>("/stats/category", {
    params: { ledger_id: ledgerId, year, month },
  });
}

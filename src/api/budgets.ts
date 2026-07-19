import { api } from "./client";
import type { BudgetStatusResponse } from "@/types";

export interface BudgetPayload {
  ledger_id: number;
  year: number;
  month: number;
  total_budget: number | null;
  category_budgets: Record<string, number>;
}

export function getBudget(ledgerId: number, year: number, month: number) {
  return api<BudgetPayload | null>("/budgets", {
    params: { ledger_id: ledgerId, year, month },
  });
}

export function setBudget(data: BudgetPayload) {
  return api<BudgetPayload>("/budgets", { method: "PUT", body: data });
}

export function getBudgetStatus(ledgerId: number, year?: number, month?: number) {
  return api<BudgetStatusResponse>("/budgets/status", {
    params: { ledger_id: ledgerId, year, month },
  });
}

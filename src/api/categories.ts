import { api } from "./client";
import type { BillType, CustomCategory } from "@/types";

export interface CategoryPayload {
  ledger_id: number;
  type: BillType;
  parent_name: string;
  name: string;
  icon?: string | null;
  sort?: number;
}

export function getCategories(ledgerId: number, type?: BillType) {
  return api<CustomCategory[]>("/categories", {
    params: { ledger_id: ledgerId, type },
  });
}

export function createCategory(payload: CategoryPayload) {
  return api<CustomCategory>("/categories", { method: "POST", body: payload });
}

export function updateCategory(id: number, payload: Partial<Omit<CategoryPayload, "ledger_id" | "type">>) {
  return api<CustomCategory>(`/categories/${id}`, { method: "PUT", body: payload });
}

export function deleteCategory(id: number) {
  return api<void>(`/categories/${id}`, { method: "DELETE" });
}

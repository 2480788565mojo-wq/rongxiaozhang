import { api } from "./client";
import type { Account } from "@/types";

export interface AccountPayload {
  ledger_id: number;
  name: string;
  type: string;
  icon?: string | null;
  balance: number;
}

export function getAccounts(ledgerId: number) {
  return api<Account[]>("/accounts", { params: { ledger_id: ledgerId } });
}

export function createAccount(payload: AccountPayload) {
  return api<Account>("/accounts", { method: "POST", body: payload });
}

export function updateAccount(id: number, payload: Partial<Omit<AccountPayload, "ledger_id">>) {
  return api<Account>(`/accounts/${id}`, { method: "PUT", body: payload });
}

export function deleteAccount(id: number) {
  return api<void>(`/accounts/${id}`, { method: "DELETE" });
}

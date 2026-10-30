import { api } from "./client";
import type { Ledger } from "@/types";

export function getLedgers() {
  return api<Ledger[]>("/ledgers");
}

export function getLedger(id: number) {
  return api<Ledger>(`/ledgers/${id}`);
}

export function createLedger(name: string, type: "personal" | "shared") {
  return api<Ledger>("/ledgers", { method: "POST", body: { name, type } });
}

export function joinLedger(ledgerId: number, inviteCode: string) {
  return api<Ledger>(`/ledgers/${ledgerId}/join`, {
    method: "POST",
    body: { invite_code: inviteCode },
  });
}

export interface Settlement {
  from_user_id: number;
  from_user_name: string;
  to_user_id: number;
  to_user_name: string;
  amount: number;
  share_ids: number[];
}

export interface SettlementResponse {
  ledger_id: number;
  settlements: Settlement[];
}

export function settleLedger(ledgerId: number) {
  return api<SettlementResponse>(`/ledgers/${ledgerId}/settle`, {
    method: "POST",
  });
}

export function confirmSettlement(
  ledgerId: number,
  payload: { from_user_id: number; to_user_id: number; share_ids: number[] },
) {
  return api<SettlementResponse>(`/ledgers/${ledgerId}/settle/confirm`, {
    method: "POST",
    body: payload,
  });
}

export function rotateInviteCode(ledgerId: number) {
  return api<Ledger>(`/ledgers/${ledgerId}/invite/rotate`, { method: "POST" });
}

export function removeLedgerMember(ledgerId: number, userId: number) {
  return api<Ledger>(`/ledgers/${ledgerId}/members/${userId}`, {
    method: "DELETE",
  });
}

export function updateMemberRole(
  ledgerId: number,
  userId: number,
  role: "admin" | "member",
) {
  return api<Ledger>(`/ledgers/${ledgerId}/members/${userId}`, {
    method: "PUT",
    body: { role },
  });
}

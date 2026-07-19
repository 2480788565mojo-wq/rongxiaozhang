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

export function settleLedger(ledgerId: number) {
  return api<{ ledger_id: number; settlements: unknown[] }>(
    `/ledgers/${ledgerId}/settle`,
    { method: "POST" },
  );
}

export function rotateInviteCode(ledgerId: number) {
  return api<Ledger>(`/ledgers/${ledgerId}/invite/rotate`, { method: "POST" });
}

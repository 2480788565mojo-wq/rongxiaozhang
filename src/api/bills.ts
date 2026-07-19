import { api, API_BASE_URL } from "./client";
import type { Bill, BillListResponse, ParsedBill } from "@/types";

export interface BillQuery {
  ledger_id: number;
  year?: number;
  month?: number;
  category?: string;
  page?: number;
  page_size?: number;
}

export interface ConfirmBillPayload {
  ledger_id: number;
  session_id: string;
  raw_input: string;
  parsed: ParsedBill;
  share_user_ids?: number[];
  force?: boolean;
}

export const transcribeStreamUrl = () => `${API_BASE_URL}/bills/transcribe`;

export function confirmBill(payload: ConfirmBillPayload) {
  return api<Bill>("/bills/confirm", { method: "POST", body: payload });
}

export function getBills(params: BillQuery) {
  return api<BillListResponse>("/bills", { params: { ...params } });
}

export function getBill(id: number) {
  return api<Bill>(`/bills/${id}`);
}

export function updateBill(id: number, data: Partial<ParsedBill>) {
  return api<Bill>(`/bills/${id}`, { method: "PUT", body: data });
}

export function deleteBill(id: number) {
  return api<void>(`/bills/${id}`, { method: "DELETE" });
}

export type BillType = "expense" | "income";
export type LedgerType = "personal" | "shared";
export type LedgerRole = "owner" | "admin" | "member";
export type RiskLevel = "safe" | "warning" | "blocked";

export interface User {
  id: number;
  nickname: string | null;
  avatar_url: string | null;
  default_ledger_id: number | null;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface LedgerMember {
  user_id: number;
  role: LedgerRole;
  nickname: string | null;
  avatar_url: string | null;
}

export interface Ledger {
  id: number;
  name: string;
  type: LedgerType;
  owner_id: number;
  invite_code: string | null;
  settle_strategy: string;
  member_count: number;
  created_at: string | null;
  members: LedgerMember[];
}

export interface BillShare {
  user_id: number;
  share_amount: number;
  settled: boolean;
  settled_at: string | null;
}

export interface Bill {
  id: number;
  ledger_id: number;
  creator_id: number;
  type: BillType;
  amount: number;
  category: string;
  subcategory: string | null;
  account: string | null;
  note: string | null;
  bill_date: string;
  raw_input: string | null;
  ai_parsed: boolean;
  created_at: string;
  shares: BillShare[];
}

export interface BillListResponse {
  items: Bill[];
  total: number;
  page: number;
  page_size: number;
}

export interface Account {
  id: number;
  user_id: number;
  ledger_id: number;
  name: string;
  type: string;
  icon: string | null;
  balance: number;
  created_at: string;
}

export interface CustomCategory {
  id: number;
  user_id: number;
  ledger_id: number;
  type: BillType;
  parent_name: string;
  name: string;
  icon: string | null;
  sort: number;
  created_at: string;
}

export interface ParsedBill {
  type: BillType;
  amount: number;
  category: string;
  subcategory: string | null;
  account: string | null;
  note: string | null;
  bill_date: string;
}

export interface BudgetStatus {
  category: string;
  kind?: "category" | "total";
  spent: number;
  budget: number;
  remaining: number;
  percentage: number;
  risk_level: RiskLevel;
}

export interface BudgetStatusResponse {
  ledger_id: number;
  year: number;
  month: number;
  statuses: BudgetStatus[];
}

export interface BudgetAlertData extends Partial<BudgetStatus> {
  risk_level: RiskLevel;
  message?: string;
}

export interface StatsOverview {
  ledger_id: number;
  year: number;
  month: number;
  income: number;
  expense: number;
  balance: number;
  budget_used_percentage: number | null;
}

export interface TrendPoint {
  period: string;
  income: number;
  expense: number;
}

export interface CategoryStat {
  category: string;
  amount: number;
  percentage: number;
}

export interface Insight {
  id: number;
  user_id: number;
  ledger_id: number;
  report_type: "weekly" | "monthly" | "on_demand";
  content: string;
  key_findings: unknown[] | null;
  suggested_actions: unknown[] | null;
  generated_at: string;
}

export interface SSEEvent<T = Record<string, unknown>> {
  event: string;
  data: T;
}

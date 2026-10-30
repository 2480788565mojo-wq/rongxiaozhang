import { api } from "./client";
import type { TokenResponse, User } from "@/types";

export function wxLogin(code: string) {
  return api<TokenResponse>("/auth/login", {
    method: "POST",
    body: { code },
  });
}

export function devLogin(nickname = "H5 测试用户") {
  return api<TokenResponse>("/auth/dev-login", {
    method: "POST",
    body: { nickname },
  });
}

export function getMe() {
  return api<User>("/auth/me");
}

export function exportAccount() {
  return api<Record<string, unknown>>("/auth/export");
}

export function deleteAccount() {
  return api<void>("/auth/me", { method: "DELETE" });
}

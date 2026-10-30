const TOKEN_KEY = "rxz_access_token";
let authExpiredNotified = false;

function notifyAuthExpired(): void {
  clearToken();
  if (authExpiredNotified) return;
  authExpiredNotified = true;
  uni.$emit("rxz:auth-expired");
  setTimeout(() => {
    authExpiredNotified = false;
  }, 1500);
}

export const API_BASE_URL =
  (import.meta as any).env?.VITE_API_BASE_URL ||
  "https://api.rongxiaozhang.cn/api/v1";

export interface RequestOptions {
  method?: "GET" | "POST" | "PUT" | "DELETE";
  body?: any;
  params?: Record<string, unknown>;
}

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly statusCode: number,
    public readonly data?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export function getStoredToken(): string {
  return uni.getStorageSync(TOKEN_KEY) || "";
}

export function saveToken(token: string): void {
  uni.setStorageSync(TOKEN_KEY, token);
}

export function clearToken(): void {
  uni.removeStorageSync(TOKEN_KEY);
}

function appendQuery(path: string, params?: Record<string, unknown>): string {
  if (!params) return path;
  const query = Object.entries(params)
    .filter(([, value]) => value !== undefined && value !== null && value !== "")
    .map(
      ([key, value]) =>
        `${encodeURIComponent(key)}=${encodeURIComponent(String(value))}`,
    )
    .join("&");
  return query ? `${path}?${query}` : path;
}

export async function api<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const token = getStoredToken();
  const response = await uni.request({
    url: `${API_BASE_URL}${appendQuery(path, options.params)}`,
    method: options.method || "GET",
    data: options.body,
    header: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });

  if (response.statusCode === 401) {
    notifyAuthExpired();
  }
  if (response.statusCode >= 400) {
    const data = response.data as { detail?: string; message?: string } | undefined;
    throw new ApiError(
      data?.detail || data?.message || "请求失败，请稍后重试",
      response.statusCode,
      response.data,
    );
  }
  return response.data as T;
}

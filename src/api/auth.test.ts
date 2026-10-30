import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "./client";
import { deleteAccount, exportAccount } from "./auth";

vi.mock("./client");

describe("exportAccount", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("GET /auth/export 原样返回服务器导出的 JSON", async () => {
    const payload = {
      user: { id: 1, nickname: "阿荣" },
      ledgers: [{ id: 5, name: "我的账本" }],
      bills: [],
      accounts: [],
      budgets: [],
      categories: [],
      insights: [],
    };
    vi.mocked(api).mockResolvedValue(payload);

    const result = await exportAccount();

    expect(api).toHaveBeenCalledExactlyOnceWith("/auth/export");
    expect(result).toEqual(payload);
  });
});

describe("deleteAccount", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("DELETE /auth/me 且不发送请求体", async () => {
    vi.mocked(api).mockResolvedValue(undefined);

    await deleteAccount();

    expect(api).toHaveBeenCalledExactlyOnceWith("/auth/me", {
      method: "DELETE",
    });
  });
});

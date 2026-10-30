import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "./client";
import {
  confirmSettlement,
  removeLedgerMember,
  updateMemberRole,
} from "./ledgers";
import type { Ledger } from "@/types";

const ledger: Ledger = {
  id: 5,
  name: "旅行账本",
  type: "shared",
  owner_id: 1,
  invite_code: "INVITE88",
  settle_strategy: "equal",
  member_count: 1,
  created_at: null,
  members: [],
};

vi.mock("./client");

describe("confirmSettlement", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("POST 到 /settle/confirm 并原样提交双方与 share_ids", async () => {
    const payload = { from_user_id: 2, to_user_id: 1, share_ids: [11, 12] };
    vi.mocked(api).mockResolvedValue({ ledger_id: 5, settlements: [] });

    const result = await confirmSettlement(5, payload);

    expect(api).toHaveBeenCalledExactlyOnceWith("/ledgers/5/settle/confirm", {
      method: "POST",
      body: payload,
    });
    expect(result.settlements).toEqual([]);
  });
});

describe("removeLedgerMember", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("DELETE 到 /ledgers/{id}/members/{user_id}", async () => {
    vi.mocked(api).mockResolvedValue(ledger);

    const result = await removeLedgerMember(5, 9);

    expect(api).toHaveBeenCalledExactlyOnceWith("/ledgers/5/members/9", {
      method: "DELETE",
    });
    expect(result).toEqual(ledger);
  });
});

describe("updateMemberRole", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("PUT 到 /ledgers/{id}/members/{user_id} 并原样提交角色", async () => {
    vi.mocked(api).mockResolvedValue(ledger);

    const result = await updateMemberRole(5, 9, "admin");

    expect(api).toHaveBeenCalledExactlyOnceWith("/ledgers/5/members/9", {
      method: "PUT",
      body: { role: "admin" },
    });
    expect(result).toEqual(ledger);
  });

  it("降级为普通成员时提交 member", async () => {
    vi.mocked(api).mockResolvedValue(ledger);

    await updateMemberRole(7, 3, "member");

    expect(api).toHaveBeenCalledExactlyOnceWith("/ledgers/7/members/3", {
      method: "PUT",
      body: { role: "member" },
    });
  });
});

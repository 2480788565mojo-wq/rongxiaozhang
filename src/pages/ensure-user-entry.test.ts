import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { flushPromises, mount, type VueWrapper } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { getMe } from "@/api/auth";
import * as ledgerApi from "@/api/ledgers";
import { useUserStore } from "@/stores/user";
import type { Ledger, User } from "@/types";
import MembersPage from "./ledgers/members.vue";
import SettlePage from "./ledgers/settle.vue";
import SettingsPage from "./settings/index.vue";

vi.mock("@/api/auth");
vi.mock("@/api/ledgers");
vi.mock("@/api/bills");
vi.mock("@/api/accounts");
vi.mock("@/api/categories");

const USER: User = {
  id: 2,
  nickname: "我",
  avatar_url: null,
  default_ledger_id: 5,
};

const LEDGER: Ledger = {
  id: 5,
  name: "旅行账本",
  type: "shared",
  owner_id: 2,
  invite_code: "INVITE88",
  settle_strategy: "equal",
  member_count: 2,
  created_at: null,
  members: [
    { user_id: 2, role: "owner", nickname: "我", avatar_url: null },
    { user_id: 3, role: "member", nickname: "小明", avatar_url: null },
  ],
};

const wrappers: VueWrapper[] = [];

function deferredGetMe() {
  let resolveMe!: (value: User) => void;
  vi.mocked(getMe).mockImplementation(
    () =>
      new Promise<User>((resolve) => {
        resolveMe = resolve;
      }),
  );
  return () => resolveMe(USER);
}

function mountPage(component: any) {
  const pinia = createPinia();
  setActivePinia(pinia);
  // 模拟 restore 非 401 失败后：本地仍有 token，但 user 为 null。
  useUserStore().token = "stored-token";
  const wrapper = mount(component, { global: { plugins: [pinia] } });
  wrappers.push(wrapper);
  return wrapper;
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(getCurrentPages).mockReturnValue([
    { options: { id: "5" } },
  ] as any);
});

afterEach(() => {
  wrappers.splice(0).forEach((wrapper) => wrapper.unmount());
});

describe("角色页进入时先补拉用户", () => {
  it("members：ensureUser 完成前不加载账本，完成后恢复创建者操作按钮", async () => {
    vi.mocked(ledgerApi.getLedger).mockResolvedValue(LEDGER);
    const resolveMe = deferredGetMe();
    const wrapper = mountPage(MembersPage);
    await flushPromises();

    expect(getMe).toHaveBeenCalledTimes(1);
    expect(ledgerApi.getLedger).not.toHaveBeenCalled();

    resolveMe();
    await flushPromises();

    expect(ledgerApi.getLedger).toHaveBeenCalledExactlyOnceWith(5);
    expect(wrapper.findAll(".action").length).toBeGreaterThan(0);
  });

  it("settle：ensureUser 完成前不计算结算，完成后按当前用户显示确认按钮", async () => {
    vi.mocked(ledgerApi.settleLedger).mockResolvedValue({
      ledger_id: 5,
      settlements: [
        {
          from_user_id: 2,
          from_user_name: "我",
          to_user_id: 3,
          to_user_name: "小明",
          amount: 50,
          share_ids: [11],
        },
      ],
    });
    const resolveMe = deferredGetMe();
    const wrapper = mountPage(SettlePage);
    await flushPromises();

    expect(getMe).toHaveBeenCalledTimes(1);
    expect(ledgerApi.settleLedger).not.toHaveBeenCalled();

    resolveMe();
    await flushPromises();

    expect(ledgerApi.settleLedger).toHaveBeenCalledExactlyOnceWith(5);
    expect(wrapper.find(".confirm-settle").exists()).toBe(true);
  });

  it("settings：ensureUser 完成前不加载账本列表，完成后才发起 getLedgers", async () => {
    vi.mocked(ledgerApi.getLedgers).mockResolvedValue([]);
    const resolveMe = deferredGetMe();
    mountPage(SettingsPage);
    await flushPromises();

    expect(getMe).toHaveBeenCalledTimes(1);
    expect(ledgerApi.getLedgers).not.toHaveBeenCalled();

    resolveMe();
    await flushPromises();

    expect(ledgerApi.getLedgers).toHaveBeenCalledTimes(1);
  });
});

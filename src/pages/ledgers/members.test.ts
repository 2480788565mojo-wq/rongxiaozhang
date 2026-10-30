import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { flushPromises, mount, type VueWrapper } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { useUserStore } from "@/stores/user";
import * as ledgerApi from "@/api/ledgers";
import type { Ledger, LedgerMember, LedgerRole } from "@/types";
import MembersPage from "./members.vue";

vi.mock("@/api/ledgers");

const wrappers: VueWrapper[] = [];

function member(
  user_id: number,
  role: LedgerRole,
  nickname: string,
): LedgerMember {
  return { user_id, role, nickname, avatar_url: null };
}

function ledgerWith(members: LedgerMember[]): Ledger {
  return {
    id: 5,
    name: "旅行账本",
    type: "shared",
    owner_id: 1,
    invite_code: "INVITE88",
    settle_strategy: "equal",
    member_count: members.length,
    created_at: null,
    members,
  };
}

async function mountPage(members: LedgerMember[], currentUserId = 1) {
  const pinia = createPinia();
  setActivePinia(pinia);
  useUserStore().user = {
    id: currentUserId,
    nickname: "我",
    avatar_url: null,
    default_ledger_id: 5,
  };
  vi.mocked(ledgerApi.getLedger).mockResolvedValue(ledgerWith(members));
  vi.mocked(getCurrentPages).mockReturnValue([
    { options: { id: "5" } },
  ] as any);
  const wrapper = mount(MembersPage, { global: { plugins: [pinia] } });
  wrappers.push(wrapper);
  await flushPromises();
  return wrapper;
}

function rowOf(wrapper: VueWrapper, nickname: string) {
  const row = wrapper
    .findAll(".member")
    .find((item) => item.text().includes(nickname));
  if (!row) throw new Error(`未找到成员行：${nickname}`);
  return row;
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(uni.showModal).mockImplementation((options: any) => {
    void options.success?.({ confirm: true, cancel: false });
  });
});

afterEach(() => {
  wrappers.splice(0).forEach((wrapper) => wrapper.unmount());
});

describe("账本成员管理", () => {
  it("创建者看到普通成员的设为管理员和移除，对自己/创建者不显示操作", async () => {
    const wrapper = await mountPage([
      member(1, "owner", "阿荣"),
      member(2, "member", "小明"),
      member(3, "admin", "小红"),
    ]);

    const plainActions = rowOf(wrapper, "小明").findAll(".action");
    expect(plainActions.map((item) => item.text())).toEqual([
      "设为管理员",
      "移除",
    ]);
    const adminActions = rowOf(wrapper, "小红").findAll(".action");
    expect(adminActions.map((item) => item.text())).toEqual([
      "设为成员",
      "移除",
    ]);
    // 创建者（也是当前用户）那一行没有移除按钮。
    expect(rowOf(wrapper, "阿荣").findAll(".action")).toHaveLength(0);
    expect(wrapper.text()).toContain("创建者");
    expect(wrapper.text()).toContain("管理员");
  });

  it("管理员只能移除普通成员，且没有设为管理员入口", async () => {
    const wrapper = await mountPage(
      [
        member(1, "owner", "阿荣"),
        member(2, "member", "小明"),
        member(3, "admin", "小红"),
        member(4, "admin", "小刚"),
      ],
      3,
    );

    const plainActions = rowOf(wrapper, "小明").findAll(".action");
    expect(plainActions.map((item) => item.text())).toEqual(["移除"]);
    // 管理员不能操作创建者、自己和其他管理员。
    expect(rowOf(wrapper, "阿荣").findAll(".action")).toHaveLength(0);
    expect(rowOf(wrapper, "小红").findAll(".action")).toHaveLength(0);
    expect(rowOf(wrapper, "小刚").findAll(".action")).toHaveLength(0);
    expect(wrapper.text()).not.toContain("设为管理员");
    expect(wrapper.text()).not.toContain("设为成员");
  });

  it("普通成员看不到任何成员操作按钮", async () => {
    const wrapper = await mountPage(
      [
        member(1, "owner", "阿荣"),
        member(2, "member", "小明"),
        member(3, "admin", "小红"),
        member(4, "member", "小刚"),
      ],
      2,
    );

    expect(wrapper.findAll(".action")).toHaveLength(0);
    expect(wrapper.text()).not.toContain("移除");
    expect(wrapper.text()).not.toContain("设为管理员");
  });

  it("复制邀请码调用 uni.setClipboardData 并提示复制成功", async () => {
    const wrapper = await mountPage([member(1, "owner", "阿荣")]);

    await wrapper.find(".invite .copy").trigger("click");

    expect(uni.setClipboardData).toHaveBeenCalledExactlyOnceWith({
      data: "INVITE88",
      success: expect.any(Function),
    });
    const options = vi.mocked(uni.setClipboardData).mock.calls[0][0] as any;
    options.success();
    expect(uni.showToast).toHaveBeenCalledWith({
      title: "邀请码已复制",
      icon: "none",
    });
  });

  it("设为管理员提交精确的 PUT 参数并刷新页面数据", async () => {
    const wrapper = await mountPage(
      [member(1, "owner", "阿荣"), member(2, "member", "小明")],
      1,
    );
    vi.mocked(ledgerApi.updateMemberRole).mockResolvedValue(
      ledgerWith([
        member(1, "owner", "阿荣"),
        member(2, "admin", "小明"),
      ]),
    );

    await rowOf(wrapper, "小明").findAll(".action")[0].trigger("click");
    await flushPromises();

    expect(ledgerApi.updateMemberRole).toHaveBeenCalledExactlyOnceWith(
      5,
      2,
      "admin",
    );
    expect(rowOf(wrapper, "小明").text()).toContain("管理员");
    expect(rowOf(wrapper, "小明").findAll(".action")[0].text()).toBe(
      "设为成员",
    );
    expect(uni.showToast).toHaveBeenCalledWith({
      title: "成员角色已更新",
      icon: "success",
    });
  });

  it("设为成员提交精确的 PUT 参数", async () => {
    const wrapper = await mountPage(
      [member(1, "owner", "阿荣"), member(3, "admin", "小红")],
      1,
    );
    vi.mocked(ledgerApi.updateMemberRole).mockResolvedValue(
      ledgerWith([
        member(1, "owner", "阿荣"),
        member(3, "member", "小红"),
      ]),
    );

    await rowOf(wrapper, "小红").findAll(".action")[0].trigger("click");
    await flushPromises();

    expect(ledgerApi.updateMemberRole).toHaveBeenCalledExactlyOnceWith(
      5,
      3,
      "member",
    );
    expect(rowOf(wrapper, "小红").text()).toContain("成员");
  });

  it("移除成员确认后提交精确的 DELETE 参数并移除该行", async () => {
    const wrapper = await mountPage(
      [member(1, "owner", "阿荣"), member(2, "member", "小明")],
      1,
    );
    vi.mocked(ledgerApi.removeLedgerMember).mockResolvedValue(
      ledgerWith([member(1, "owner", "阿荣")]),
    );

    const removeButton = rowOf(wrapper, "小明")
      .findAll(".action")
      .find((item) => item.text() === "移除");
    await removeButton!.trigger("click");
    await flushPromises();

    expect(uni.showModal).toHaveBeenCalledWith(
      expect.objectContaining({ title: "移除成员" }),
    );
    expect(ledgerApi.removeLedgerMember).toHaveBeenCalledExactlyOnceWith(5, 2);
    expect(wrapper.find(".member").exists()).toBe(true);
    expect(wrapper.text()).not.toContain("小明");
    expect(uni.showToast).toHaveBeenCalledWith({
      title: "已移除成员",
      icon: "success",
    });
  });
});

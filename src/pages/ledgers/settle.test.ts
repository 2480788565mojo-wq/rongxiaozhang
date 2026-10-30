import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { flushPromises, mount, type VueWrapper } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { useUserStore } from "@/stores/user";
import * as ledgerApi from "@/api/ledgers";
import SettlePage from "./settle.vue";

vi.mock("@/api/ledgers");

const wrappers: VueWrapper[] = [];

const directTransfer: ledgerApi.Settlement = {
  from_user_id: 2,
  from_user_name: "小明",
  to_user_id: 1,
  to_user_name: "小红",
  amount: 50,
  share_ids: [11, 12],
};

const chainTransfer: ledgerApi.Settlement = {
  from_user_id: 3,
  from_user_name: "小刚",
  to_user_id: 1,
  to_user_name: "小红",
  amount: 30,
  share_ids: [],
};

async function mountPage(ledgerId = 5, currentUserId: number | null = 2) {
  const pinia = createPinia();
  setActivePinia(pinia);
  useUserStore().user =
    currentUserId === null
      ? null
      : {
          id: currentUserId,
          nickname: "我",
          avatar_url: null,
          default_ledger_id: ledgerId,
        };
  vi.mocked(getCurrentPages).mockReturnValue([
    { options: { id: String(ledgerId) } },
  ] as any);
  const wrapper = mount(SettlePage, { global: { plugins: [pinia] } });
  wrappers.push(wrapper);
  await flushPromises();
  return wrapper;
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(ledgerApi.settleLedger).mockResolvedValue({
    ledger_id: 5,
    settlements: [directTransfer, chainTransfer],
  });
  vi.mocked(ledgerApi.confirmSettlement).mockResolvedValue({
    ledger_id: 5,
    settlements: [],
  });
});

afterEach(() => {
  wrappers.splice(0).forEach((wrapper) => wrapper.unmount());
});

describe("AA 结算确认", () => {
  it("付款人看到“标记已结算”并按原 share_ids 提交", async () => {
    const wrapper = await mountPage(5, directTransfer.from_user_id);

    expect(ledgerApi.settleLedger).toHaveBeenCalledWith(5);
    const buttons = wrapper.findAll(".confirm-settle");
    expect(buttons).toHaveLength(1);
    expect(buttons[0].text()).toContain("标记已结算");

    await buttons[0].trigger("click");
    await flushPromises();

    expect(ledgerApi.confirmSettlement).toHaveBeenCalledExactlyOnceWith(5, {
      from_user_id: 2,
      to_user_id: 1,
      share_ids: [11, 12],
    });
    expect(uni.showToast).toHaveBeenCalledWith({
      title: "已标记结算",
      icon: "success",
    });
    // 后端返回刷新后的空计划，页面应立即清空。
    expect(wrapper.findAll(".transfer")).toHaveLength(0);
  });

  it("账本 id 非法时显示错误，不请求结算也不显示空状态", async () => {
    const pinia = createPinia();
    setActivePinia(pinia);
    useUserStore().user = {
      id: 2,
      nickname: "我",
      avatar_url: null,
      default_ledger_id: 5,
    };
    vi.mocked(getCurrentPages).mockReturnValue([
      { options: { id: "not-a-number" } },
    ] as any);
    const wrapper = mount(SettlePage, { global: { plugins: [pinia] } });
    wrappers.push(wrapper);
    await flushPromises();

    expect(wrapper.text()).toContain("账本编号无效");
    expect(wrapper.find(".empty").exists()).toBe(false);
    expect(ledgerApi.settleLedger).not.toHaveBeenCalled();
  });

  it("重新计算失败时清空旧列表并显示错误", async () => {
    const wrapper = await mountPage(5, directTransfer.from_user_id);
    expect(wrapper.findAll(".transfer")).toHaveLength(2);
    vi.mocked(ledgerApi.settleLedger).mockRejectedValueOnce(
      new Error("结算服务暂不可用"),
    );

    await wrapper.find(".calculate").trigger("click");
    await flushPromises();

    expect(wrapper.text()).toContain("结算服务暂不可用");
    expect(wrapper.findAll(".transfer")).toHaveLength(0);
    expect(wrapper.find(".empty").exists()).toBe(false);
  });

  it("收款人也看到确认按钮", async () => {
    const wrapper = await mountPage(5, directTransfer.to_user_id);

    expect(wrapper.findAll(".confirm-settle")).toHaveLength(1);
  });

  it("非付款/收款成员看不到按钮，只看到他人确认提示", async () => {
    const wrapper = await mountPage(5, 9);

    expect(wrapper.find(".confirm-settle").exists()).toBe(false);
    expect(wrapper.find(".manual").text()).toContain("这笔由其他成员确认");
    expect(ledgerApi.confirmSettlement).not.toHaveBeenCalled();
  });

  it("share_ids 为空的链路转账不显示按钮并提示逐笔处理", async () => {
    vi.mocked(ledgerApi.settleLedger).mockResolvedValue({
      ledger_id: 5,
      settlements: [chainTransfer],
    });

    const wrapper = await mountPage(5, chainTransfer.from_user_id);

    expect(wrapper.find(".confirm-settle").exists()).toBe(false);
    expect(wrapper.find(".manual").text()).toContain("请到账单详情逐笔处理");
  });

  it("加载失败显示后端原因并可重新计算", async () => {
    vi.mocked(ledgerApi.settleLedger).mockRejectedValueOnce(
      new Error("结算服务暂不可用"),
    );

    const wrapper = await mountPage();
    expect(wrapper.find(".load-error").text()).toContain("结算服务暂不可用");

    await wrapper.find(".calculate").trigger("click");
    await flushPromises();

    expect(wrapper.find(".load-error").exists()).toBe(false);
    expect(wrapper.findAll(".transfer")).toHaveLength(2);
  });

  it("确认失败时提示原因并重新拉取结算计划", async () => {
    vi.mocked(ledgerApi.confirmSettlement).mockRejectedValueOnce(
      new Error("金额已变化，请重新计算"),
    );

    const wrapper = await mountPage();
    await wrapper.find(".confirm-settle").trigger("click");
    await flushPromises();

    expect(uni.showToast).toHaveBeenCalledWith({
      title: "金额已变化，请重新计算",
      icon: "none",
    });
    expect(ledgerApi.settleLedger).toHaveBeenCalledTimes(2);
    expect(wrapper.findAll(".confirm-settle")).toHaveLength(1);
  });
});

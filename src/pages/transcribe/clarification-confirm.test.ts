import { beforeEach, describe, expect, it, vi } from "vitest";
import { flushPromises, mount, type VueWrapper } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import type { SSEEvent } from "@/types";

/**
 * Bug N1 回归：多笔解析时后端可能回传“含未完成项”的 items，
 * 前端 normalize 会丢弃未完成项。若此时仍允许确认，确认键会按过滤后的
 * 下标生成，导致重复/错记账单。生产修复：clarificationQuestion 非空时
 * canConfirm 必为 false，saveBills 提前返回。
 */

const { sseCalls, confirmBill } = vi.hoisted(() => ({
  sseCalls: [] as any[],
  confirmBill: vi.fn(),
}));

vi.mock("@/utils/sse", () => ({
  createSSEConnection: vi.fn((_url: string, options: any) => {
    sseCalls.push(options);
    return { close: vi.fn() };
  }),
}));

vi.mock("@/api/bills", () => ({
  transcribeStreamUrl: () => "/api/v1/bills/transcribe",
  confirmBill,
}));

const ledger = {
  id: 1,
  name: "我的账本",
  type: "personal" as const,
  owner_id: 1,
  invite_code: null,
  settle_strategy: "equal",
  member_count: 1,
  created_at: "2026-10-01T00:00:00",
  members: [],
};

const billStub = (id: number) => ({
  id,
  ledger_id: 1,
  user_id: 1,
  type: "expense" as const,
  amount: 12,
  category: "餐饮",
  subcategory: null,
  account: null,
  note: null,
  bill_date: "2026-10-29",
  created_at: "2026-10-29T00:00:00",
});

const wrappers: VueWrapper[] = [];

async function mountPage() {
  const pinia = createPinia();
  setActivePinia(pinia);
  const { useAppStore } = await import("@/stores/app");
  const { useUserStore } = await import("@/stores/user");
  const { useLedgerStore } = await import("@/stores/ledger");
  useAppStore().aiEnabled = true;
  useUserStore().token = "token";
  useLedgerStore().ledgers = [ledger];
  useLedgerStore().switchLedger(1);
  const component = (await import("./index.vue")).default;
  const wrapper = mount(component, { global: { plugins: [pinia] } });
  await flushPromises();
  wrappers.push(wrapper);
  return wrapper;
}

function streamOptions() {
  return sseCalls[sseCalls.length - 1];
}

async function startAnalysis(wrapper: VueWrapper, text = "早餐 12，打车 20，第三笔 30") {
  await wrapper.find(".speech-input").setValue(text);
  await wrapper.find(".analyze-button").trigger("click");
  await flushPromises();
  expect(sseCalls.length).toBeGreaterThan(0);
  return streamOptions();
}

async function emit(options: any, event: SSEEvent) {
  options.onEvent(event);
  await flushPromises();
}

/** 直接调用 saveBills，验证“入口提前返回”这一层防护（不依赖 disabled 属性）。 */
async function callSaveBills(wrapper: VueWrapper) {
  const vm = wrapper.vm as any;
  const saveBills = vm.saveBills ?? vm.$?.setupState?.saveBills;
  expect(typeof saveBills, "saveBills 应可从组件实例访问").toBe("function");
  await saveBills.call(vm, false);
  await flushPromises();
}

beforeEach(() => {
  sseCalls.length = 0;
  vi.mocked((globalThis as any).uni.showModal).mockReset();
  confirmBill.mockReset();
  confirmBill.mockImplementation(({ parsed }: any) => Promise.resolve(billStub(parsed.amount)));
});

describe("已有草稿再解析单笔：让用户选择追加/新批次", () => {
  const firstBatch = {
    session_id: "sess-first",
    items: [
      { type: "expense", amount: 12, category: "餐饮", bill_date: "2026-10-29" },
      { type: "expense", amount: 20, category: "交通", bill_date: "2026-10-29" },
    ],
  };
  const nextSingle = {
    session_id: "sess-second",
    items: [
      { type: "expense", amount: 30, category: "购物", bill_date: "2026-10-29" },
    ],
  };

  function answerModal(confirm: boolean) {
    vi.mocked((globalThis as any).uni.showModal).mockImplementationOnce(
      (options: any) => options.success({ confirm, cancel: !confirm }),
    );
  }

  it("草稿存在时输入栏仍可见，可再次提交解析", async () => {
    const wrapper = await mountPage();
    const sse = await startAnalysis(wrapper);
    await emit(sse, { event: "parsed", data: firstBatch });
    await emit(sse, { event: "awaiting_confirmation", data: { session_id: "sess-first" } });

    expect(wrapper.find(".speech-input").exists()).toBe(true);
    await wrapper.find(".speech-input").setValue("再记一笔 30");
    await wrapper.find(".analyze-button").trigger("click");
    await flushPromises();

    expect(sseCalls.length).toBe(2);
  });

  it("选择追加：保留旧草稿并把新一笔加到末尾", async () => {
    const wrapper = await mountPage();
    const sse = await startAnalysis(wrapper);
    await emit(sse, { event: "parsed", data: firstBatch });
    await emit(sse, { event: "awaiting_confirmation", data: { session_id: "sess-first" } });
    // H1：草稿存在时输入栏仍可见，用户才能真正触发第二次解析。
    expect(wrapper.find(".speech-input").exists()).toBe(true);
    answerModal(true);

    await emit(sse, { event: "parsed", data: nextSingle });

    expect(wrapper.find(".batch-card").text()).toContain("识别到 3 笔");
    await wrapper.find(".batch-card .confirm-button").trigger("click");
    await flushPromises();

    const payloads = confirmBill.mock.calls.map(([payload]: any[]) => payload);
    expect(payloads.map((payload) => payload.parsed.amount)).toEqual([12, 20, 30]);
    expect(payloads.map((payload) => payload.session_id)).toEqual([
      "sess-first:0",
      "sess-first:1",
      "sess-first:2",
    ]);
  });

  it("选择新批次：替换旧草稿，只确认新的一笔", async () => {
    const wrapper = await mountPage();
    const sse = await startAnalysis(wrapper);
    await emit(sse, { event: "parsed", data: firstBatch });
    await emit(sse, { event: "awaiting_confirmation", data: { session_id: "sess-first" } });
    answerModal(false);

    await emit(sse, { event: "parsed", data: nextSingle });

    expect(wrapper.find(".batch-card").exists()).toBe(false);
    await wrapper.find(".result-section.card .confirm-button").trigger("click");
    await flushPromises();

    expect(confirmBill).toHaveBeenCalledTimes(1);
    expect(confirmBill.mock.calls[0][0]).toMatchObject({
      is_batch_item: false,
      parsed: { amount: 30, category: "购物" },
    });
    expect(confirmBill.mock.calls[0][0].session_id).toMatch(/^sess-second-r\d+$/);
  });
});

describe("Bug N1 追问期间禁止确认", () => {
  it("多笔含未完成项被 normalize 丢弃后，追问期间确认按钮仍禁用且不会提交", async () => {
    const wrapper = await mountPage();
    const sse = await startAnalysis(wrapper);

    await emit(sse, {
      event: "parsed",
      data: {
        session_id: "sess-multi",
        items: [
          { type: "expense", amount: 12, category: "餐饮", bill_date: "2026-10-29" },
          { type: "expense", amount: 20, category: "交通", bill_date: "2026-10-29" },
          // 未完成项：normalizeParsed 会丢弃，确认键若按过滤后的数组生成即错位
          { type: "expense", amount: 30, category: null, bill_date: "2026-10-29" },
        ],
      },
    });

    const batchCard = wrapper.find(".batch-card");
    expect(batchCard.text()).toContain("识别到 2 笔");

    await emit(sse, {
      event: "clarify",
      data: { question: "第三笔缺少分类，请补充", session_id: "sess-multi" },
    });

    expect(wrapper.text()).toContain("第三笔缺少分类，请补充");
    const button = batchCard.find(".confirm-button");
    expect(button.attributes("disabled")).toBeDefined();

    await callSaveBills(wrapper);
    expect(confirmBill).not.toHaveBeenCalled();
  });

  it("追问清除且所有条目完整后恢复可确认，确认键按完整条目生成", async () => {
    const wrapper = await mountPage();
    const sse = await startAnalysis(wrapper);

    await emit(sse, {
      event: "parsed",
      data: {
        session_id: "sess-multi",
        items: [
          { type: "expense", amount: 12, category: "餐饮", bill_date: "2026-10-29" },
          { type: "expense", amount: 20, category: "交通", bill_date: "2026-10-29" },
        ],
      },
    });
    await emit(sse, {
      event: "clarify",
      data: { question: "还差一笔的金额", session_id: "sess-multi" },
    });

    const batchCard = wrapper.find(".batch-card");
    const button = batchCard.find(".confirm-button");
    expect(button.attributes("disabled")).toBeDefined();

    // awaiting_confirmation 会清空 clarificationQuestion，条目完整后应恢复可确认
    await emit(sse, {
      event: "awaiting_confirmation",
      data: { session_id: "sess-multi", items: [] },
    });
    expect(button.attributes("disabled")).toBeUndefined();

    await button.trigger("click");
    await flushPromises();

    expect(confirmBill).toHaveBeenCalledTimes(2);
    const payloads = confirmBill.mock.calls.map(([payload]: any[]) => payload);
    expect(payloads.map((payload) => payload.session_id)).toEqual([
      "sess-multi:0",
      "sess-multi:1",
    ]);
    expect(payloads.every((payload) => payload.is_batch_item === true)).toBe(true);
    expect(payloads.map((payload) => payload.parsed.amount)).toEqual([12, 20]);
  });

  it("单笔账单处于追问中时同样禁用确认并拒绝保存", async () => {
    const wrapper = await mountPage();
    const sse = await startAnalysis(wrapper, "早餐 12");

    await emit(sse, {
      event: "parsed",
      data: {
        session_id: "sess-single",
        items: [{ type: "expense", amount: 12, category: "餐饮", bill_date: "2026-10-29" }],
      },
    });

    const card = wrapper.find(".result-section.card");
    const button = card.find(".confirm-button");
    expect(button.attributes("disabled")).toBeUndefined();

    await emit(sse, {
      event: "clarify",
      data: { question: "请问是哪一天？", session_id: "sess-single" },
    });
    expect(button.attributes("disabled")).toBeDefined();

    await callSaveBills(wrapper);
    expect(confirmBill).not.toHaveBeenCalled();

    await emit(sse, {
      event: "awaiting_confirmation",
      data: { session_id: "sess-single" },
    });
    expect(button.attributes("disabled")).toBeUndefined();

    await button.trigger("click");
    await flushPromises();
    expect(confirmBill).toHaveBeenCalledTimes(1);
    expect(confirmBill.mock.calls[0][0]).toMatchObject({
      session_id: "sess-single",
      is_batch_item: false,
    });
  });
});

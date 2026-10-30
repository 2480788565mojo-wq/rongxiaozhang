import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { flushPromises, mount, type VueWrapper } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { onShow } from "@dcloudio/uni-app";
import * as budgetApi from "@/api/budgets";
import * as categoryApi from "@/api/categories";
import { useBudgetStore } from "@/stores/budget";
import { useLedgerStore } from "@/stores/ledger";
import BudgetPage from "./index.vue";

vi.mock("@/api/budgets");
vi.mock("@/api/categories");
vi.mock("@/api/ledgers", () => ({ getLedgers: vi.fn().mockResolvedValue([]) }));
vi.mock("echarts", () => ({
  init: vi.fn(),
  graphic: { LinearGradient: class {} },
}));

const ledger = {
  id: 1,
  name: "我的账本",
  type: "personal" as const,
  owner_id: 1,
  invite_code: null,
  settle_strategy: "equal",
  member_count: 1,
  created_at: null,
  members: [],
};
const stubs = { BudgetGauge: { template: '<div class="gauge-stub" />' } };
const wrappers: VueWrapper[] = [];
const unhandled: unknown[] = [];
const captureUnhandled = (reason: unknown) => {
  unhandled.push(reason);
};
type RejectionListener = (reason: unknown) => void;
// 只引入 @dcloudio/types 时没有完整 Node 类型，这里按需声明用到的 process 事件接口。
const nodeProcess = (
  globalThis as unknown as {
    process: {
      on: (event: string, listener: RejectionListener) => void;
      off: (event: string, listener: RejectionListener) => void;
    };
  }
).process;

function period() {
  const now = new Date();
  return { year: now.getFullYear(), month: now.getMonth() + 1 };
}

function mountBudget() {
  const pinia = createPinia();
  setActivePinia(pinia);
  const ledgerStore = useLedgerStore();
  ledgerStore.ledgers = [{ ...ledger }];
  ledgerStore.switchLedger(1);
  const wrapper = mount(BudgetPage, {
    global: { plugins: [pinia], stubs },
  });
  wrappers.push(wrapper);
  return wrapper;
}

/** 取预算页注册的 onShow 回调，用于模拟页面再次显示（例如跨月后返回）。 */
function triggerShow() {
  const calls = vi.mocked(onShow).mock.calls;
  const callback = calls[calls.length - 1]?.[0];
  if (!callback) throw new Error("预算页没有注册 onShow 回调");
  callback();
}

function totalInput(wrapper: VueWrapper): string {
  return (wrapper.find(".total-row input").element as HTMLInputElement).value;
}

function categoryInput(wrapper: VueWrapper, name: string): string {
  const row = wrapper
    .findAll(".category-row")
    .find((item) => item.text().trim().startsWith(name));
  if (!row) throw new Error(`未找到分类行：${name}`);
  return (row.find("input").element as HTMLInputElement).value;
}

/** 等待所有请求和 Vue 更新结束，再确认没有漏出未处理的 Promise 拒绝。 */
async function expectNoUnhandledRejection() {
  await flushPromises();
  await new Promise((resolve) => setTimeout(resolve, 0));
  await flushPromises();
  expect(unhandled).toEqual([]);
}

beforeEach(() => {
  vi.clearAllMocks();
  unhandled.length = 0;
  nodeProcess.on("unhandledRejection", captureUnhandled);
  const { year, month } = period();
  vi.mocked(categoryApi.getCategories).mockResolvedValue([]);
  vi.mocked(budgetApi.getBudgetStatus).mockResolvedValue({
    ledger_id: 1,
    year,
    month,
    statuses: [
      {
        category: "餐饮美食",
        spent: 320,
        budget: 1000,
        remaining: 680,
        percentage: 32,
        risk_level: "safe",
      },
    ],
  });
  vi.mocked(budgetApi.getBudget).mockResolvedValue({
    ledger_id: 1,
    year,
    month,
    total_budget: 5000,
    category_budgets: { 餐饮美食: 1000 },
  });
});

afterEach(() => {
  wrappers.splice(0).forEach((wrapper) => wrapper.unmount());
  nodeProcess.off("unhandledRejection", captureUnhandled);
});

describe("预算页加载失败（F4）", () => {
  it("接口失败时显示错误和重新加载按钮，并清空上个月的输入，不产生未处理拒绝", async () => {
    vi.mocked(budgetApi.getBudget)
      .mockResolvedValueOnce({
        ledger_id: 1,
        year: period().year,
        month: period().month,
        total_budget: 5000,
        category_budgets: { 餐饮美食: 1000 },
      })
      .mockRejectedValue(new Error("预算服务不可用"));
    const wrapper = mountBudget();
    await flushPromises();

    expect(totalInput(wrapper)).toBe("5000");
    expect(categoryInput(wrapper, "餐饮美食")).toBe("1000");
    expect(wrapper.find(".load-error").exists()).toBe(false);

    // 模拟跨月后再次 onShow：接口失败，旧输入必须清空，错误必须可见。
    triggerShow();
    await flushPromises();

    expect(wrapper.find(".load-error").text()).toContain("预算服务不可用");
    expect(wrapper.find(".retry-load").text()).toContain("重新加载");
    expect(totalInput(wrapper)).toBe("");
    expect(useBudgetStore().statuses).toEqual([]);
    expect(categoryInput(wrapper, "餐饮美食")).toBe("");
    await expectNoUnhandledRejection();
  });

  it("点击“重新加载”会重新请求，成功后清除错误并回填数据", async () => {
    vi.mocked(budgetApi.getBudget).mockRejectedValueOnce(
      new Error("预算接口超时"),
    );
    const wrapper = mountBudget();
    await flushPromises();

    expect(wrapper.find(".load-error").text()).toContain("预算接口超时");
    expect(vi.mocked(budgetApi.getBudget)).toHaveBeenCalledTimes(1);

    const { year, month } = period();
    vi.mocked(budgetApi.getBudget).mockResolvedValue({
      ledger_id: 1,
      year,
      month,
      total_budget: 3000,
      category_budgets: { 餐饮美食: 800 },
    });
    await wrapper.find(".retry-load").trigger("click");
    await flushPromises();

    expect(vi.mocked(budgetApi.getBudget)).toHaveBeenCalledTimes(2);
    expect(vi.mocked(categoryApi.getCategories)).toHaveBeenCalledTimes(2);
    expect(vi.mocked(budgetApi.getBudgetStatus)).toHaveBeenCalledTimes(2);
    expect(wrapper.find(".load-error").exists()).toBe(false);
    expect(totalInput(wrapper)).toBe("3000");
    expect(categoryInput(wrapper, "餐饮美食")).toBe("800");
    await expectNoUnhandledRejection();
  });

  const failures = [
    {
      name: "分类接口",
      message: "分类接口异常",
      inject: () =>
        vi
          .mocked(categoryApi.getCategories)
          .mockRejectedValue(new Error("分类接口异常")),
    },
    {
      name: "预算状态接口",
      message: "预算状态接口异常",
      inject: () =>
        vi
          .mocked(budgetApi.getBudgetStatus)
          .mockRejectedValue(new Error("预算状态接口异常")),
    },
    {
      name: "预算接口",
      message: "预算接口异常",
      inject: () =>
        vi
          .mocked(budgetApi.getBudget)
          .mockRejectedValue(new Error("预算接口异常")),
    },
  ];

  it.each(failures)(
    "$name 失败时显示错误和重试按钮，不产生未处理拒绝",
    async ({ message, inject }) => {
      inject();
      const wrapper = mountBudget();
      await flushPromises();

      expect(wrapper.find(".load-error").text()).toContain(message);
      expect(wrapper.find(".retry-load").exists()).toBe(true);
      expect(totalInput(wrapper)).toBe("");
      await expectNoUnhandledRejection();
    },
  );
});

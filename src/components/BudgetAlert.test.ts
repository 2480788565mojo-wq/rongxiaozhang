import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import BudgetAlert from "./BudgetAlert.vue";
import { useBudgetStore } from "@/stores/budget";
import type { BudgetAlertData } from "@/types";

const warningData: BudgetAlertData = {
  risk_level: "warning",
  category: "餐饮",
  spent: 850,
  budget: 1000,
  remaining: 150,
  percentage: 85,
  message: "本月预算已使用 85%",
};

const blockedData: BudgetAlertData = {
  risk_level: "blocked",
  category: "购物",
  spent: 1250,
  budget: 1000,
  remaining: -250,
  percentage: 125,
};

function setup() {
  const pinia = createPinia();
  setActivePinia(pinia);
  const store = useBudgetStore();
  const mountAlert = () => mount(BudgetAlert, { global: { plugins: [pinia] } });
  return { store, mountAlert };
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("BudgetAlert 预算告警弹层", () => {
  it("warning：黄色警示态、85% 标题、分类与明细，只有一个“知道了”且点击后隐藏", async () => {
    const { store, mountAlert } = setup();
    store.showAlert(warningData);
    const wrapper = mountAlert();
    const overlay = wrapper.find(".budget-overlay");

    expect(overlay.exists()).toBe(true);
    expect(overlay.classes()).toContain("is-warning");
    expect(overlay.classes()).not.toContain("is-blocked");
    expect(wrapper.find(".budget-title").text().trim()).toBe("预算已使用 85%");
    expect(wrapper.find(".budget-category").text().trim()).toBe("餐饮");
    expect(wrapper.find(".budget-detail").text().trim()).toBe(
      "已花 ¥850.00 / ¥1000.00",
    );
    expect(wrapper.find(".budget-remaining").exists()).toBe(false);
    expect(wrapper.findAll("button")).toHaveLength(1);
    expect(wrapper.find(".budget-cancel").exists()).toBe(false);
    expect(wrapper.find(".budget-confirm").text().trim()).toBe("知道了");

    await wrapper.find(".budget-confirm").trigger("click");

    expect(wrapper.find(".budget-overlay").exists()).toBe(false);
    expect(store.alertVisible).toBe(false);
  });

  it("blocked：红色阻断态、超限标题与负数“超出”文案", () => {
    const { store, mountAlert } = setup();
    store.showAlert(blockedData);
    const wrapper = mountAlert();
    const overlay = wrapper.find(".budget-overlay");

    expect(overlay.exists()).toBe(true);
    expect(overlay.classes()).toContain("is-blocked");
    expect(overlay.classes()).not.toContain("is-warning");
    expect(wrapper.find(".budget-title").text().trim()).toBe("本月预算已超限");
    expect(wrapper.find(".budget-category").text().trim()).toBe("购物");
    expect(wrapper.find(".budget-detail").text().trim()).toBe(
      "已花 ¥1250.00 / ¥1000.00",
    );
    expect(wrapper.find(".budget-remaining").text().trim()).toBe("超出 ¥250.00");
  });

  it("回调流程：取消 + 仍然记账，确认后 resolve(true) 并隐藏", async () => {
    const { store, mountAlert } = setup();
    const resolve = vi.fn();
    store.showAlert(blockedData, resolve);
    const wrapper = mountAlert();

    expect(wrapper.findAll("button")).toHaveLength(2);
    expect(wrapper.find(".budget-cancel").text().trim()).toBe("取消");
    expect(wrapper.find(".budget-confirm").text().trim()).toBe("仍然记账");

    await wrapper.find(".budget-confirm").trigger("click");

    expect(resolve).toHaveBeenCalledTimes(1);
    expect(resolve).toHaveBeenCalledWith(true);
    expect(store.alertVisible).toBe(false);
    expect(wrapper.find(".budget-overlay").exists()).toBe(false);
  });

  it("回调流程：取消后 resolve(false) 并隐藏", async () => {
    const { store, mountAlert } = setup();
    const resolve = vi.fn();
    store.showAlert(warningData, resolve);
    const wrapper = mountAlert();

    await wrapper.find(".budget-cancel").trigger("click");

    expect(resolve).toHaveBeenCalledTimes(1);
    expect(resolve).toHaveBeenCalledWith(false);
    expect(store.alertVisible).toBe(false);
    expect(wrapper.find(".budget-overlay").exists()).toBe(false);
  });

  it("无动作回调：没有“取消”，“知道了”只关闭弹层", async () => {
    const { store, mountAlert } = setup();
    store.showAlert(warningData);
    const wrapper = mountAlert();

    expect(wrapper.find(".budget-cancel").exists()).toBe(false);
    expect(wrapper.find(".budget-confirm").text().trim()).toBe("知道了");

    await wrapper.find(".budget-confirm").trigger("click");

    expect(store.alertVisible).toBe(false);
    expect(wrapper.find(".budget-overlay").exists()).toBe(false);
  });

  it("store.showAlert 不再调用 uni.showModal", () => {
    const { store } = setup();
    const modalSpy = vi.mocked(uni.showModal);
    const resolve = vi.fn();

    store.showAlert(blockedData, resolve);

    expect(modalSpy).not.toHaveBeenCalled();
    expect(store.alertVisible).toBe(true);
    expect(store.alertData).toMatchObject({ risk_level: "blocked", category: "购物" });
    expect(store.hasAlertAction).toBe(true);

    store.cancelAlert();

    expect(resolve).toHaveBeenCalledWith(false);
    expect(store.alertVisible).toBe(false);
    expect(store.hasAlertAction).toBe(false);
  });

  it("409 的 resolver 不被后到的 SSE 告警覆盖", () => {
    const { store } = setup();
    const resolve = vi.fn();

    // 后端先发 SSE、再返回 409，两种到达顺序都不能丢 resolver。
    store.showAlert(warningData, resolve);
    store.showAlert(blockedData);

    expect(store.alertVisible).toBe(true);
    expect(store.alertData?.risk_level).toBe("blocked");
    expect(store.hasAlertAction).toBe(true);

    store.confirmAlert();

    expect(resolve).toHaveBeenCalledTimes(1);
    expect(resolve).toHaveBeenCalledWith(true);
    expect(store.alertVisible).toBe(false);
  });

  it("dismiss 会以 false 结束挂起的 409 Promise", () => {
    const { store } = setup();
    const resolve = vi.fn();

    store.showAlert(warningData, resolve);
    store.dismissAlert();

    expect(resolve).toHaveBeenCalledWith(false);
    expect(store.alertVisible).toBe(false);
    expect(store.hasAlertAction).toBe(false);
  });

  it("clear（退出/换账号）会以 false 结束挂起的 409 Promise", () => {
    const { store } = setup();
    const resolve = vi.fn();

    store.showAlert(blockedData, resolve);
    store.clear();

    expect(resolve).toHaveBeenCalledWith(false);
    expect(store.hasAlertAction).toBe(false);
  });

  it("SSE 先到、409 的 resolver 后到：仍然安装并可确认结算", () => {
    const { store } = setup();
    const resolve = vi.fn();

    // SSE 告警没有 resolver，先弹出；随后 409 处理器才安装 resolver。
    store.showAlert(warningData);
    expect(store.alertVisible).toBe(true);
    expect(store.hasAlertAction).toBe(false);

    store.showAlert(blockedData, resolve);
    expect(store.hasAlertAction).toBe(true);
    expect(store.alertData?.risk_level).toBe("blocked");

    store.confirmAlert();

    expect(resolve).toHaveBeenCalledTimes(1);
    expect(resolve).toHaveBeenCalledWith(true);
    expect(store.alertVisible).toBe(false);
  });

  it("重复 confirm 只结算一次，不会重复 resolve", () => {
    const { store } = setup();
    const resolve = vi.fn();

    store.showAlert(blockedData, resolve);
    store.confirmAlert();
    store.confirmAlert();

    expect(resolve).toHaveBeenCalledTimes(1);
    expect(resolve).toHaveBeenCalledWith(true);
    expect(store.hasAlertAction).toBe(false);
  });

  it("无挂起 resolver 时 dismiss/clear 安全，且不影响后续新的 resolver", () => {
    const { store } = setup();

    expect(() => store.dismissAlert()).not.toThrow();
    expect(() => store.clear()).not.toThrow();
    expect(store.alertVisible).toBe(false);
    expect(store.alertData).toBeNull();

    const resolve = vi.fn();
    store.showAlert(warningData, resolve);
    expect(store.hasAlertAction).toBe(true);

    store.showAlert(blockedData);

    expect(store.hasAlertAction).toBe(true);
    store.confirmAlert();
    expect(resolve).toHaveBeenCalledTimes(1);
  });
});

function pageSource(page: string) {
  return readFileSync(
    resolve(process.cwd(), "src", "pages", page, "index.vue"),
    "utf8",
  );
}

describe("预算告警接线（源码级）", () => {
  it("transcribe 的 409 分支使用 budgetStore.showAlert，保存流程不再出现 uni.showModal", () => {
    const source = pageSource("transcribe");
    expect(source).toContain("budgetStore.showAlert(");
    const saveBillsSource = source.slice(
      source.indexOf("async function saveBills"),
      source.indexOf("function reset"),
    );
    expect(saveBillsSource).not.toContain("uni.showModal");

    const alertPath = source.slice(
      source.indexOf("error.statusCode !== 409"),
      source.indexOf("if (!confirmed)"),
    );
    expect(alertPath.length).toBeGreaterThan(0);
    expect(alertPath).toContain("budgetStore.showAlert");
    expect(alertPath).not.toContain("uni.showModal");
  });

  it.each(["index", "bills", "stats", "settings", "transcribe"])(
    "%s 页面挂载了 <BudgetAlert />",
    (page) => {
      const source = pageSource(page);
      expect(source).toContain("<BudgetAlert />");
      expect(source).toContain("@/components/BudgetAlert.vue");
    },
  );

  it("预算 store 自身不再依赖 uni.showModal", () => {
    const source = readFileSync(
      resolve(process.cwd(), "src", "stores", "budget.ts"),
      "utf8",
    );
    expect(source).not.toContain("uni.showModal");
    expect(source).toContain("hasAlertAction");
  });
});

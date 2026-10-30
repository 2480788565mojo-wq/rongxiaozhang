import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { getBills } from "@/api/bills";
import { useBillStore } from "@/stores/bill";
import type { Bill, BillListResponse } from "@/types";

vi.mock("@/api/bills", () => ({
  getBills: vi.fn(),
}));

function bill(id: number, month: number): Bill {
  return {
    id,
    ledger_id: 1,
    creator_id: 1,
    type: "expense",
    amount: id,
    category: "餐饮",
    subcategory: null,
    account: null,
    note: null,
    bill_date: `2026-${String(month).padStart(2, "0")}-01`,
    raw_input: null,
    ai_parsed: false,
    created_at: "2026-01-01T00:00:00",
    shares: [],
  };
}

function pageOf(items: Bill[], total: number, page = 1): BillListResponse {
  return { items, total, page, page_size: 20 };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((done, fail) => {
    resolve = done;
    reject = fail;
  });
  return { promise, resolve, reject };
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(getBills).mockReset();
  setActivePinia(createPinia());
});

describe("billStore.fetchBills 请求竞态", () => {
  it("旧筛选的迟到响应不能覆盖新筛选结果", async () => {
    const oldPage = deferred<BillListResponse>();
    const newPage = deferred<BillListResponse>();
    vi.mocked(getBills)
      .mockReturnValueOnce(oldPage.promise)
      .mockReturnValueOnce(newPage.promise);

    const store = useBillStore();
    const oldRequest = store.fetchBills(1, true, { month: 9 });
    const newRequest = store.fetchBills(1, true, { month: 10 });

    newPage.resolve(pageOf([bill(10, 10)], 1));
    await newRequest;
    expect(store.bills.map((item) => item.id)).toEqual([10]);
    expect(store.total).toBe(1);
    expect(store.loading).toBe(false);

    // 迟到的旧响应返回空数组，全部状态保持新请求的结果。
    oldPage.resolve(pageOf([bill(9, 9)], 1));
    await expect(oldRequest).resolves.toEqual([]);
    expect(store.bills.map((item) => item.id)).toEqual([10]);
    expect(store.total).toBe(1);
    expect(store.loading).toBe(false);
  });

  it("退出/切换账号 clear 后，旧请求不能回填账单", async () => {
    const pending = deferred<BillListResponse>();
    vi.mocked(getBills).mockReturnValueOnce(pending.promise);
    const store = useBillStore();
    const request = store.fetchBills(1, true, { month: 9 });

    store.clear();
    pending.resolve(pageOf([bill(9, 9)], 1));
    await request;

    expect(store.bills).toEqual([]);
    expect(store.total).toBe(0);
    expect(store.page).toBe(1);
  });

  it("加载更多期间切换筛选，旧页不能追加到新列表", async () => {
    const loadMore = deferred<BillListResponse>();
    const reset = deferred<BillListResponse>();
    vi.mocked(getBills)
      .mockReturnValueOnce(loadMore.promise)
      .mockReturnValueOnce(reset.promise);

    const store = useBillStore();
    store.bills = [bill(1, 9)];
    store.page = 2;
    const moreRequest = store.fetchBills(1, false, { month: 9 });
    const resetRequest = store.fetchBills(1, true, { month: 10 });
    expect(getBills).toHaveBeenNthCalledWith(1, expect.objectContaining({ page: 2, month: 9 }));
    expect(getBills).toHaveBeenNthCalledWith(2, expect.objectContaining({ page: 1, month: 10 }));

    reset.resolve(pageOf([bill(10, 10)], 1));
    await resetRequest;
    loadMore.resolve(pageOf([bill(2, 9)], 2, 2));
    await expect(moreRequest).resolves.toEqual([]);

    expect(store.bills.map((item) => item.id)).toEqual([10]);
    expect(store.total).toBe(1);
    expect(store.loading).toBe(false);
  });

  it("并发两次加载更多时旧页不会重复追加", async () => {
    const firstPage = deferred<BillListResponse>();
    const secondPage = deferred<BillListResponse>();
    vi.mocked(getBills)
      .mockReturnValueOnce(firstPage.promise)
      .mockReturnValueOnce(secondPage.promise);

    const store = useBillStore();
    store.bills = [bill(1, 9)];
    store.total = 3;
    store.page = 2;
    const firstRequest = store.fetchBills(1, false, { month: 9 });
    const secondRequest = store.fetchBills(1, false, { month: 9 });

    secondPage.resolve(pageOf([bill(2, 9)], 3, 2));
    await secondRequest;
    expect(store.bills.map((item) => item.id)).toEqual([1, 2]);

    firstPage.resolve(pageOf([bill(2, 9)], 3, 2));
    await expect(firstRequest).resolves.toEqual([]);
    expect(store.bills.map((item) => item.id)).toEqual([1, 2]);
    expect(store.total).toBe(3);
    expect(store.loading).toBe(false);
  });

  it("旧请求报错不会清除新请求的 loading", async () => {
    const oldPage = deferred<BillListResponse>();
    const newPage = deferred<BillListResponse>();
    vi.mocked(getBills)
      .mockReturnValueOnce(oldPage.promise)
      .mockReturnValueOnce(newPage.promise);

    const store = useBillStore();
    const oldRequest = store.fetchBills(1, true, { month: 9 });
    const newRequest = store.fetchBills(1, true, { month: 10 });

    oldPage.reject(new Error("旧请求失败"));
    await expect(oldRequest).rejects.toThrow("旧请求失败");
    expect(store.loading).toBe(true);
    expect(store.bills).toEqual([]);
    expect(store.total).toBe(0);

    newPage.resolve(pageOf([bill(10, 10)], 1));
    await newRequest;
    expect(store.loading).toBe(false);
    expect(store.bills.map((item) => item.id)).toEqual([10]);
    expect(store.total).toBe(1);
  });

  it("旧加载更多的迟到成功响应不会提前结束新重置的 loading", async () => {
    const morePage = deferred<BillListResponse>();
    const resetPage = deferred<BillListResponse>();
    vi.mocked(getBills)
      .mockReturnValueOnce(morePage.promise)
      .mockReturnValueOnce(resetPage.promise);

    const store = useBillStore();
    store.bills = [bill(1, 9)];
    store.total = 2;
    store.page = 2;
    const moreRequest = store.fetchBills(1, false, { month: 9 });
    const resetRequest = store.fetchBills(1, true, { month: 10 });

    morePage.resolve(pageOf([bill(2, 9)], 2, 2));
    await expect(moreRequest).resolves.toEqual([]);
    expect(store.loading).toBe(true);
    expect(store.bills.map((item) => item.id)).toEqual([1]);
    expect(store.total).toBe(2);

    resetPage.resolve(pageOf([bill(10, 10)], 1));
    await resetRequest;
    expect(store.loading).toBe(false);
    expect(store.bills.map((item) => item.id)).toEqual([10]);
    expect(store.total).toBe(1);
  });

  it("重置请求固定请求第 1 页并先复位 page", async () => {
    const resetPage = deferred<BillListResponse>();
    vi.mocked(getBills).mockReturnValueOnce(resetPage.promise);

    const store = useBillStore();
    store.bills = [bill(1, 9), bill(2, 9)];
    store.total = 5;
    store.page = 3;

    const request = store.fetchBills(1, true, { month: 10 });
    expect(store.page).toBe(1);
    expect(getBills).toHaveBeenCalledWith(expect.objectContaining({ page: 1, month: 10 }));

    resetPage.resolve(pageOf([bill(10, 10)], 1));
    await request;
    expect(store.page).toBe(1);
    expect(store.bills.map((item) => item.id)).toEqual([10]);
    expect(store.total).toBe(1);
  });
});

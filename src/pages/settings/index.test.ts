import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { flushPromises, mount, type VueWrapper } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { useUserStore } from "@/stores/user";
import * as authApi from "@/api/auth";
import SettingsPage from "./index.vue";

vi.mock("@/api/auth");
vi.mock("@/api/bills");
vi.mock("@/api/accounts");
vi.mock("@/api/categories");

const wrappers: VueWrapper[] = [];
let anchorClick: ReturnType<typeof vi.fn>;
let createObjectURL: ReturnType<typeof vi.fn>;
let revokeObjectURL: ReturnType<typeof vi.fn>;
let downloadedFile: { name: string; href: string } | null = null;

function mountSettings() {
  const pinia = createPinia();
  setActivePinia(pinia);
  const wrapper = mount(SettingsPage, { global: { plugins: [pinia] } });
  wrappers.push(wrapper);
  return { wrapper, userStore: useUserStore() };
}

function menuRow(wrapper: VueWrapper, label: string) {
  const row = wrapper
    .findAll(".menu view")
    .find((item) => item.text().trim().startsWith(label));
  if (!row) throw new Error(`未找到菜单项：${label}`);
  return row;
}

beforeEach(() => {
  vi.clearAllMocks();
  if (!(uni as any).reLaunch) (uni as any).reLaunch = vi.fn();
  downloadedFile = null;
  createObjectURL = vi.fn(() => "blob:mock-account-export");
  revokeObjectURL = vi.fn();
  (URL as any).createObjectURL = createObjectURL;
  (URL as any).revokeObjectURL = revokeObjectURL;
  anchorClick = vi.fn(function (this: HTMLAnchorElement) {
    downloadedFile = { name: this.download, href: this.href };
  });
  vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(
    anchorClick as any,
  );
  (globalThis as any).wx = {
    env: { USER_DATA_PATH: "/tmp" },
    getFileSystemManager: () => ({ writeFile: vi.fn() }),
  };
});

afterEach(() => {
  wrappers.splice(0).forEach((wrapper) => wrapper.unmount());
  vi.restoreAllMocks();
  delete (globalThis as any).wx;
});

describe("设置页账号数据导出", () => {
  it("点击“导出账号数据（服务器）”调用 API 并下载含服务器数据的 JSON", async () => {
    vi.mocked(authApi.exportAccount).mockResolvedValue({
      exported_at: "2026-10-29T09:00:00+00:00",
      user: { id: 1, nickname: "阿荣" },
      ledgers: [{ id: 5, name: "我的账本" }],
      bills: [{ id: 9, amount: 12.5 }],
      accounts: [],
      budgets: [],
      categories: [],
      insights: [],
    });
    const { wrapper } = mountSettings();
    await flushPromises();

    await menuRow(wrapper, "导出账号数据（服务器）").trigger("click");
    await flushPromises();

    expect(authApi.exportAccount).toHaveBeenCalledTimes(1);
    expect(createObjectURL).toHaveBeenCalledTimes(1);
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:mock-account-export");
    expect(anchorClick).toHaveBeenCalledTimes(1);
    expect(downloadedFile?.name).toMatch(
      /^荣小账账号数据_\d{4}-\d{2}-\d{2}\.json$/,
    );

    const blob = createObjectURL.mock.calls[0][0] as Blob;
    const content = JSON.parse(await blob.text());
    expect(content.user).toEqual({ id: 1, nickname: "阿荣" });
    expect(content.ledgers).toEqual([{ id: 5, name: "我的账本" }]);
    expect(content.bills).toEqual([{ id: 9, amount: 12.5 }]);
  });
});

describe("设置页永久删除账号", () => {
  it("弹窗确认后调用删除 API、退出登录并回到首页", async () => {
    vi.mocked(authApi.deleteAccount).mockResolvedValue(undefined);
    vi.mocked(uni.showModal).mockImplementation((options: any) => {
      void options.success?.({ confirm: true, cancel: false });
    });
    const { wrapper, userStore } = mountSettings();
    await flushPromises();
    const logoutSpy = vi.spyOn(userStore, "logout");

    await menuRow(wrapper, "永久删除账号").trigger("click");
    await flushPromises();

    expect(uni.showModal).toHaveBeenCalledTimes(1);
    const modal = vi.mocked(uni.showModal).mock.calls[0][0] as any;
    expect(modal.title).toBe("永久删除账号");
    expect(modal.confirmText).toBe("永久删除");
    expect(modal.content).toContain("无法恢复");
    expect(authApi.deleteAccount).toHaveBeenCalledTimes(1);
    expect(logoutSpy).toHaveBeenCalledTimes(1);

    await new Promise((resolve) => setTimeout(resolve, 600));
    expect(uni.reLaunch).toHaveBeenCalledWith({ url: "/pages/index/index" });
  });

  it("弹窗取消时不调用删除 API 也不退出登录", async () => {
    vi.mocked(uni.showModal).mockImplementation((options: any) => {
      void options.success?.({ confirm: false, cancel: true });
    });
    const { wrapper, userStore } = mountSettings();
    await flushPromises();
    const logoutSpy = vi.spyOn(userStore, "logout");

    await menuRow(wrapper, "永久删除账号").trigger("click");
    await flushPromises();

    expect(authApi.deleteAccount).not.toHaveBeenCalled();
    expect(logoutSpy).not.toHaveBeenCalled();
    expect(uni.reLaunch).not.toHaveBeenCalled();
  });

  it("删除失败时提示错误且不退出登录", async () => {
    vi.mocked(authApi.deleteAccount).mockRejectedValue(new Error("网络异常"));
    vi.mocked(uni.showModal).mockImplementation((options: any) => {
      void options.success?.({ confirm: true, cancel: false });
    });
    const { wrapper, userStore } = mountSettings();
    await flushPromises();
    const logoutSpy = vi.spyOn(userStore, "logout");

    await menuRow(wrapper, "永久删除账号").trigger("click");
    await flushPromises();

    expect(uni.showToast).toHaveBeenCalledWith({
      title: "网络异常",
      icon: "none",
    });
    expect(logoutSpy).not.toHaveBeenCalled();
    expect(uni.reLaunch).not.toHaveBeenCalled();
  });
});

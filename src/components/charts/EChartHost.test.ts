import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";
import EChartHost from "./EChartHost.vue";

describe("EChartHost 图表生命周期", () => {
  it("并发初始化只创建一个实例，尺寸变化时重绘，卸载时释放", async () => {
    const canvas = document.createElement("canvas");
    vi.spyOn(canvas, "getBoundingClientRect").mockReturnValue({ width: 300, height: 200 } as DOMRect);
    const canvasLookup = vi.spyOn(document, "getElementById").mockReturnValue(canvas);
    const originalResizeObserver = globalThis.ResizeObserver;
    const observer = { observe: vi.fn(), disconnect: vi.fn() };
    class FakeResizeObserver {
      observe = observer.observe;
      disconnect = observer.disconnect;
    }
    vi.stubGlobal("ResizeObserver", FakeResizeObserver);
    const canvasNode: Record<string, unknown> = {};
    const query: any = {
      in: vi.fn(() => query),
      select: vi.fn(() => query),
      fields: vi.fn(() => query),
      exec: vi.fn((callback: (result: any[]) => void) => callback([{ node: canvasNode, width: 300, height: 200 }])),
    };
    (uni as any).createSelectorQuery = vi.fn(() => query);
    (uni as any).getSystemInfoSync = vi.fn(() => ({ pixelRatio: 2 }));
    (uni as any).onWindowResize = vi.fn();
    (uni as any).offWindowResize = vi.fn();

    const chart = {
      isDisposed: vi.fn(() => false),
      resize: vi.fn(),
      dispose: vi.fn(),
    };
    const echarts = { init: vi.fn(() => chart) };
    const wrapper = mount(EChartHost);
    const exposed = wrapper.vm as any;
    try {
      const [first, second] = await Promise.all([exposed.init(echarts), exposed.init(echarts)]);
      expect(first).toBe(chart);
      expect(second).toBe(chart);
      expect(echarts.init).toHaveBeenCalledTimes(1);

      exposed.resize();
      expect(chart.resize).toHaveBeenCalledWith({ width: 300, height: 200 });

      wrapper.unmount();
      expect(chart.dispose).toHaveBeenCalledTimes(1);
      expect(observer.disconnect).toHaveBeenCalled();
      expect((uni as any).offWindowResize).toHaveBeenCalled();
    } finally {
      if (wrapper.exists()) wrapper.unmount();
      canvasLookup.mockRestore();
      if (originalResizeObserver) vi.stubGlobal("ResizeObserver", originalResizeObserver);
      else delete (globalThis as any).ResizeObserver;
      delete (uni as any).createSelectorQuery;
      delete (uni as any).getSystemInfoSync;
      delete (uni as any).onWindowResize;
      delete (uni as any).offWindowResize;
    }
  });
});

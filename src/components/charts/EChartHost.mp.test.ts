import { afterEach, describe, expect, it, vi } from 'vitest';
import { mount } from '@vue/test-utils';
import EChartHost from './EChartHost.vue';
import echarts from './echarts-lite';
function selector(target: () => any) {
  const query: any = { in: () => query, select: () => query, fields: () => query, exec: (cb: any) => cb([target()]) };
  (uni as any).createSelectorQuery = () => query;
  (uni as any).getSystemInfoSync = () => ({ pixelRatio: 2 });
}
afterEach(() => { vi.useRealTimers(); });
describe('微信画布分支', () => {
  it('等待异步画布节点和非零尺寸后再创建图表', async () => {
    vi.useFakeTimers(); let attempts = 0; const node = {};
    selector(() => ++attempts < 3 ? null : { node, width: 320, height: 220 });
    const chart = { dispose: vi.fn(), isDisposed: () => false };
    const engine = { init: vi.fn(() => chart) };
    const wrapper = mount(EChartHost);
    const ready = (wrapper.vm as any).init(engine);
    await vi.advanceTimersByTimeAsync(300);
    await expect(ready).resolves.toBe(chart);
    expect(engine.init).toHaveBeenCalledTimes(1);
    expect(engine.init).toHaveBeenCalledWith(node, undefined, expect.objectContaining({ renderer: 'canvas' }));
    wrapper.unmount();
  });
  it('真实 ECharts 在微信样式画布上输出柱状图和饼图绘制指令', async () => {
    const draw = vi.fn();
    const node: any = { width: 320, height: 220 };
    const ctx: any = new Proxy({ canvas: node, measureText: (text: string) => ({ width: text.length * 10 }),
      createLinearGradient: () => ({ addColorStop() {} }), createRadialGradient: () => ({ addColorStop() {} }) },
      { get: (target, name) => name in target ? (target as any)[name] : draw });
    node.getContext = () => ctx;
    selector(() => ({ node, width: 320, height: 220 }));
    const wrapper = mount(EChartHost);
    const chart = await (wrapper.vm as any).init(echarts);
    expect(typeof node.addEventListener).toBe('function');
    expect(typeof node.removeEventListener).toBe('function');
    chart.setOption({ animation: false, xAxis: { type: 'category', data: ['08','09'] }, yAxis: {}, series: [{ type: 'line', data: [20,40] }] });
    expect(draw.mock.calls.length).toBeGreaterThan(10); draw.mockClear();
    chart.setOption({ animation: false, series: [{ type: 'pie', data: [{ name: '餐饮', value: 20 },{ name: '交通', value: 10 }] }] }, true);
    expect(draw.mock.calls.length).toBeGreaterThan(10); wrapper.unmount();
  });
});

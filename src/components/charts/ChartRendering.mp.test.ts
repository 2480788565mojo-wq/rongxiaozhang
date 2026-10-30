import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { mount, type VueWrapper } from '@vue/test-utils';
import TrendLine from './TrendLine.vue';
import CategoryPie from './CategoryPie.vue';
import BudgetGauge from './BudgetGauge.vue';
import EChartHost from './EChartHost.vue';
import echarts from './echarts-lite';

// zrender 在模块加载时保存 requestAnimationFrame；使用可控时钟驱动完整动画。
vi.hoisted(() => {
  window.requestAnimationFrame = callback => setTimeout(() => callback(Date.now()), 16) as unknown as number;
});

type DrawCall = { method: string; args: any[]; fillStyle: unknown; strokeStyle: unknown };
let wrapper: VueWrapper | undefined;

function nativeCanvas() {
  const calls: DrawCall[] = [];
  const node: any = { width: 320, height: 240 };
  const values: Record<string | symbol, any> = {
    canvas: node,
    measureText: (text: string) => ({ width: String(text).length * 8 }),
    createLinearGradient: () => ({ addColorStop() {} }),
    createRadialGradient: () => ({ addColorStop() {} }),
  };
  const context = new Proxy(values, {
    get(target, method) {
      if (method in target) return target[method];
      return (...args: any[]) => calls.push({ method: String(method), args, fillStyle: target.fillStyle, strokeStyle: target.strokeStyle });
    },
  });
  node.getContext = () => context;
  let width = 320;
  const query: any = { in: () => query, select: () => query, fields: () => query, exec: (callback: any) => callback([{ node, width, height: 240 }]) };
  (uni as any).createSelectorQuery = () => query;
  (uni as any).getSystemInfoSync = () => ({ pixelRatio: 2 });
  (uni as any).onWindowResize = vi.fn();
  (uni as any).offWindowResize = vi.fn();
  return { calls, node, setWidth: (next: number) => { width = next; } };
}

beforeEach(() => { vi.useFakeTimers(); });
afterEach(() => { wrapper?.unmount(); wrapper = undefined; vi.useRealTimers(); });

describe('微信端实际图表组件绘制', () => {
  it('趋势图画出每月的两条折线并响应数据更新', async () => {
    const canvas = nativeCanvas();
    wrapper = mount(TrendLine, { props: { data: [
      { period: '2026-08', income: 100, expense: 20 },
      { period: '2026-09', income: 200, expense: 80 },
    ] } });
    await vi.advanceTimersByTimeAsync(1000);
    expect(wrapper.find('.chart-retry').exists()).toBe(false);
    const host = wrapper.findComponent(EChartHost).vm as any;
    const chart = await host.init(echarts);
    expect(chart.getOption().series.map((series: any) => series.type)).toEqual(['line', 'line']);
    // 两条折线都以真实线条绘制（stroke），而不是填充的柱子。
    for (const color of ['#ff3b30', '#34c759']) {
      expect(canvas.calls.some(call => call.method === 'stroke' && call.strokeStyle === color)).toBe(true);
    }
    // 检查 ECharts 算出的真实折线点位：同月两条系列共用横坐标，金额越大点位越高。
    const expensePoints = chart.getModel().getSeriesByIndex(0).getData().getLayout('points') as number[];
    const incomePoints = chart.getModel().getSeriesByIndex(1).getData().getLayout('points') as number[];
    expect(expensePoints).toHaveLength(4);
    expect(incomePoints).toHaveLength(4);
    for (let index = 0; index < 2; index++) {
      const expenseX = expensePoints[index * 2];
      const expenseY = expensePoints[index * 2 + 1];
      const incomeX = incomePoints[index * 2];
      const incomeY = incomePoints[index * 2 + 1];
      expect(Number.isFinite(expenseX) && Number.isFinite(expenseY)).toBe(true);
      expect(Number.isFinite(incomeX) && Number.isFinite(incomeY)).toBe(true);
      expect(incomeX).toBeCloseTo(expenseX);
      // 画布纵轴向下，支出金额更小，因此点位更靠下。
      expect(expenseY).toBeGreaterThan(incomeY);
      if (index > 0) {
        expect(expenseX).toBeGreaterThan(expensePoints[(index - 1) * 2]);
        // 金额从 20 涨到 80，折线点位应当向上移动。
        expect(expenseY).toBeLessThan(expensePoints[(index - 1) * 2 + 1]);
      }
    }
    canvas.calls.length = 0;
    await wrapper.setProps({ data: [{ period: '2026-10', income: 400, expense: 120 }] });
    await vi.advanceTimersByTimeAsync(1000);
    expect(canvas.calls.some(call => call.method === 'fillText' && call.args[0] === '10月')).toBe(true);
    expect(chart.getOption().series[0].data).toEqual([120]);
    expect(chart.getOption().series[1].data).toEqual([400]);
  });

  it('小屏下十二个月仍绘制两条折线，零收入落在零刻度上', async () => {
    const canvas = nativeCanvas();
    canvas.setWidth(280);
    wrapper = mount(TrendLine, { props: { data: Array.from({ length: 12 }, (_, index) => ({
      period: `2026-${String(index + 1).padStart(2, '0')}`,
      income: index === 0 ? 0 : 12000, expense: 10000,
    })) } });
    await vi.advanceTimersByTimeAsync(1000);
    const chart = await (wrapper.findComponent(EChartHost).vm as any).init(echarts);
    const expense = chart.getModel().getSeriesByIndex(0).getData();
    const income = chart.getModel().getSeriesByIndex(1).getData();
    const expensePoints = expense.getLayout('points') as number[];
    const incomePoints = income.getLayout('points') as number[];
    const zeroY = chart.convertToPixel({ yAxisIndex: 0 }, 0);
    expect(expensePoints).toHaveLength(24);
    expect(incomePoints).toHaveLength(24);
    for (let index = 0; index < 12; index++) {
      const x = expensePoints[index * 2];
      const y = expensePoints[index * 2 + 1];
      // 同一个月两条折线共用横坐标，不会像柱子那样左右并排偏移。
      expect(incomePoints[index * 2]).toBeCloseTo(x);
      expect(y).toBeLessThan(zeroY);
      if (index < 11) expect(expensePoints[(index + 1) * 2]).toBeGreaterThan(x);
      expect(canvas.calls.some(call => call.method === 'fillText' && call.args[0] === `${index + 1}月`)).toBe(true);
    }
    // 零收入必须落在零刻度线上，不能画出有高度的图形。
    expect(incomePoints[1]).toBeCloseTo(zeroY, 0);
    expect(incomePoints[3]).toBeLessThan(zeroY);
  });

  it('分类饼图首屏绘制出有面积的扇区', async () => {
    const canvas = nativeCanvas();
    wrapper = mount(CategoryPie, { props: { data: [
      { category: '餐饮', amount: 75, percentage: 75 },
      { category: '交通', amount: 25, percentage: 25 },
    ] } });
    await vi.advanceTimersByTimeAsync(1000);
    expect(wrapper.find('.chart-retry').exists()).toBe(false);
    expect(canvas.calls.some(call => call.method === 'arc' && call.args[2] > 30 && Math.abs(call.args[4] - call.args[3]) > 1)).toBe(true);
    expect(canvas.calls.some(call => call.method === 'fill' && call.fillStyle === '#4a90e2')).toBe(true);
  });

  it('预算仪表盘会真正绘制最终数值', async () => {
    const canvas = nativeCanvas();
    wrapper = mount(BudgetGauge, { props: { statuses: [
      { category: '餐饮', spent: 82, budget: 100, remaining: 18, percentage: 82, risk_level: 'warning' },
    ] } });
    await vi.advanceTimersByTimeAsync(1000);
    expect(wrapper.find('.chart-retry').exists()).toBe(false);
    expect(canvas.calls.some(call => call.method === 'fillText' && call.args[0] === '82%')).toBe(true);
  });

  it('画布尺寸变化后仍重新画出饼图', async () => {
    const canvas = nativeCanvas();
    wrapper = mount(CategoryPie, { props: { data: [{ category: '餐饮', amount: 75, percentage: 100 }] } });
    await vi.advanceTimersByTimeAsync(1000);
    canvas.calls.length = 0;
    canvas.setWidth(400);
    const host = wrapper.findComponent(EChartHost).vm as any;
    host.resize();
    await vi.advanceTimersByTimeAsync(1000);
    expect((await host.init(echarts)).getWidth()).toBe(400);
    expect(canvas.calls.some(call => call.method === 'fill' && call.fillStyle === '#4a90e2')).toBe(true);
  });
});

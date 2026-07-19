import { beforeEach, describe, expect, it, vi } from "vitest";
import { flushPromises, mount } from "@vue/test-utils";
import TrendLine from "./TrendLine.vue";
import CategoryPie from "./CategoryPie.vue";
import BudgetGauge from "./BudgetGauge.vue";

const chartMocks = vi.hoisted(() => ({
  init: vi.fn(),
  setOption: vi.fn(),
}));

vi.mock("echarts", () => ({
  graphic: {
    LinearGradient: class LinearGradient {
      constructor(...args: unknown[]) {
        Object.assign(this, { args });
      }
    },
  },
}));

vi.mock("./EChartHost.vue", () => ({
  default: {
    template: "<div class=\"chart-host-stub\" />",
    methods: { init: chartMocks.init },
  },
}));

function latestOption() {
  return chartMocks.setOption.mock.calls.at(-1)?.[0] as any;
}

beforeEach(() => {
  chartMocks.init.mockReset();
  chartMocks.setOption.mockReset();
  chartMocks.init.mockResolvedValue({ setOption: chartMocks.setOption });
});

describe("Apple 浅色图表主题", () => {
  it("趋势图使用浅色提示框并正确映射收支数据", async () => {
    mount(TrendLine, {
      props: {
        data: [
          { period: "2026-06", expense: 120, income: 500 },
          { period: "2026-07", expense: 80, income: 600 },
        ],
      },
    });
    await flushPromises();

    const option = latestOption();
    expect(option.tooltip).toMatchObject({
      trigger: "axis",
      backgroundColor: "#ffffff",
      borderColor: "#e5e5ea",
    });
    expect(option.series[0]).toMatchObject({ name: "支出", data: [120, 80] });
    expect(option.series[1]).toMatchObject({ name: "收入", data: [500, 600] });
  });

  it("趋势图不包含霓虹发光参数", async () => {
    mount(TrendLine, { props: { data: [{ period: "2026-07", expense: 80, income: 600 }] } });
    await flushPromises();

    expect(JSON.stringify(latestOption())).not.toMatch(/shadowBlur|shadowColor|glow/i);
  });

  it("分类环图使用柔和配色和白色分隔线", async () => {
    mount(CategoryPie, {
      props: {
        data: [
          { category: "餐饮美食", amount: 88, percentage: 55 },
          { category: "交通出行", amount: 72, percentage: 45 },
        ],
      },
    });
    await flushPromises();

    const option = latestOption();
    expect(option.color).toEqual(["#4a90e2", "#34c759", "#ff9f0a", "#7d6ee8", "#5ac8fa", "#ff7a73", "#8e8e93"]);
    expect(option.series[0].itemStyle).toMatchObject({ borderColor: "#ffffff", borderWidth: 4 });
    expect(option.series[0].data).toEqual([
      { name: "餐饮美食", value: 88 },
      { name: "交通出行", value: 72 },
    ]);
  });

  it.each([
    [60, "#4a90e2"],
    [85, "#ff9f0a"],
    [105, "#ff3b30"],
  ])("预算使用率 %s%% 显示对应状态色", async (percentage, expectedColor) => {
    mount(BudgetGauge, {
      props: {
        statuses: [{
          category: "餐饮美食",
          spent: percentage,
          budget: 100,
          remaining: 100 - percentage,
          percentage,
          risk_level: percentage >= 100 ? "blocked" : percentage >= 80 ? "warning" : "safe",
        }],
      },
    });
    await flushPromises();

    const gauge = latestOption().series[0];
    expect(gauge.progress.itemStyle.color).toBe(expectedColor);
    expect(gauge.detail.color).toBe(expectedColor);
  });

  it("预算仪表盘将显示百分比上限限制为 150%", async () => {
    mount(BudgetGauge, {
      props: {
        statuses: [{
          category: "餐饮美食",
          spent: 300,
          budget: 100,
          remaining: -200,
          percentage: 300,
          risk_level: "blocked",
        }],
      },
    });
    await flushPromises();

    expect(latestOption().series[0].data[0].value).toBe(150);
  });
});

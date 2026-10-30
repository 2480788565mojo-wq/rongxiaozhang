import { readFileSync } from "node:fs";
import { resolve } from "node:path";
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
  chartMocks.init.mockResolvedValue({ setOption: chartMocks.setOption, isDisposed: () => false });
});

describe("Apple 浅色图表主题", () => {
  it("趋势图使用浅色提示框并以折线面积图正确映射收支数据", async () => {
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
    // Spec 要求月度趋势为折线图：支出和收入两条系列都必须是 line。
    expect(option.series).toHaveLength(2);
    expect(option.series.map((series: any) => series.type)).toEqual(["line", "line"]);
    expect(option.series[0]).toMatchObject({ name: "支出", type: "line", data: [120, 80] });
    expect(option.series[1]).toMatchObject({ name: "收入", type: "line", data: [500, 600] });
    expect(option.series.every((series: any) => !series.stack && !series.smooth)).toBe(true);
    // 折线图使用线性坐标轴指示器，且数据点不向两侧留空。
    expect(option.tooltip.axisPointer).toMatchObject({ type: "line" });
    expect(option.xAxis.boundaryGap).toBe(false);
    // 两条系列都带折线样式与面积渐变，而不是柱子。
    for (const series of option.series) {
      expect(series.lineStyle).toMatchObject({ width: 3 });
      expect(series.lineStyle.color).toBeTruthy();
      expect(series.areaStyle).toBeTruthy();
      expect(series.areaStyle.color).toBeTruthy();
      expect(series.barWidth).toBeUndefined();
    }
    expect(option.xAxis.data).toEqual(["2026-06", "2026-07"]);
    expect(option.tooltip.valueFormatter(123.4)).toBe("¥123.40");
  });

  it("图表依赖与文档不再引用 uCharts", () => {
    const root = process.cwd();
    const scannedFiles = [
      "package.json",
      "package-lock.json",
      "AGENTS.md",
      "CLAUDE.md",
      "README.md",
      "docs/superpowers/specs/2026-07-14-rongxiaozhang-rebuild-design.md",
      "src/components/charts/TrendLine.vue",
      "src/components/charts/echarts-lite.ts",
    ];
    for (const file of scannedFiles) {
      expect(readFileSync(resolve(root, file), "utf8"), file).not.toMatch(/@qiun\/ucharts|ucharts/i);
    }
  });

  it("十二个月均显示短月份标签，金额轴缩写后仍保留完整金额提示", async () => {
    mount(TrendLine, { props: { data: Array.from({ length: 12 }, (_, index) => ({
      period: `2026-${String(index + 1).padStart(2, "0")}`, expense: index * 100, income: index * 10000,
    })) } });
    await flushPromises();

    const option = latestOption();
    expect(option.xAxis.axisLabel.interval).toBe(0);
    expect(option.xAxis.axisLabel.rotate).toBeGreaterThan(0);
    expect(option.xAxis.axisLabel.formatter("2026-09")).toBe("9月");
    expect(option.yAxis.axisLabel.formatter(120000)).toBe("¥12万");
    expect(option.yAxis.axisLabel.formatter(1500)).toBe("¥1.5千");
    expect(option.tooltip.valueFormatter(123456.78)).toBe("¥123456.78");
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

<template>
  <view class="chart"><EChartHost ref="chartRef" :height="440" /><button v-if="renderError" class="chart-retry" @click="render">图表加载失败，点击重试</button></view>
</template>

<script setup lang="ts">
import { nextTick, onMounted, ref, watch } from "vue";
import { onShow, onReady } from "@dcloudio/uni-app";
import echarts from "./echarts-lite";
import type { EChartsType as ECharts } from "echarts/core";
import type { EChartsOption } from "echarts";
import type { TrendPoint } from "@/types";
import EChartHost from "./EChartHost.vue";

const props = withDefaults(defineProps<{ data: TrendPoint[] }>(), { data: () => [] });
const chartRef = ref<any>(null);
let chart: ECharts | null = null;
const renderError = ref(false);

function option(): EChartsOption {
  return {
    backgroundColor: "transparent",
    animationDuration: 280,
    animationEasing: "cubicOut",
    grid: { left: 8, right: 12, top: 34, bottom: 8, containLabel: true },
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "line" },
      backgroundColor: "#ffffff",
      borderColor: "#e5e5ea",
      textStyle: { color: "#1d1d1f", fontFamily: "sans-serif" },
      valueFormatter: (value) => `¥${Number(value).toFixed(2)}`,
    },
    legend: { top: 0, right: 8, itemWidth: 12, textStyle: { color: "#86868b" } },
    xAxis: {
      type: "category",
      boundaryGap: false,
      // 轴上仅显示月份，完整年月保留给触摸提示，跨年数据也不会混淆。
      data: props.data.map((item) => item.period),
      axisLine: { lineStyle: { color: "#e5e5ea" } },
      axisTick: { show: false },
      axisLabel: {
        color: "#86868b", fontFamily: "sans-serif", fontSize: 10,
        interval: 0, rotate: props.data.length > 6 ? 45 : 0,
        formatter: (value: string) => `${Number(value.slice(5, 7))}月`,
      },
    },
    yAxis: {
      type: "value",
      splitNumber: 3,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: {
        color: "#86868b", fontFamily: "sans-serif", fontSize: 10,
        // 小屏幕缩短金额刻度，把横向空间留给折线；提示框仍显示精确金额。
        formatter: (value: number) => Math.abs(value) >= 10000 ? `¥${value / 10000}万`
          : Math.abs(value) >= 1000 ? `¥${value / 1000}千` : `¥${value}`,
      },
      splitLine: { show: true, lineStyle: { color: "#f0f0f2", type: "dashed" } },
    },
    series: [
      {
        name: "支出",
        type: "line",
        smooth: false,
        symbol: "circle",
        symbolSize: 6,
        showSymbol: props.data.length <= 12,
        data: props.data.map((item) => item.expense),
        lineStyle: { width: 3, color: "#ff3b30" },
        itemStyle: { color: "#ff3b30" },
        areaStyle: { color: "rgba(255, 59, 48, 0.08)" },
      },
      {
        name: "收入",
        type: "line",
        smooth: false,
        symbol: "circle",
        symbolSize: 6,
        showSymbol: props.data.length <= 12,
        data: props.data.map((item) => item.income),
        lineStyle: { width: 3, color: "#34c759" },
        itemStyle: { color: "#34c759" },
        areaStyle: { color: "rgba(52, 199, 89, 0.08)" },
      },
    ],
  };
}

async function render() {
  await nextTick();
  if (!chartRef.value) return;
  try {
    if (!chart || chart.isDisposed()) chart = await chartRef.value.init(echarts) as ECharts | null;
    if (!chart) { renderError.value = true; return; }
    chart.setOption(option(), true);
    renderError.value = false;
  } catch { renderError.value = true; }
}

onMounted(render);
onReady(render);
onShow(() => { void render(); chartRef.value?.resize(); });
watch(() => props.data, render, { deep: true });
</script>

<style scoped>
.chart { position: relative; width: 100%; height: 440rpx; }
.chart-retry { position: absolute; left: 10%; right: 10%; top: 35%; font-size: 26rpx; color: var(--color-text-secondary); background: var(--color-surface-muted); }
</style>

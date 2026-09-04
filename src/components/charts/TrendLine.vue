<template>
  <view class="chart"><EChartHost ref="chartRef" /></view>
</template>

<script setup lang="ts">
import { nextTick, onMounted, ref, watch } from "vue";
import echarts from "./echarts-lite";
import type { ECharts, EChartsOption } from "echarts";
import type { TrendPoint } from "@/types";
import EChartHost from "./EChartHost.vue";

const props = withDefaults(defineProps<{ data: TrendPoint[] }>(), { data: () => [] });
const chartRef = ref<any>(null);
let chart: ECharts | null = null;

function option(): EChartsOption {
  return {
    backgroundColor: "transparent",
    animationDuration: 280,
    animationEasing: "cubicOut",
    grid: { left: 8, right: 12, top: 34, bottom: 8, containLabel: true },
    tooltip: {
      trigger: "axis",
      backgroundColor: "#ffffff",
      borderColor: "#e5e5ea",
      textStyle: { color: "#1d1d1f", fontFamily: "sans-serif" },
      valueFormatter: (value) => `¥${Number(value).toFixed(2)}`,
    },
    legend: { top: 0, right: 8, itemWidth: 12, textStyle: { color: "#86868b" } },
    xAxis: {
      type: "category",
      boundaryGap: false,
      data: props.data.map((item) => item.period.slice(5)),
      axisLine: { lineStyle: { color: "#e5e5ea" } },
      axisTick: { show: false },
      axisLabel: { color: "#86868b", fontFamily: "sans-serif" },
    },
    yAxis: {
      type: "value",
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: "#86868b", fontFamily: "sans-serif", formatter: (value: number) => `¥${value}` },
      splitLine: { show: true, lineStyle: { color: "#f0f0f2", type: "dashed" } },
    },
    series: [
      {
        name: "支出",
        type: "line",
        smooth: true,
        symbolSize: 6,
        data: props.data.map((item) => item.expense),
        lineStyle: { color: "#ff3b30", width: 3 },
        itemStyle: { color: "#ff3b30", borderColor: "#ffffff", borderWidth: 2 },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: "rgba(255,59,48,.14)" },
            { offset: 1, color: "rgba(255,59,48,0)" },
          ]),
        },
      },
      {
        name: "收入",
        type: "line",
        smooth: true,
        symbolSize: 6,
        data: props.data.map((item) => item.income),
        lineStyle: { color: "#34c759", width: 3 },
        itemStyle: { color: "#34c759", borderColor: "#ffffff", borderWidth: 2 },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: "rgba(52,199,89,.12)" },
            { offset: 1, color: "rgba(52,199,89,0)" },
          ]),
        },
      },
    ],
  };
}

async function render() {
  await nextTick();
  if (!chartRef.value) return;
  if (chart) {
    chart.setOption(option(), true);
    return;
  }
  const instance = await chartRef.value.init(echarts) as echarts.ECharts | null;
  if (!instance) return;
  chart = instance;
  chart.setOption(option());
}

onMounted(render);
watch(() => props.data, render, { deep: true });
</script>

<style scoped>
.chart { width: 100%; height: 440rpx; }
</style>

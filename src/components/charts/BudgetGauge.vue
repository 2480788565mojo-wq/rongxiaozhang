<template>
  <view class="chart"><EChartHost ref="chartRef" :height="400" /><button v-if="renderError" class="chart-retry" @click="render">图表加载失败，点击重试</button></view>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from "vue";
import { onShow, onReady } from "@dcloudio/uni-app";
import echarts from "./echarts-lite";
import type { EChartsType as ECharts } from "echarts/core";
import type { EChartsOption } from "echarts";
import type { BudgetStatus } from "@/types";
import EChartHost from "./EChartHost.vue";

const props = withDefaults(defineProps<{ statuses: BudgetStatus[] }>(), { statuses: () => [] });
const chartRef = ref<any>(null);
let chart: ECharts | null = null;
const renderError = ref(false);
const usage = computed(() => Math.max(0, ...props.statuses.map((item) => item.percentage), 0));

function option(): EChartsOption {
  const value = Math.min(usage.value, 150);
  return {
    backgroundColor: "transparent",
    animationDuration: 280,
    series: [
      {
        type: "gauge",
        startAngle: 210,
        endAngle: -30,
        min: 0,
        max: 150,
        splitNumber: 6,
        progress: { show: true, width: 18, roundCap: true, itemStyle: { color: value >= 100 ? "#ff3b30" : value >= 80 ? "#ff9f0a" : "#4a90e2" } },
        axisLine: {
          lineStyle: {
            width: 18,
            color: [[0.533, "#e8f8ed"], [0.667, "#fff4df"], [1, "#fff0ef"]],
          },
        },
        pointer: { show: false },
        axisTick: { show: false },
        splitLine: { show: false },
        axisLabel: { show: false },
        anchor: { show: false },
        title: { offsetCenter: [0, "42%"], color: "#86868b", fontSize: 13 },
        detail: {
          valueAnimation: true,
          offsetCenter: [0, "4%"],
          formatter: "{value}%",
          color: value >= 100 ? "#ff3b30" : value >= 80 ? "#ff9f0a" : "#4a90e2",
          fontSize: 28,
          fontWeight: 700,
          fontFamily: "sans-serif",
        },
        data: [{ value: Number(value.toFixed(1)), name: "最高预算使用率" }],
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
watch(() => props.statuses, render, { deep: true });
</script>

<style scoped>
.chart { position: relative; width: 100%; height: 400rpx; }
.chart-retry { position: absolute; left: 10%; right: 10%; top: 35%; font-size: 26rpx; color: var(--color-text-secondary); background: var(--color-surface-muted); }
</style>

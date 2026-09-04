<template>
  <view class="chart"><EChartHost ref="chartRef" /></view>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from "vue";
import echarts from "./echarts-lite";
import type { ECharts, EChartsOption } from "echarts";
import type { BudgetStatus } from "@/types";
import EChartHost from "./EChartHost.vue";

const props = withDefaults(defineProps<{ statuses: BudgetStatus[] }>(), { statuses: () => [] });
const chartRef = ref<any>(null);
let chart: ECharts | null = null;
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
        data: [{ value: Number(value.toFixed(1)), name: "最高分类预算使用率" }],
      },
    ],
  };
}

async function render() {
  await nextTick();
  if (!chartRef.value) return;
  if (chart) return void chart.setOption(option(), true);
  const instance = await chartRef.value.init(echarts) as echarts.ECharts | null;
  if (!instance) return;
  chart = instance;
  chart.setOption(option());
}

onMounted(render);
watch(() => props.statuses, render, { deep: true });
</script>

<style scoped>
.chart { width: 100%; height: 400rpx; }
</style>

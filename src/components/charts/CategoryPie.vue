<template>
  <view class="chart"><EChartHost ref="chartRef" :height="480" /><button v-if="renderError" class="chart-retry" @click="render">图表加载失败，点击重试</button></view>
</template>

<script setup lang="ts">
import { nextTick, onMounted, ref, watch } from "vue";
import { onShow, onReady } from "@dcloudio/uni-app";
import echarts from "./echarts-lite";
import type { EChartsType as ECharts } from "echarts/core";
import type { EChartsOption } from "echarts";
import type { CategoryStat } from "@/types";
import EChartHost from "./EChartHost.vue";

const props = withDefaults(defineProps<{ data: CategoryStat[] }>(), { data: () => [] });
const chartRef = ref<any>(null);
let chart: ECharts | null = null;
const renderError = ref(false);
const colors = ["#4a90e2", "#34c759", "#ff9f0a", "#7d6ee8", "#5ac8fa", "#ff7a73", "#8e8e93"];

function option(): EChartsOption {
  return {
    color: colors,
    backgroundColor: "transparent",
    animationDuration: 280,
    tooltip: { trigger: "item", formatter: "{b}<br/>¥{c} · {d}%", backgroundColor: "#ffffff", borderColor: "#e5e5ea", textStyle: { color: "#1d1d1f", fontFamily: "sans-serif" } },
    legend: {
      type: "scroll",
      bottom: 0,
      textStyle: { color: "#86868b" },
    },
    series: [
      {
        name: "分类支出",
        type: "pie",
        radius: ["46%", "68%"],
        center: ["50%", "43%"],
        avoidLabelOverlap: true,
        itemStyle: { borderColor: "#ffffff", borderWidth: 4, borderRadius: 4 },
        emphasis: { scaleSize: 5 },
        label: { formatter: "{b}\n{d}%", color: "#424245", fontFamily: "sans-serif" },
        labelLine: { lineStyle: { color: "#c7c7cc" } },
        data: props.data.map((item) => ({ name: item.category, value: item.amount })),
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
.chart { position: relative; width: 100%; height: 480rpx; }
.chart-retry { position: absolute; left: 10%; right: 10%; top: 35%; font-size: 26rpx; color: var(--color-text-secondary); background: var(--color-surface-muted); }
</style>

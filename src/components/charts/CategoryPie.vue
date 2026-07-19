<template>
  <view class="chart"><EChartHost ref="chartRef" /></view>
</template>

<script setup lang="ts">
import { nextTick, onMounted, ref, watch } from "vue";
import * as echarts from "echarts";
import type { CategoryStat } from "@/types";
import EChartHost from "./EChartHost.vue";

const props = withDefaults(defineProps<{ data: CategoryStat[] }>(), { data: () => [] });
const chartRef = ref<any>(null);
let chart: echarts.ECharts | null = null;
const colors = ["#4a90e2", "#34c759", "#ff9f0a", "#7d6ee8", "#5ac8fa", "#ff7a73", "#8e8e93"];

function option(): echarts.EChartsOption {
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
  if (chart) return void chart.setOption(option(), true);
  const instance = await chartRef.value.init(echarts) as echarts.ECharts | null;
  if (!instance) return;
  chart = instance;
  chart.setOption(option());
}

onMounted(render);
watch(() => props.data, render, { deep: true });
</script>

<style scoped>
.chart { width: 100%; height: 480rpx; }
</style>

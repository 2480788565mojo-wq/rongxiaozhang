<template>
  <canvas
    :id="canvasId"
    :canvas-id="canvasId"
    type="2d"
    class="echart-host"
    @touchstart="forwardTouch('mousedown', $event)"
    @touchmove="forwardTouch('mousemove', $event)"
    @touchend="forwardTouch('mouseup', $event)"
  />
</template>

<script setup lang="ts">
import { getCurrentInstance, nextTick, onUnmounted } from "vue";

const canvasId = `echart-${Math.random().toString(36).slice(2, 10)}`;
const instance = getCurrentInstance();
let chart: any = null;
let canvasTarget: any = null;
let initPromise: Promise<any | null> | null = null;
let resizeObserver: ResizeObserver | null = null;
let destroyed = false;
let generation = 0;

function createChart(echarts: any): Promise<any | null> {
  // #ifdef H5
  const canvas = document.getElementById(canvasId) as HTMLCanvasElement | null;
  if (!canvas) return Promise.resolve(null);
  const rect = canvas.getBoundingClientRect();
  const ratio = window.devicePixelRatio || 1;
  canvas.width = Math.max(1, rect.width * ratio);
  canvas.height = Math.max(1, rect.height * ratio);
  canvasTarget = canvas;
  return Promise.resolve(echarts.init(canvas, undefined, {
    width: rect.width,
    height: rect.height,
    devicePixelRatio: ratio,
  }));
  // #endif

  // #ifndef H5
  return new Promise((resolve) => {
    uni.createSelectorQuery()
      .in(instance?.proxy)
      .select(`#${canvasId}`)
      .fields({ node: true, size: true }, () => {})
      .exec((result) => {
        const target = result?.[0];
        if (!target?.node) return resolve(null);
        const ratio = uni.getSystemInfoSync().pixelRatio || 1;
        target.node.width = target.width * ratio;
        target.node.height = target.height * ratio;
        canvasTarget = target.node;
        resolve(echarts.init(target.node, undefined, {
          width: target.width,
          height: target.height,
          devicePixelRatio: ratio,
        }));
      });
  });
  // #endif
}

async function init(echarts: any) {
  if (chart && !chart.isDisposed?.()) return chart;
  if (initPromise) return initPromise;
  const currentGeneration = ++generation;
  initPromise = (async () => {
    await nextTick();
    const created = await createChart(echarts);
    if (!created) return null;
    if (destroyed || currentGeneration !== generation) {
      created.dispose?.();
      return null;
    }
    chart = created;
    bindResize();
    return chart;
  })();
  try {
    return await initPromise;
  } finally {
    initPromise = null;
  }
}

function resize() {
  if (!chart || chart.isDisposed?.()) return;
  // #ifdef H5
  const canvas = canvasTarget as HTMLCanvasElement | null;
  const rect = canvas?.getBoundingClientRect();
  if (rect?.width && rect?.height) chart.resize({ width: rect.width, height: rect.height });
  // #endif
  // #ifndef H5
  uni.createSelectorQuery()
    .in(instance?.proxy)
    .select(`#${canvasId}`)
    .fields({ size: true }, () => {})
    .exec((result) => {
      const target = result?.[0];
      if (target?.width && target?.height && chart && !chart.isDisposed?.()) {
        chart.resize({ width: target.width, height: target.height });
      }
    });
  // #endif
}

function bindResize() {
  // #ifdef H5
  if (typeof ResizeObserver !== "undefined" && canvasTarget) {
    resizeObserver = new ResizeObserver(resize);
    resizeObserver.observe(canvasTarget);
  } else {
    window.addEventListener("resize", resize);
  }
  // #endif
  // #ifndef H5
  (uni as any).onWindowResize?.(resize);
  // #endif
}

function dispose() {
  generation += 1;
  resizeObserver?.disconnect();
  resizeObserver = null;
  // #ifdef H5
  window.removeEventListener("resize", resize);
  // #endif
  // #ifndef H5
  (uni as any).offWindowResize?.(resize);
  // #endif
  chart?.dispose?.();
  chart = null;
  canvasTarget = null;
}

function forwardTouch(type: string, event: any) {
  // ECharts already binds native pointer/touch events on H5 canvases.
  // #ifdef H5
  return;
  // #endif
  if (!chart) return;
  const touch = event.touches?.[0] || event.changedTouches?.[0];
  if (!touch) return;
  chart.getZr().handler.dispatch(type, {
    zrX: touch.x ?? touch.clientX,
    zrY: touch.y ?? touch.clientY,
  });
}

onUnmounted(() => {
  destroyed = true;
  dispose();
});

defineExpose({ init, resize, dispose });
</script>

<style scoped>
.echart-host { width: 100%; height: 100%; }
</style>

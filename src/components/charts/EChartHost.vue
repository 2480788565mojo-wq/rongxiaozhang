<template>
  <!-- #ifdef H5 -->
  <view :id="canvasId" class="echart-host" :style="{ height: `${height}rpx` }" />
  <!-- #endif -->
  <!-- #ifndef H5 -->
  <canvas
    :id="canvasId"
    :canvas-id="canvasId"
    type="2d"
    class="echart-host"
    :style="{ height: `${height}rpx` }"
    @touchstart="forwardTouch('mousedown', $event)"
    @touchmove="forwardTouch('mousemove', $event)"
    @touchend="forwardTouch('mouseup', $event)"
  />
  <!-- #endif -->
</template>

<script setup lang="ts">
import { getCurrentInstance, nextTick, onUnmounted } from "vue";

withDefaults(defineProps<{ height?: number }>(), { height: 440 });
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
  const canvas = document.getElementById(canvasId) as HTMLElement | null;
  if (!canvas) return Promise.resolve(null);
  const rect = canvas.getBoundingClientRect();
  const ratio = window.devicePixelRatio || 1;
  if (!rect.width || !rect.height) return Promise.resolve(null);
  canvasTarget = canvas;
  return Promise.resolve(echarts.init(canvas, undefined, {
    width: rect.width,
    height: rect.height,
    devicePixelRatio: ratio,
    renderer: "canvas",
  }));
  // #endif

  // #ifndef H5
  return new Promise((resolve, reject) => {
    let attempts = 0;
    // Vue 更新结束不等于微信视图层画布已创建，短暂等待节点与尺寸就绪。
    const queryCanvas = () => {
      if (destroyed) return resolve(null);
      uni.createSelectorQuery()
        .in(instance?.proxy)
        .select(`#${canvasId}`)
        .fields({ node: true, size: true }, () => {})
        .exec((result) => {
          if (destroyed) return resolve(null);
          const target = result?.[0];
          if (!target?.node || !target.width || !target.height) {
            if (++attempts < 20) setTimeout(queryCanvas, 50);
            else resolve(null);
            return;
          }
          try {
            const ratio = uni.getSystemInfoSync().pixelRatio || 1;
            target.node.width = target.width * ratio;
            target.node.height = target.height * ratio;
            canvasTarget = target.node;
            // ECharts 5 在微信环境也会绑定 DOM 事件，但原生 Canvas 没有这些方法。
            // 保留原生节点的绘制能力，只补齐空事件接口；真实触摸由模板转发。
            const nativeCanvas = target.node as any;
            nativeCanvas.addEventListener ||= () => {};
            nativeCanvas.removeEventListener ||= () => {};
            nativeCanvas.setAttribute ||= (key: string, value: unknown) => { nativeCanvas[key] = value; };
            resolve(echarts.init(nativeCanvas, undefined, {
              renderer: 'canvas',
              width: target.width,
              height: target.height,
              devicePixelRatio: ratio,
            }));
          } catch (error) { reject(error); }
        });
    };
    queryCanvas();
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
  const canvas = canvasTarget as HTMLElement | null;
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
  const position = { zrX: touch.x ?? touch.clientX, zrY: touch.y ?? touch.clientY };
  chart.getZr().handler.dispatch(type, position);
  if (type === 'mouseup') chart.getZr().handler.dispatch('click', position);
}

onUnmounted(() => {
  destroyed = true;
  dispose();
});

defineExpose({ init, resize, dispose });
</script>

<style scoped>
.echart-host { display: block; width: 100%; height: 100%; }
</style>

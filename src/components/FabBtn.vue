<template>
	<button
		class="fab-btn"
		:class="{ 'is-positioned': position !== null, 'is-dragging': dragging }"
		:style="positionStyle"
		type="button"
		aria-label="打开智能记账"
		title="打开智能记账"
		@touchstart="onTouchStart"
		@touchmove.stop.prevent="onTouchMove"
		@touchend="finishDrag"
		@touchcancel="finishDrag"
		@mousedown.prevent="onMouseStart"
		@click="goAdd"
	>
		<text class="fab-icon">+</text>
	</button>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";

type Point = { x: number; y: number };
type TouchLike = { clientX?: number; clientY?: number; pageX?: number; pageY?: number };

const STORAGE_KEY = "rxz-fab-position";
const EDGE_GAP = 8;
const DRAG_THRESHOLD = 5;
const position = ref<Point | null>(null);
const dragging = ref(false);
let viewport = { width: 375, height: 667, safeTop: 0, safeBottom: 0, size: 48 };
let dragOffset = { x: 0, y: 0 };
let dragOrigin = { x: 0, y: 0 };
let moved = false;
let suppressClick = false;

const positionStyle = computed(() => position.value
	? { left: `${position.value.x}px`, top: `${position.value.y}px`, bottom: "auto" }
	: undefined);

function readViewport() {
	const info = uni.getSystemInfoSync() as any;
	const width = Number(info.windowWidth) || 375;
	const height = Number(info.windowHeight) || 667;
	const safeArea = info.safeArea || {};
	viewport = {
		width,
		height,
		safeTop: Math.max(0, Number(safeArea.top) || 0),
		safeBottom: Math.max(0, height - (Number(safeArea.bottom) || height)),
		size: Math.max(44, width * 96 / 750),
	};
}

function clampPoint(point: Point): Point {
	const minX = EDGE_GAP;
	const maxX = Math.max(minX, viewport.width - viewport.size - EDGE_GAP);
	const minY = viewport.safeTop + EDGE_GAP;
	// Allow dragging across the full visible page. Only keep the button inside
	// the device safe area instead of creating a fixed tab-bar dead zone.
	const maxY = Math.max(
		minY,
		viewport.height - viewport.size - viewport.safeBottom - EDGE_GAP,
	);
	return {
		x: Math.min(maxX, Math.max(minX, point.x)),
		y: Math.min(maxY, Math.max(minY, point.y)),
	};
}

function initialPosition(): Point {
	return clampPoint({
		x: (viewport.width - viewport.size) / 2,
		y: viewport.height - viewport.size - viewport.safeBottom - viewport.width * 130 / 750,
	});
}

function eventPoint(touch: TouchLike): Point {
	return {
		x: Number(touch.clientX ?? touch.pageX ?? 0),
		y: Number(touch.clientY ?? touch.pageY ?? 0),
	};
}

function startDrag(point: Point) {
	const current = position.value || initialPosition();
	position.value = current;
	dragOffset = { x: point.x - current.x, y: point.y - current.y };
	dragOrigin = point;
	moved = false;
	dragging.value = true;
}

function moveDrag(point: Point) {
	if (!dragging.value) return;
	if (Math.hypot(point.x - dragOrigin.x, point.y - dragOrigin.y) >= DRAG_THRESHOLD) moved = true;
	position.value = clampPoint({ x: point.x - dragOffset.x, y: point.y - dragOffset.y });
}

function onTouchStart(event: any) {
	const touch = event.touches?.[0];
	if (touch) startDrag(eventPoint(touch));
}

function onTouchMove(event: any) {
	const touch = event.touches?.[0];
	if (touch) moveDrag(eventPoint(touch));
}

function finishDrag() {
	if (!dragging.value) return;
	dragging.value = false;
	if (moved && position.value) {
		suppressClick = true;
		uni.setStorageSync(STORAGE_KEY, position.value);
		setTimeout(() => {
			suppressClick = false;
			moved = false;
		}, 400);
	}
	removeMouseListeners();
}

function onMouseMove(event: MouseEvent) {
	moveDrag(eventPoint(event));
}

function onMouseUp() {
	finishDrag();
}

function removeMouseListeners() {
	if (typeof window === "undefined") return;
	window.removeEventListener("mousemove", onMouseMove);
	window.removeEventListener("mouseup", onMouseUp);
}

function onMouseStart(event: MouseEvent) {
	if (typeof window === "undefined") return;
	startDrag(eventPoint(event));
	window.addEventListener("mousemove", onMouseMove);
	window.addEventListener("mouseup", onMouseUp);
}

function goAdd() {
	if (suppressClick || moved) {
		suppressClick = false;
		moved = false;
		return;
	}
	uni.switchTab({ url: "/pages/transcribe/index" });
}

onMounted(() => {
	readViewport();
	const saved = uni.getStorageSync(STORAGE_KEY) as Point | undefined;
	position.value = saved && Number.isFinite(saved.x) && Number.isFinite(saved.y)
		? clampPoint(saved)
		: initialPosition();
});

onUnmounted(removeMouseListeners);
</script>

<style lang="scss" scoped>
// 固定在屏幕底部的圆形按钮样式
.fab-btn {
	position: fixed;
	bottom: calc(130rpx + constant(safe-area-inset-bottom));
	bottom: calc(130rpx + env(safe-area-inset-bottom));
	left: 50%;
	transform: translateX(-50%);
	width: 96rpx;
	height: 96rpx;
	border-radius: 50%;
	border: 0;
	background: linear-gradient(145deg, #5aa1f0, #3d7fd1);
	color: #fff;
	display: flex;
	align-items: center;
	justify-content: center;
	box-shadow: 0 16rpx 32rpx rgba(74, 144, 226, .28);
	z-index: 999;
	margin: 0;
	padding: 0;
	line-height: 1;
	touch-action: none;
	user-select: none;
	will-change: left, top, transform;
}
.fab-btn:active { transform: translateX(-50%) scale(.97); box-shadow: 0 8rpx 20rpx rgba(74, 144, 226, .3); }
.fab-btn.is-positioned { transform: none; }
.fab-btn.is-positioned:active { transform: scale(.97); }
.fab-btn.is-dragging { transform: scale(1.04); box-shadow: 0 20rpx 36rpx rgba(74, 144, 226, .32); }
.fab-btn:focus-visible { outline: 3rpx solid #1d1d1f; outline-offset: 6rpx; }
.fab-icon {
	font-size: 56rpx;
	font-weight: 300;
	line-height: 1;
	margin-top: -4rpx;
}
</style>

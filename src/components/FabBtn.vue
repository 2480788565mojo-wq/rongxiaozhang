<template>
	<button class="fab-btn" type="button" aria-label="打开智能记账" title="打开智能记账" @click="goAdd">
		<text class="fab-icon">+</text>
	</button>
</template>

<script setup lang="ts">
// 跳转到记账页面
function goAdd() {
	uni.switchTab({ url: "/pages/transcribe/index" });
}
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
	background: #4a90e2;
	color: #fff;
	display: flex;
	align-items: center;
	justify-content: center;
	box-shadow: 0 8rpx 24rpx rgba(74, 144, 226, .24);
	z-index: 999;
	margin: 0;
	padding: 0;
	line-height: 1;
}
.fab-btn:active { transform: translateX(-50%) scale(.97); box-shadow: 0 4rpx 16rpx rgba(74, 144, 226, .3); }
.fab-btn:focus-visible { outline: 3rpx solid #1d1d1f; outline-offset: 6rpx; }
.fab-icon {
	font-size: 56rpx;
	font-weight: 300;
	line-height: 1;
	margin-top: -4rpx;
}
</style>

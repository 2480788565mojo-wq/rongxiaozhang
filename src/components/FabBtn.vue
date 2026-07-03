<template>
	<view class="fab-btn" @click="goAdd">
		<text class="fab-icon">+</text>
	</view>
</template>

<script setup lang="ts">
function goAdd() {
	uni.navigateTo({ url: "/pages/add/index" });
}
</script>

<style lang="scss" scoped>
.fab-btn {
	position: fixed;
	bottom: 130rpx;
	left: 50%;
	transform: translateX(-50%);
	width: 96rpx;
	height: 96rpx;
	border-radius: 50%;
	background: #2979ff;
	color: #fff;
	display: flex;
	align-items: center;
	justify-content: center;
	box-shadow: 0 4rpx 16rpx rgba(41, 121, 255, 0.4);
	z-index: 999;
}
.fab-icon {
	font-size: 56rpx;
	font-weight: 300;
	line-height: 1;
	margin-top: -4rpx;
}
</style>

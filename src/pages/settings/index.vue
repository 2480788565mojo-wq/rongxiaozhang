<template>
	<view class="page-settings">
		<view class="user-card">
			<image class="avatar" src="/static/logo.jpg" mode="aspectFill"></image>
			<text class="nickname">荣小账</text>
			<text class="desc">记录每一笔，心中有数</text>
		</view>

		<view class="settings-list">
			<view class="settings-item" @click="goExport">
				<text class="item-label">📥 导出为 CSV（Excel）</text>
				<text class="arrow">></text>
			</view>
			<view class="settings-item" @click="exportBackup">
				<text class="item-label">💾 导出备份（JSON）</text>
				<text class="arrow">></text>
			</view>
			<view class="settings-item" @click="goCategories">
				<text class="item-label">📂 分类管理</text>
				<text class="arrow">></text>
			</view>
			<view class="settings-item" @click="goAccounts">
				<text class="item-label">🏦 账户管理</text>
				<text class="arrow">></text>
			</view>
		</view>

		<view class="settings-list">
			<view class="settings-item" @click="showClearConfirm = true">
				<text class="item-label danger">🗑️ 清除所有数据</text>
				<text class="arrow">></text>
			</view>
		</view>

		<view class="about-section">
			<text class="version">荣小账 v1.0.0</text>
			<text class="storage-tip">数据存储于本地，清除浏览器缓存会丢失</text>
		</view>

		<u-modal
			:show="showClearConfirm"
			title="确认清除"
			content="确定要清除所有数据吗？此操作不可恢复！建议先导出备份。"
			@confirm="clearAllData"
			@cancel="showClearConfirm = false"
		></u-modal>
		<FabBtn />
	</view>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { getBills, exportCSV, exportAllData, clearAllLocalData } from '@/utils/store';

const showClearConfirm = ref(false);

function goCategories() {
	uni.navigateTo({ url: '/pages/categories/index' });
}

function goExport() {
	const bills = getBills();
	if (bills.length === 0) {
		uni.showToast({ title: '暂无数据可导出', icon: 'none' });
		return;
	}
	const csv = exportCSV(bills);

	// 在H5环境下，通过下载方式导出
	const blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8;' });
	const url = URL.createObjectURL(blob);
	const a = document.createElement('a');
	a.href = url;
	a.download = '荣小账_' + new Date().toISOString().slice(0, 10) + '.csv';
	a.click();
	URL.revokeObjectURL(url);

	uni.showToast({ title: '导出成功', icon: 'success' });
}

function exportBackup() {
	const data = exportAllData();
	const blob = new Blob([data], { type: 'application/json;charset=utf-8;' });
	const url = URL.createObjectURL(blob);
	const a = document.createElement('a');
	a.href = url;
	a.download = '荣小账备份_' + new Date().toISOString().slice(0, 10) + '.json';
	a.click();
	URL.revokeObjectURL(url);
	uni.showToast({ title: '备份已下载', icon: 'success' });
}

function goAccounts() {
	uni.navigateTo({ url: '/pages/accounts/index' });
}

function clearAllData() {
	showClearConfirm.value = false;
	clearAllLocalData();
	uni.showToast({ title: '数据已清除', icon: 'success' });
}
</script>

<style lang="scss" scoped>
.page-settings { padding-bottom: 120rpx; }

.user-card {
	text-align: center; padding: 60rpx 30rpx;
	background: linear-gradient(135deg, #2979ff, #5b8ff9); color: #fff;
}
.avatar {
	width: 120rpx; height: 120rpx; border-radius: 50%;
	border: 4rpx solid rgba(255,255,255,0.5); margin-bottom: 16rpx;
}
.nickname { font-size: 32rpx; font-weight: bold; display: block; }
.desc { font-size: 24rpx; opacity: 0.8; margin-top: 8rpx; display: block; }

.settings-list {
	background: #fff; border-radius: 16rpx; margin: 20rpx 30rpx;
	box-shadow: 0 2rpx 8rpx rgba(0,0,0,0.04); overflow: hidden;
}
.settings-item {
	display: flex; justify-content: space-between; align-items: center;
	padding: 30rpx; border-bottom: 1rpx solid #f5f5f5;
}
.item-label { font-size: 28rpx; }
.item-label.danger { color: #dd524d; }
.arrow { color: #ccc; font-size: 28rpx; }

.about-section { text-align: center; padding: 40rpx; }
.version { font-size: 24rpx; color: #ccc; display: block; }
.storage-tip { font-size: 22rpx; color: #f0ad4e; display: block; margin-top: 8rpx; }
</style>

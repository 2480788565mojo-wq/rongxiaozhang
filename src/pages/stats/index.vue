<template>
	<view class="page-stats">
		<view class="header">
			<text class="title">统计报表</text>
			<picker mode="date" fields="month" :value="selYear + '-' + String(selMonth).padStart(2, '0')" @change="onMonthChange">
			<view class="month-select">
				<text>{{ currentMonth }}</text>
				<text class="arrow">▼</text>
			</view>
			</picker>
		</view>

		<view class="stats-summary">
			<view class="stat-box">
				<text class="stat-label">本月支出</text>
				<text class="stat-value expense">¥{{ totalExpense.toFixed(2) }}</text>
			</view>
			<view class="stat-box">
				<text class="stat-label">本月收入</text>
				<text class="stat-value income">¥{{ totalIncome.toFixed(2) }}</text>
			</view>
			<view class="stat-box" v-if="lastExpense > 0">
				<text class="stat-label">环比上月</text>
				<text class="stat-value" :class="compareColor">{{ compareText }}</text>
			</view>
		</view>

		<view class="chart-card">
			<text class="chart-title">月度收支趋势</text>
			<canvas canvas-id="trendCanvas" id="trendCanvas" class="chart-canvas"></canvas>
		</view>

		<view class="chart-card">
			<text class="chart-title">支出分类占比</text>
			<canvas canvas-id="pieCanvas" id="pieCanvas" class="chart-canvas"></canvas>
		</view>

		<view class="top5-card">
			<text class="chart-title">本月支出TOP{{ top5.length }}</text>
			<view class="top-item" v-for="(item, index) in top5" :key="index">
				<text class="top-rank">{{ index + 1 }}</text>
				<text class="top-name">{{ item.name }}</text>
				<view class="top-bar-bg">
					<view class="top-bar" :style="{ width: item.percent + '%' }"></view>
				</view>
				<text class="top-amount">¥{{ item.amount.toFixed(2) }}</text>
			</view>
			<view class="empty-tip" v-if="top5.length === 0"><text>本月暂无支出</text></view>
		</view>
		<FabBtn />
	</view>
</template>

<script setup lang="ts">
import { ref, computed, nextTick } from 'vue';
import { getMonthlyStats, getCategoryStats, getTrendData } from '@/utils/store';
import { onShow } from '@dcloudio/uni-app';
import FabBtn from '@/components/FabBtn.vue';

const now = new Date();
const selYear = ref(now.getFullYear());
const selMonth = ref(now.getMonth() + 1);
const currentMonth = computed(() => selYear.value + '年' + selMonth.value + '月');

const totalExpense = ref(0);
const totalIncome = ref(0);
const lastExpense = ref(0);
const compareText = ref('');
const compareColor = ref('');
const top5 = ref<{name: string; amount: number; percent: number}[]>([]);

function loadData() {
	const stats = getMonthlyStats(selYear.value, selMonth.value);
	totalExpense.value = stats.expense;
	totalIncome.value = stats.income;

	let lastM = selMonth.value - 1;
	let lastY = selYear.value;
	if (lastM === 0) { lastM = 12; lastY--; }
	const last = getMonthlyStats(lastY, lastM);
	lastExpense.value = last.expense;

	if (last.expense > 0) {
		const diff = ((stats.expense - last.expense) / last.expense * 100);
		compareText.value = (diff > 0 ? '+' : '') + diff.toFixed(1) + '%';
		compareColor.value = diff > 0 ? 'expense' : 'income';
	}

	const catStats = getCategoryStats(selYear.value, selMonth.value);
	if (catStats.length > 0) {
		const maxAmount = catStats[0].amount;
		top5.value = catStats.slice(0, 5).map(c => ({
			name: c.name,
			amount: c.amount,
			percent: Math.round((c.amount / maxAmount) * 100),
		}));
	} else {
		top5.value = [];
	}

	nextTick(() => resizeAndDraw());
}

function resizeAndDraw() {
	['trendCanvas', 'pieCanvas'].forEach((id) => {
		const canvas = document.querySelector('[canvas-id="' + id + '"]') as HTMLCanvasElement | null;
		if (canvas && canvas.clientWidth > 0 && canvas.clientHeight > 0) {
			canvas.width = canvas.clientWidth;
			canvas.height = canvas.clientHeight;
		}
	});
	drawTrend();
	drawPie();
}

function drawTrend() {
	const canvas = document.querySelector('[canvas-id="trendCanvas"]') as HTMLCanvasElement | null;
	if (!canvas) return;
	const ctx = uni.createCanvasContext('trendCanvas');

	const w = canvas.width;
	const h = canvas.height;
	const pad = { top: 40, bottom: 30, left: 45, right: 25 };
	const cw = w - pad.left - pad.right;
	const ch = h - pad.top - pad.bottom;

	const data = getTrendData();
	const allVals = [...data.map(d => d.expense), ...data.map(d => d.income)];
	const maxV = Math.max(...allVals, 1);
	const ceiling = Math.ceil(maxV / 1000) * 1000 || 1000;

	for (let i = 0; i <= 4; i++) {
		const y = pad.top + (ch / 4) * i;
		ctx.beginPath();
		ctx.moveTo(pad.left, y);
		ctx.lineTo(w - pad.right, y);
		ctx.setStrokeStyle('#ddd');
		ctx.setLineWidth(1);
		ctx.stroke();
		ctx.setFontSize(10);
		ctx.setFillStyle('#999');
		ctx.fillText(String(Math.round((ceiling / 4) * (4 - i))), 2, y + 3);
	}

	function drawLine(vals: number[], color: string) {
		ctx.beginPath();
		ctx.setStrokeStyle(color);
		ctx.setLineWidth(3);
		vals.forEach((v, i) => {
			const x = pad.left + (cw / (data.length - 1 || 1)) * i;
			const y = pad.top + ch - (v / ceiling) * ch;
			i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
		});
		ctx.stroke();

		vals.forEach((v, i) => {
			const x = pad.left + (cw / (data.length - 1 || 1)) * i;
			const y = pad.top + ch - (v / ceiling) * ch;
			ctx.beginPath();
			ctx.arc(x, y, 4, 0, Math.PI * 2);
			ctx.setFillStyle(color);
			ctx.fill();
			ctx.beginPath();
			ctx.arc(x, y, 2, 0, Math.PI * 2);
			ctx.setFillStyle('#fff');
			ctx.fill();
		});
	}

	drawLine(data.map(d => d.expense), '#1a5cc8');
	drawLine(data.map(d => d.income), '#2e8b57');

	ctx.setFontSize(10);
	ctx.setFillStyle('#666');
	data.forEach((d, i) => {
		const x = pad.left + (cw / (data.length - 1 || 1)) * i;
		ctx.fillText(d.month, x - 8, pad.top + ch + 16);
	});

	ctx.setFillStyle('#1a5cc8');
	ctx.fillRect(w - 90, 10, 14, 14);
	ctx.setFillStyle('#333');
	ctx.setFontSize(11);
	ctx.fillText('支出', w - 72, 22);
	ctx.setFillStyle('#2e8b57');
	ctx.fillRect(w - 35, 10, 14, 14);
	ctx.fillText('收入', w - 17, 22);

	ctx.draw();
}

function drawPie() {
	const canvas = document.querySelector('[canvas-id="pieCanvas"]') as HTMLCanvasElement | null;
	if (!canvas) return;
	const ctx = uni.createCanvasContext('pieCanvas');

	const w = canvas.width;
	const h = canvas.height;
	const catStats = getCategoryStats(selYear.value, selMonth.value);
	const colors = ['#2979ff','#5b8ff9','#f0ad4e','#4cd964','#dd524d','#b0bec5','#9c27b0','#ff7043','#26a69a','#78909c'];

	if (catStats.length === 0) {
		ctx.setFontSize(14);
		ctx.setFillStyle('#ccc');
		ctx.fillText('暂无数据', w / 2 - 30, h / 2);
		ctx.draw();
		return;
	}

	const total = catStats.reduce((s, d) => s + d.amount, 0);
	const cx = w * 0.3, cy = h / 2, r = Math.min(w, h) * 0.3;
	let start = -Math.PI / 2;

	catStats.forEach((d, i) => {
		const angle = (d.amount / total) * Math.PI * 2;
		ctx.beginPath();
		ctx.moveTo(cx, cy);
		ctx.arc(cx, cy, r, start, start + angle);
		ctx.closePath();
		ctx.setFillStyle(colors[i % colors.length]);
		ctx.fill();
		start += angle;
	});

	const lx = w * 0.65;
	let ly = 15;
	const show = catStats.slice(0, 6);
	show.forEach((d, i) => {
		ctx.setFillStyle(colors[i % colors.length]);
		ctx.fillRect(lx, ly, 14, 14);
		ctx.setFontSize(11);
		ctx.setFillStyle('#333');
		ctx.fillText(d.name, lx + 18, ly + 12);
		ctx.setFillStyle('#999');
		ctx.fillText(Math.round((d.amount / total) * 100) + '%', lx + 18, ly + 26);
		ly += 48;
	});

	ctx.draw();
}

onShow(() => { loadData(); });
loadData();
</script>

<style lang="scss" scoped>
.page-stats { padding: 20rpx 30rpx 120rpx; }
.header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 30rpx; }
.title { font-size: 32rpx; font-weight: bold; }
.month-select { font-size: 26rpx; color: #999; }
.arrow { font-size: 20rpx; margin-left: 8rpx; }

.stats-summary {
	display: flex; background: #fff; border-radius: 20rpx; padding: 30rpx;
	margin-bottom: 20rpx; box-shadow: 0 2rpx 12rpx rgba(0,0,0,0.06);
}
.stat-box { flex: 1; text-align: center; }
.stat-label { font-size: 22rpx; color: #999; display: block; margin-bottom: 8rpx; }
.stat-value { font-size: 32rpx; font-weight: bold; display: block; }
.stat-value.expense { color: #333; }
.stat-value.income { color: #4cd964; }

.chart-card, .top5-card {
	background: #fff; border-radius: 20rpx; padding: 30rpx;
	margin-bottom: 20rpx; box-shadow: 0 2rpx 12rpx rgba(0,0,0,0.06);
}
.chart-title { font-size: 28rpx; font-weight: bold; display: block; margin-bottom: 20rpx; }
.chart-canvas { width: 100%; height: 700rpx; }

.top-item { display: flex; align-items: center; margin-bottom: 16rpx; }
.top-rank {
	width: 36rpx; height: 36rpx; border-radius: 50%;
	background: #f5f5f5; display: flex; align-items: center;
	justify-content: center; font-size: 22rpx; color: #999; margin-right: 16rpx;
}
.top-name { width: 140rpx; font-size: 26rpx; }
.top-bar-bg { flex: 1; height: 24rpx; background: #f5f5f5; border-radius: 12rpx; margin: 0 16rpx; overflow: hidden; }
.top-bar { height: 100%; background: linear-gradient(90deg, #2979ff, #5b8ff9); border-radius: 12rpx; }
.top-amount { font-size: 26rpx; color: #333; width: 100rpx; text-align: right; }
.empty-tip { text-align: center; padding: 40rpx; color: #ccc; font-size: 26rpx; }
</style>

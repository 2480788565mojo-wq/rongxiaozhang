<template>
	<view class="page-home">
		<view class="header-card">
			<view class="date-section">
				<text class="month">{{ currentMonth }}</text>
			</view>
			<view class="summary-row">
				<view class="summary-item">
					<text class="label">支出</text>
					<text class="amount expense">¥{{ monthlyStats.expense }}</text>
				</view>
				<view class="summary-item">
					<text class="label">收入</text>
					<text class="amount income">¥{{ monthlyStats.income }}</text>
				</view>
				<view class="summary-item">
					<text class="label">结余</text>
					<text class="amount">¥{{ monthlyStats.balance }}</text>
				</view>
			</view>
		</view>

		<view class="budget-card" @click="goBudget">
			<view class="card-header">
				<text class="section-title">预算进度</text>
				<text class="more">查看详情 ></text>
			</view>
			<view v-if="budgetData" class="budget-item">
				<view class="budget-label">
					<text>总预算</text>
					<text class="budget-value">¥{{ budgetData.used }}/¥{{ budgetData.total }}</text>
				</view>
				<u-line-progress
					:percentage="budgetData.percent"
					:activeColor="budgetData.percent > 100 ? '#dd524d' : budgetData.percent > 80 ? '#f0ad4e' : '#2979ff'"
					height="12"
				></u-line-progress>
			</view>
			<view v-else class="budget-item">
				<text class="no-budget">尚未设置预算</text>
			</view>
		</view>

		<view class="recent-card">
			<view class="card-header">
				<text class="section-title">最近记录</text>
				<text class="more" @click="goBills">查看全部 ></text>
			</view>
			<view class="record-item" v-for="item in recentBills" :key="item._id" @click="editBill(item)">
				<view class="record-icon">{{ getIcon(item.category) }}</view>
				<view class="record-info">
					<text class="record-cate">{{ item.category }}</text>
					<text class="record-note">{{ item.note || item.account }}</text>
				</view>
				<text class="record-amount" :class="item.type">
					{{ item.type === 'expense' ? '-' : '+' }}¥{{ item.amount.toFixed(2) }}
				</text>
			</view>
			<view class="empty-tip" v-if="recentBills.length === 0">
				<text>还没有记录，点击下方 + 开始记账吧</text>
			</view>
		</view>
	</view>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { getRecentBills, getMonthlyStats, getBudget, getBills, type Bill } from '@/utils/store';
import { onShow } from '@dcloudio/uni-app';

const now = new Date();
const year = now.getFullYear();
const month = now.getMonth() + 1;

const currentMonth = computed(() => `${year}年${month}月`);
const monthlyStats = ref({ expense: 0, income: 0, balance: 0 });
const recentBills = ref<Bill[]>([]);
const budgetData = ref<{ total: number; used: number; percent: number } | null>(null);

function loadData() {
	monthlyStats.value = getMonthlyStats(year, month);
	recentBills.value = getRecentBills(5);

	const budget = getBudget(year, month);
	if (budget && budget.totalBudget > 0) {
		const used = monthlyStats.value.expense;
		const total = budget.totalBudget;
		budgetData.value = {
			total,
			used,
			percent: Math.min(100, Math.round((used / total) * 100)),
		};
	} else {
		budgetData.value = null;
	}
}

function getIcon(category: string): string {
	const iconMap: Record<string, string> = {
		'早餐':'🍜','午餐':'🍜','晚餐':'🍜','外卖':'🥡','水果零食':'🍎','奶茶饮品':'🧋','聚餐宴请':'🍽️',
		'公交地铁':'🚌','打车':'🚗','加油':'⛽','停车费':'🅿️','过路费':'🛣️','火车/飞机':'🚄','共享单车':'🚲',
		'服装鞋包':'👗','美妆护肤':'💄','家居日用':'🏠','数码电器':'📱','文具书籍':'📚','宠物用品':'🐾',
		'房租/房贷':'🏠','水费':'🚰','电费':'⚡','燃气费':'🔥','物业费':'🏢','维修':'🔧','网络宽带':'🌐',
		'电影演出':'🎬','运动健身':'🏋️','游戏充值':'🎮','旅游度假':'✈️','KTV/酒吧':'🎤',
		'红包礼金':'🧧','孝敬父母':'👨‍👩‍👧','送礼':'🎁','聚会请客':'🍻',
		'看病挂号':'🏥','药品':'💊','体检':'🩺','牙科/眼科':'🦷','保健':'💪',
		'课程培训':'📖','考证报名':'📝','书籍':'📕',
		'话费':'📞','流量套餐':'📶',
		'工资':'💰','奖金':'🏆','补贴':'📄',
		'兼职':'💼','投资理财':'📈','红包收入':'🧧',
		'退款':'↩️','闲置出售':'🏷️','其他':'📌',
	};
	return iconMap[category] || '📌';
}

onShow(() => {
	loadData();
});
loadData();

function goBudget() { uni.navigateTo({ url: '/pages/budget/index' }); }
function goBills() { uni.switchTab({ url: '/pages/bills/index' }); }
function editBill(item: Bill) { uni.navigateTo({ url: '/pages/add/index?id=' + item._id }); }
</script>

<style lang="scss" scoped>
.page-home { padding: 20rpx 30rpx 120rpx; }
.header-card {
	background: linear-gradient(135deg, #2979ff, #5b8ff9);
	border-radius: 20rpx; padding: 40rpx 30rpx; color: #fff;
}
.date-section { margin-bottom: 30rpx; }
.month { font-size: 32rpx; font-weight: bold; }
.summary-row { display: flex; justify-content: space-between; }
.summary-item { text-align: center; flex: 1; }
.label { font-size: 24rpx; opacity: 0.8; display: block; }
.amount { font-size: 36rpx; font-weight: bold; display: block; margin-top: 10rpx; }
.amount.income { color: #4cd964; }

.budget-card, .recent-card {
	background: #fff; border-radius: 20rpx; padding: 30rpx;
	margin-top: 20rpx; box-shadow: 0 2rpx 12rpx rgba(0,0,0,0.06);
}
.card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24rpx; }
.section-title { font-size: 30rpx; font-weight: bold; }
.more { font-size: 24rpx; color: #999; }
.budget-item { margin-bottom: 20rpx; }
.budget-label { display: flex; justify-content: space-between; font-size: 26rpx; margin-bottom: 10rpx; }
.budget-value { color: #999; }
.no-budget { color: #ccc; font-size: 26rpx; }

.record-item {
	display: flex; align-items: center; padding: 20rpx 0;
	border-bottom: 1rpx solid #f5f5f5;
}
.record-icon {
	width: 64rpx; height: 64rpx; border-radius: 50%; background: #f5f5f5;
	display: flex; align-items: center; justify-content: center; font-size: 28rpx;
}
.record-info { flex: 1; margin-left: 20rpx; }
.record-cate { font-size: 28rpx; display: block; }
.record-note { font-size: 22rpx; color: #999; display: block; margin-top: 4rpx; }
.record-amount { font-size: 30rpx; font-weight: bold; }
.record-amount.income { color: #4cd964; }
.empty-tip { text-align: center; padding: 40rpx; color: #ccc; font-size: 26rpx; }
</style>

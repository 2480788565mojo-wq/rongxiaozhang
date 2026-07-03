<template>
	<view class="page-bills">
		<view class="filter-bar">
			<picker mode="date" fields="month" :value="selYear + '-' + String(selMonth).padStart(2, '0')" @change="onMonthChange">
			<view class="month-selector">
				<text>{{ currentMonth }}</text>
				<text class="arrow">▼</text>
			</view>
			</picker>
			<view class="total-summary">
				<text>支出 ¥{{ totalExpense.toFixed(2) }}</text>
				<text class="income"> 收入 ¥{{ totalIncome.toFixed(2) }}</text>
			</view>
		</view>

		<view class="bill-list" v-for="(group, gi) in billGroups" :key="gi">
			<view class="date-header">
				<text class="date-text">{{ group.date }}</text>
				<text class="date-total">支出 ¥{{ group.expense.toFixed(2) }} 收入 ¥{{ group.income.toFixed(2) }}</text>
			</view>
			<view class="bill-item" v-for="bill in group.list" :key="bill._id" @click="editBill(bill)">
				<view class="bill-icon">{{ getIcon(bill.category) }}</view>
				<view class="bill-info">
					<text class="bill-cate">{{ bill.category }}</text>
					<text class="bill-note">{{ bill.note || bill.account }}</text>
				</view>
				<text class="bill-amount" :class="bill.type">
					{{ bill.type === 'expense' ? '-' : '+' }}¥{{ bill.amount.toFixed(2) }}
				</text>
			</view>
		</view>

		<view class="empty-state" v-if="billGroups.length === 0">
			<text class="empty-text">暂无账单记录</text>
		</view>
		<FabBtn />
	</view>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { getBillsByMonth, type Bill } from '@/utils/store';
import { onShow } from '@dcloudio/uni-app';
import FabBtn from '@/components/FabBtn.vue';

const now = new Date();
const selYear = ref(now.getFullYear());
const selMonth = ref(now.getMonth() + 1);
const currentMonth = computed(() => selYear.value + '年' + selMonth.value + '月');

const totalExpense = ref(0);
const totalIncome = ref(0);
const billGroups = ref<{date: string; expense: number; income: number; list: Bill[]}[]>([]);

function loadBills() {
	const bills = getBillsByMonth(selYear.value, selMonth.value);
	totalExpense.value = 0;
	totalIncome.value = 0;

	// Group by date
	const groups: Record<string, Bill[]> = {};
	bills.forEach(b => {
		const d = b.date;
		if (!groups[d]) groups[d] = [];
		groups[d].push(b);
		if (b.type === 'expense') totalExpense.value += b.amount;
		else totalIncome.value += b.amount;
	});

	billGroups.value = Object.entries(groups).map(([date, list]) => {
		let exp = 0, inc = 0;
		list.forEach(b => {
			if (b.type === 'expense') exp += b.amount;
			else inc += b.amount;
		});
		return { date, expense: exp, income: inc, list };
	}).sort((a, b) => b.date.localeCompare(a.date));
}

function getIcon(category: string): string {
	const map: Record<string, string> = {
		'早餐':'🍜','午餐':'🍜','晚餐':'🍜','外卖':'🥡','水果零食':'🍎','奶茶饮品':'🧋','聚餐宴请':'🍽️',
		'公交地铁':'🚌','打车':'🚗','加油':'⛽','火车/飞机':'🚄',
		'服装鞋包':'👗','美妆护肤':'💄','家居日用':'🏠','数码电器':'📱','文具书籍':'📚',
		'房租/房贷':'🏠','水费':'🚰','电费':'⚡','燃气费':'🔥',
		'电影演出':'🎬','运动健身':'🏋️','游戏充值':'🎮','旅游度假':'✈️',
		'红包礼金':'🧧','送礼':'🎁',
		'看病挂号':'🏥','药品':'💊',
		'课程培训':'📖','书籍':'📕',
		'话费':'📞',
		'工资':'💰','奖金':'🏆',
		'退款':'↩️',
	};
	return map[category] || '📌';
}

onShow(() => { loadBills(); });
loadBills();

function editBill(item: Bill) {
	uni.navigateTo({ url: '/pages/add/index?id=' + item._id });
}
</script>

<style lang="scss" scoped>
.page-bills { padding-bottom: 120rpx; }
.filter-bar {
	display: flex; justify-content: space-between; align-items: center;
	padding: 20rpx 30rpx; background: #fff; border-bottom: 1rpx solid #f5f5f5;
}
.month-selector { font-size: 30rpx; font-weight: bold; }
.arrow { font-size: 20rpx; margin-left: 10rpx; color: #999; }
.total-summary { font-size: 24rpx; color: #999; }
.total-summary .income { margin-left: 20rpx; }

.date-header {
	display: flex; justify-content: space-between;
	padding: 20rpx 30rpx 10rpx; font-size: 24rpx; color: #999;
}
.bill-item {
	display: flex; align-items: center; padding: 20rpx 30rpx;
	background: #fff; border-bottom: 1rpx solid #f5f5f5;
}
.bill-icon {
	width: 64rpx; height: 64rpx; border-radius: 50%; background: #f5f5f5;
	display: flex; align-items: center; justify-content: center; font-size: 28rpx;
}
.bill-info { flex: 1; margin-left: 20rpx; }
.bill-cate { font-size: 28rpx; display: block; }
.bill-note { font-size: 22rpx; color: #999; display: block; margin-top: 4rpx; }
.bill-amount { font-size: 30rpx; font-weight: bold; }
.bill-amount.income { color: #4cd964; }
.bill-amount.expense { color: #333; }
.empty-state { text-align: center; padding: 100rpx 0; }
.empty-text { color: #ccc; font-size: 28rpx; }
</style>

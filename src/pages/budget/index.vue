<template>
	<view class="page-budget">
		<view class="section">
			<text class="section-title">每月总预算</text>
			<view class="total-budget-card">
				<view class="budget-item-col">
					<text class="label">月预算</text>
					<text class="value">¥{{ totalBudget }}</text>
				</view>
				<view class="budget-item-col">
					<text class="label">已使用</text>
					<text class="value">¥{{ usedAmount.toFixed(2) }}</text>
				</view>
				<view class="budget-item-col">
					<text class="label">剩余</text>
					<text class="value" :class="{ danger: remainAmount < 0 }">¥{{ remainAmount.toFixed(2) }}</text>
				</view>
			</view>
			<u-line-progress
				:percentage="usedPercent"
				:activeColor="usedPercent > 100 ? '#dd524d' : usedPercent > 80 ? '#f0ad4e' : '#2979ff'"
				height="16"
			></u-line-progress>
			<view class="set-budget-btn">
				<u-button type="info" size="small" plain @click="showSetTotal = true">设置总预算</u-button>
			</view>
		</view>

		<view class="section">
			<text class="section-title">分类预算</text>
			<view class="category-item" v-for="(item, idx) in categoryBudgets" :key="idx">
				<view class="cate-header">
					<text>{{ item.name }}</text>
					<text class="cate-value">¥{{ item.used.toFixed(2) }} / ¥{{ item.budget }}</text>
				</view>
				<u-line-progress
					:percentage="item.percent"
					:activeColor="item.percent > 100 ? '#dd524d' : item.percent > 80 ? '#f0ad4e' : '#2979ff'"
					height="12"
				></u-line-progress>
			</view>
			<view class="empty-tip" v-if="categoryBudgets.length === 0">
				<text>还没有设置分类预算</text>
			</view>
			<view class="set-budget-btn">
				<u-button type="primary" size="small" plain @click="showAddCategory">添加分类预算</u-button>
			</view>
		</view>

		<u-modal :show="showSetTotal" title="设置总预算" @confirm="onSetTotal" @cancel="showSetTotal = false">
			<input class="modal-input" type="digit" v-model="editTotal" placeholder="输入月预算金额" />
		</u-modal>

		<u-modal :show="showEditCat" title="设置分类预算" @confirm="onSetCategory" @cancel="showEditCat = false">
			<view class="modal-form">
				<text class="modal-label">当前分类：{{ editingCatName }}</text>
				<input class="modal-input" type="digit" v-model="editCatBudget" placeholder="输入预算金额" />
			</view>
		</u-modal>
	</view>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { getBudget, saveBudget, getMonthlyStats, getCategoryStats, getAllCategories } from '@/utils/store';
import { onShow } from '@dcloudio/uni-app';

const now = new Date();
const year = now.getFullYear();
const month = now.getMonth() + 1;

const totalBudget = ref(0);
const usedAmount = ref(0);
const remainAmount = computed(() => totalBudget.value - usedAmount.value);
const usedPercent = computed(() => {
	if (totalBudget.value <= 0) return 0;
	return Math.min(150, Math.round((usedAmount.value / totalBudget.value) * 100));
});

const categoryBudgets = ref<{name: string; budget: number; used: number; percent: number}[]>([]);

const showSetTotal = ref(false);
const editTotal = ref('');

const showEditCat = ref(false);
const editingCatName = ref('');
const editCatBudget = ref('');


function loadBudget() {
	const stats = getMonthlyStats(year, month);
	usedAmount.value = stats.expense;

	const saved = getBudget(year, month);
	if (saved) {
		totalBudget.value = saved.totalBudget;
		const catStats = getCategoryStats(year, month);
		const catMap: Record<string, number> = {};
		catStats.forEach(c => { catMap[c.name] = c.amount; });

		categoryBudgets.value = Object.entries(saved.categoryBudgets).map(([name, budget]) => {
			const used = catMap[name] || 0;
			return {
				name,
				budget,
				used,
				percent: Math.min(150, Math.round((used / budget) * 100)),
			};
		});
	}
}

function onSetTotal() {
	const val = parseFloat(editTotal.value);
	if (val > 0) {
		totalBudget.value = val;
		const saved = getBudget(year, month);
		saveBudget({
			year, month,
			totalBudget: val,
			categoryBudgets: saved?.categoryBudgets || {},
		});
		uni.showToast({ title: '设置成功', icon: 'success' });
	}
	showSetTotal.value = false;
}

function showAddCategory() {
	const cats = getAllCategories('expense').map(c => c.name);
	uni.showActionSheet({
		itemList: cats,
		success: (res) => {
			const name = cats[res.tapIndex];
			if (name) {
				editingCatName.value = name;
				editCatBudget.value = '';
				showEditCat.value = true;
			}
		},
	});
}

function onSetCategory() {
	const val = parseFloat(editCatBudget.value);
	if (editingCatName.value && val > 0) {
		const saved = getBudget(year, month) || {
			totalBudget: totalBudget.value || 5000,
			categoryBudgets: {} as Record<string, number>,
		};
		saved.categoryBudgets = saved.categoryBudgets || {};
		saved.categoryBudgets[editingCatName.value] = val;
		saveBudget({
			year, month,
			totalBudget: saved.totalBudget,
			categoryBudgets: saved.categoryBudgets,
		});
		loadBudget();
		uni.showToast({ title: '设置成功', icon: 'success' });
	}
	showEditCat.value = false;
}

onShow(() => { loadBudget(); });
loadBudget();
</script>

<style lang="scss" scoped>
.page-budget { padding: 30rpx; padding-bottom: 120rpx; }
.section { margin-bottom: 40rpx; }
.section-title { font-size: 30rpx; font-weight: bold; display: block; margin-bottom: 20rpx; }

.total-budget-card {
	display: flex; justify-content: space-around; background: #fff;
	border-radius: 20rpx; padding: 30rpx; margin-bottom: 20rpx;
	box-shadow: 0 2rpx 12rpx rgba(0,0,0,0.06);
}
.label { font-size: 24rpx; color: #999; display: block; }
.value { font-size: 36rpx; font-weight: bold; display: block; margin-top: 8rpx; }
.value.danger { color: #dd524d; }

.set-budget-btn { margin-top: 20rpx; text-align: center; }

.category-item { background: #fff; border-radius: 16rpx; padding: 24rpx; margin-bottom: 16rpx; }
.cate-header { display: flex; justify-content: space-between; font-size: 26rpx; margin-bottom: 12rpx; }
.cate-value { color: #999; }

.empty-tip { text-align: center; padding: 40rpx; color: #ccc; font-size: 26rpx; }

.modal-form { padding: 20rpx; }
.modal-label { font-size: 28rpx; display: block; margin-bottom: 16rpx; color: #666; }
.modal-input {
	border: 1rpx solid #eee; border-radius: 12rpx; padding: 20rpx;
	font-size: 28rpx; margin: 10rpx;
}
</style>

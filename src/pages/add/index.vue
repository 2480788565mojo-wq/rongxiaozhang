<template>
	<view class="page-add">
		<view class="form-section">
			<view class="type-switch">
				<view class="type-btn" :class="{ active: formData.type === 'expense' }" @click="switchType('expense')">支出</view>
				<view class="type-btn" :class="{ active: formData.type === 'income' }" @click="switchType('income')">收入</view>
			</view>

			<view class="amount-input">
				<text class="currency">¥</text>
				<input type="digit" v-model="formData.amount" placeholder="0.00" class="amount-field" />
			</view>

			<view class="form-list">
				<view class="form-item" @click="showCategory = true">
					<text class="form-label">分类</text>
					<text class="form-value">{{ selectedCategory || '请选择' }}</text>
					<text class="arrow">></text>
				</view>
				<view class="form-item" @click="showAccount = true">
					<text class="form-label">账户</text>
					<text class="form-value">{{ formData.account || '请选择' }}</text>
					<text class="arrow">></text>
				</view>
				<view class="form-item" @click="showDatePicker = true">
					<text class="form-label">日期</text>
					<text class="form-value">{{ formData.date }}</text>
					<text class="arrow">></text>
				</view>
				<view class="form-item">
					<text class="form-label">备注</text>
					<input type="text" v-model="formData.note" placeholder="选填" class="note-input" />
				</view>
			</view>
		</view>

		<view class="btn-save">
			<u-button type="primary" size="large" shape="circle" @click="saveBill">保存</u-button>
		</view>

		<u-picker :show="showCategory" :columns="categoryColumns" @confirm="onCategoryConfirm" @cancel="showCategory = false" keyName="name"></u-picker>
		<u-picker :show="showAccount" :columns="[accountList]" @confirm="onAccountConfirm" @cancel="showAccount = false" keyName="name"></u-picker>
		<u-datetime-picker :show="showDatePicker" v-model="dateValue" mode="date" @confirm="onDateConfirm" @cancel="showDatePicker = false"></u-datetime-picker>
	</view>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue';
import { addBill, getAccounts, getAllCategories, type Account } from '@/utils/store';

const formData = reactive({
	type: 'expense' as 'expense' | 'income',
	amount: '',
	category: '',
	account: '',
	date: new Date().toISOString().slice(0, 10),
	note: '',
});

const showCategory = ref(false);
const showAccount = ref(false);
const showDatePicker = ref(false);
const dateValue = ref(Number(new Date()));
const selectedCategory = ref('');

// 分类数据 — 合并预置 + 自定义
const categoryData = computed(() => getAllCategories(formData.type));

const categoryColumns = computed(() => {
	const cats = categoryData.value;
	return [cats.map(c => ({
		name: c.name,
		children: c.children.map(ch => ({ name: ch })),
	}))];
});

const accountList = ref<{name: string}[]>([]);

function loadAccounts() {
	accountList.value = getAccounts().map(a => ({ name: a.name }));
}

switchType('expense');

function switchType(type: 'expense' | 'income') {
	formData.type = type;
	selectedCategory.value = '';
	formData.category = '';
}

function onCategoryConfirm(e: any) {
	const first = e.value[0];
	const second = e.value[1];
	if (second) {
		selectedCategory.value = `${first.name} › ${second.name}`;
		formData.category = second.name;
	}
	showCategory.value = false;
}

function onAccountConfirm(e: any) {
	formData.account = e.value[0]?.name || '';
	showAccount.value = false;
}

function onDateConfirm(e: any) {
	formData.date = e.value?.slice(0, 10) || '';
	showDatePicker.value = false;
}

function saveBill() {
	if (!formData.amount || parseFloat(formData.amount) <= 0) {
		uni.showToast({ title: '请输入金额', icon: 'none' });
		return;
	}
	if (!formData.category) {
		uni.showToast({ title: '请选择分类', icon: 'none' });
		return;
	}
	if (!formData.account) {
		uni.showToast({ title: '请选择账户', icon: 'none' });
		return;
	}

	addBill({
		type: formData.type,
		amount: parseFloat(parseFloat(formData.amount).toFixed(2)),
		category: formData.category,
		categoryPath: selectedCategory.value.split(' › '),
		account: formData.account,
		note: formData.note,
		date: formData.date,
	});

	uni.showToast({ title: '保存成功', icon: 'success' });
	setTimeout(() => uni.navigateBack(), 800);
}

import { onShow } from '@dcloudio/uni-app';
onShow(() => {
	loadAccounts();
});
loadAccounts();
</script>

<style lang="scss" scoped>
.page-add { padding: 30rpx; }
.type-switch {
	display: flex; background: #f5f5f5; border-radius: 50rpx; padding: 6rpx;
	width: 240rpx; margin: 0 auto 40rpx;
}
.type-btn {
	flex: 1; text-align: center; padding: 12rpx 0;
	border-radius: 50rpx; font-size: 28rpx; color: #999;
}
.type-btn.active { background: #fff; color: #2979ff; font-weight: bold; box-shadow: 0 2rpx 8rpx rgba(0,0,0,0.1); }
.amount-input {
	display: flex; align-items: center; justify-content: center; margin-bottom: 40rpx;
}
.currency { font-size: 48rpx; font-weight: bold; color: #333; margin-right: 10rpx; }
.amount-field { font-size: 72rpx; font-weight: bold; text-align: center; width: 400rpx; height: 100rpx; }
.form-list { background: #fff; border-radius: 20rpx; overflow: hidden; }
.form-item {
	display: flex; align-items: center; padding: 30rpx;
	border-bottom: 1rpx solid #f5f5f5;
}
.form-label { font-size: 28rpx; width: 120rpx; }
.form-value { flex: 1; font-size: 28rpx; color: #333; text-align: right; }
.note-input { flex: 1; text-align: right; font-size: 28rpx; }
.arrow { color: #ccc; margin-left: 10rpx; font-size: 28rpx; }
.btn-save { margin-top: 60rpx; padding: 0 30rpx; }
</style>

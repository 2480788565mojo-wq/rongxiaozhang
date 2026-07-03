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
				<view class="form-item" @click="selectParent">
					<text class="form-label">分类</text>
					<text class="form-value">{{ selectedCategory || '请选择' }}</text>
					<text class="arrow">></text>
				</view>
				<view class="form-item" @click="showAccount = true">
					<text class="form-label">账户</text>
					<text class="form-value">{{ formData.account || '请选择' }}</text>
					<text class="arrow">></text>
				</view>
				<picker mode="date" :value="formData.date" @change="onDateChange">
					<view class="form-item" style="border-bottom: none;">
						<text class="form-label">日期</text>
						<text class="form-value">{{ formData.date }}</text>
						<text class="arrow">></text>
					</view>
				</picker>
				<view class="form-item">
					<text class="form-label">备注</text>
					<input type="text" v-model="formData.note" placeholder="选填" class="note-input" />
				</view>
			</view>
		</view>

		<view class="btn-save">
			<u-button type="primary" size="large" shape="circle" @click="saveBill">保存</u-button>
		</view>

		<u-picker :show="showAccount" :columns="[accountList]" @confirm="onAccountConfirm" @cancel="showAccount = false" keyName="name"></u-picker>
	</view>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue';
import { addBill, getAccounts, getAllCategories, getBills, updateBill, type Account, type Bill } from '@/utils/store';
import { onShow } from '@dcloudio/uni-app';

const formData = reactive({
	type: 'expense' as 'expense' | 'income',
	amount: '',
	category: '',
	account: '',
	date: new Date().toISOString().slice(0, 10),
	note: '',
});

const showAccount = ref(false);
const selectedCategory = ref('');
const currentParents = ref<{name: string; children: string[]}[]>([]);

function selectParent() {
	const all = getAllCategories(formData.type);
	currentParents.value = all.map(c => ({ name: c.name, children: c.children }));
	const names = all.map(c => c.name);
	uni.showActionSheet({
		itemList: names,
		success: (res) => {
			const parent = currentParents.value[res.tapIndex];
			if (parent && parent.children.length > 0) {
				selectChild(parent.name, parent.children);
			}
		}
	});
}

function selectChild(parentName: string, children: string[]) {
	uni.showActionSheet({
		itemList: children,
		success: (res) => {
			const child = children[res.tapIndex];
			selectedCategory.value = parentName + ' › ' + child;
			formData.category = child;
		}
	});
}

const accountList = ref<{name: string}[]>([]);

function loadAccounts() {
	accountList.value = getAccounts().map(a => ({ name: a.name }));
}

function switchType(type: 'expense' | 'income') {
	formData.type = type;
	selectedCategory.value = '';
	formData.category = '';
}

function onAccountConfirm(e: any) {
	formData.account = e.value[0]?.name || '';
	showAccount.value = false;
}

function onDateChange(e: any) {
	formData.date = (e.detail.value || '').slice(0, 10);
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

	const billData = {
		type: formData.type,
		amount: parseFloat(parseFloat(formData.amount).toFixed(2)),
		category: formData.category,
		categoryPath: selectedCategory.value.split(' › '),
		account: formData.account,
		note: formData.note,
		date: formData.date,
	};

	if (editId.value) {
		updateBill(editId.value, billData);
	} else {
		addBill(billData);
	}

	uni.showToast({ title: editId.value ? '更新成功' : '保存成功', icon: 'success' });
	setTimeout(() => uni.navigateBack(), 800);
}

const editId = ref('');

onShow(() => {
	loadAccounts();
	// 检查是否有编辑的账单ID
	const pages = getCurrentPages();
	const page = pages[pages.length - 1];
	if (page?.options?.id) {
		editId.value = page.options.id;
		const bills = getBills();
		const bill = bills.find(b => b._id === editId.value);
		if (bill) {
			formData.type = bill.type;
			formData.amount = String(bill.amount);
			formData.category = bill.category;
			formData.account = bill.account;
			formData.date = bill.date;
			formData.note = bill.note;
			const path = bill.categoryPath || [];
			if (path.length >= 2) {
				selectedCategory.value = path[0] + ' › ' + path[1];
			} else if (bill.category) {
				selectedCategory.value = bill.category;
			}
		}
	}
});
switchType('expense');
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

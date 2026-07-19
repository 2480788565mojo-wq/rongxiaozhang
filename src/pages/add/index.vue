<template>
	<view class="page-add">
		<view class="page-heading">
			<text class="heading-title">手动记一笔</text>
			<text class="heading-subtitle">填写账单明细</text>
		</view>
		<view class="form-section">
			<!-- 收支类型切换：支出 / 收入 -->
			<view class="type-switch">
				<button class="type-btn" :class="{ active: formData.type === 'expense' }" @click="switchType('expense')">支出</button>
				<button class="type-btn" :class="{ active: formData.type === 'income' }" @click="switchType('income')">收入</button>
			</view>

			<!-- 金额输入框 -->
			<view class="amount-input" :class="formData.type">
				<text class="currency">¥</text>
				<input type="digit" v-model="formData.amount" placeholder="0.00" class="amount-field" />
			</view>

			<view class="form-list">
				<!-- 选择分类：先选大类再选子类 -->
				<view class="form-item" @click="selectParent">
					<text class="form-label">分类</text>
					<text class="form-value">{{ selectedCategory || '请选择' }}</text>
					<text class="arrow">></text>
				</view>
				<!-- 选择账户 -->
				<view class="form-item" @click="showAccount = true">
					<text class="form-label">账户</text>
					<text class="form-value">{{ formData.account || '请选择' }}</text>
					<text class="arrow">></text>
				</view>
				<!-- 选择日期，默认今天 -->
				<picker mode="date" :value="formData.date" @change="onDateChange">
					<view class="form-item" style="border-bottom: none;">
						<text class="form-label">日期</text>
						<text class="form-value">{{ formData.date }}</text>
						<text class="arrow">></text>
					</view>
				</picker>
				<!-- 备注，选填 -->
				<view class="form-item">
					<text class="form-label">备注</text>
					<input type="text" v-model="formData.note" placeholder="选填" class="note-input" />
				</view>
			</view>
		</view>

		<view class="btn-save">
			<u-button class="save-button" type="primary" size="large" @click="saveBill">保存</u-button>
		</view>

		<u-picker :show="showAccount" :columns="[accountList]" @confirm="onAccountConfirm" @cancel="showAccount = false" keyName="name"></u-picker>
	</view>
</template>

<script setup lang="ts">
// 导入 Vue 响应式 API 和项目数据操作函数
import { ref, reactive } from 'vue';
import { addBill, getAccounts, getAllCategories, getBills, updateBill, type Account, type Bill } from '@/utils/store';
import { onShow } from '@dcloudio/uni-app';

// 表单数据：类型（支出/收入）、金额、分类、账户、日期、备注
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

// 选择大类：弹出可选的大类列表，用户选择后再选子类
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

// 选择子分类
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

// 加载账户列表供用户选择
function loadAccounts() {
	accountList.value = getAccounts().map(a => ({ name: a.name }));
}

// 切换支出/收入类型时，清空已选的分类
function switchType(type: 'expense' | 'income') {
	formData.type = type;
	selectedCategory.value = '';
	formData.category = '';
}

// 用户从 picker 中选择了账户
function onAccountConfirm(e: any) {
	formData.account = e.value[0]?.name || '';
	showAccount.value = false;
}

// 用户选择了日期
function onDateChange(e: any) {
	formData.date = (e.detail.value || '').slice(0, 10);
}

// 保存账单：先校验金额/分类/账户是否已填写，再保存或更新
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

// 页面显示时加载数据，并检查是否有编辑模式（从账单列表传过来的ID）
onShow(() => {
	loadAccounts();
	const pages = getCurrentPages();
	const page = pages[pages.length - 1] as any;
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
// 初始化：默认选中支出类型，加载账户列表
switchType('expense');
loadAccounts();
</script>

<style lang="scss" scoped>
.page-add { min-height: 100vh; padding: 24rpx 28rpx 80rpx; box-sizing: border-box; }
.page-heading { display: flex; margin-bottom: 24rpx; flex-direction: column; }
.heading-title { color: var(--color-text); font-size: 44rpx; font-weight: 600; }
.heading-subtitle { margin-top: 6rpx; color: var(--color-text-secondary); font-size: 24rpx; }
.form-section { padding: 30rpx; border-radius: var(--radius-lg); background: var(--color-surface); box-shadow: var(--shadow-sm); }
.type-switch {
	display: grid; grid-template-columns: 1fr 1fr; gap: 8rpx; width: 280rpx; margin: 0 auto 38rpx;
	padding: 6rpx; border-radius: 24rpx; background: var(--color-surface-muted);
}
.type-btn {
	height: 66rpx; margin: 0; padding: 0; border: 0; border-radius: 20rpx; color: var(--color-text-secondary);
	background: transparent; font-size: 27rpx; line-height: 66rpx; text-align: center;
}
.type-btn:first-child.active { color: var(--color-danger); background: #fff0ef; }
.type-btn:last-child.active { color: #248c41; background: #eaf8ee; }
.amount-input {
	display: flex; align-items: center; justify-content: center; min-height: 150rpx; margin-bottom: 30rpx;
	border-bottom: 1rpx solid var(--color-border-muted);
}
.currency { margin-right: 10rpx; color: var(--color-text); font-size: 48rpx; font-weight: 700; }
.amount-field { width: 400rpx; height: 100rpx; color: var(--color-danger); font-family: var(--font-mono); font-size: 64rpx; font-weight: 700; text-align: center; }
.amount-input.income .amount-field { color: var(--color-success); }
.form-list { overflow: hidden; }
.form-item {
	display: flex; align-items: center; min-height: 88rpx; padding: 0 8rpx;
	border-bottom: 1rpx solid var(--color-border-muted);
}
.form-label { width: 120rpx; color: var(--color-text-secondary); font-size: 26rpx; }
.form-value { flex: 1; overflow: hidden; color: var(--color-text); font-size: 27rpx; text-align: right; text-overflow: ellipsis; white-space: nowrap; }
.note-input { flex: 1; color: var(--color-text); font-size: 27rpx; text-align: right; }
.arrow { margin-left: 10rpx; color: var(--color-primary); font-size: 28rpx; }
.btn-save { margin-top: 28rpx; }
.save-button { border: 0 !important; border-radius: var(--radius-pill) !important; color: #fff !important; background: var(--color-primary) !important; box-shadow: 0 8rpx 20rpx rgba(var(--color-primary-rgb), .18) !important; font-weight: 600; }
</style>

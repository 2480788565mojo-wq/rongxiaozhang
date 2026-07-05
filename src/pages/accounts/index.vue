<template>
	<view class="page-accounts">
		<!-- 总资产卡片 -->
		<view class="total-card">
			<text class="total-label">总资产</text>
			<text class="total-amount">¥{{ totalBalance.toFixed(2) }}</text>
		</view>

		<!-- 账户列表 -->
		<view class="account-list">
			<view class="account-item" v-for="item in accounts" :key="item._id" @click="editAccount(item)">
				<view class="account-icon">{{ getIcon(item.name) }}</view>
				<view class="account-info">
					<text class="account-name">{{ item.name }}</text>
					<text class="account-type">{{ item.type }}</text>
				</view>
				<text class="account-balance">¥{{ item.balance.toFixed(2) }}</text>
			</view>
		</view>

		<!-- 添加账户按钮 -->
		<view class="btn-add">
			<u-button type="primary" shape="circle" @click="showAddModal = true">添加账户</u-button>
		</view>

		<u-modal :show="showAddModal" title="添加账户" @confirm="onAddAccount" @cancel="showAddModal = false">
			<view class="modal-form">
				<input class="modal-input" v-model="newName" placeholder="账户名称（如：储蓄卡）" />
				<input class="modal-input" v-model="newBalance" placeholder="初始余额" type="digit" />
			</view>
		</u-modal>
	</view>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { getAccounts, addAccount, deleteAccount, type Account } from '@/utils/store';
import { onShow } from '@dcloudio/uni-app';

const accounts = ref<Account[]>([]);
// 总资产 = 所有账户余额之和
const totalBalance = computed(() => accounts.value.reduce((s, a) => s + a.balance, 0));
const showAddModal = ref(false);
const newName = ref('');
const newBalance = ref('');

// 从本地存储加载账户列表
function loadAccounts() {
	accounts.value = getAccounts();
}

// 根据账户名称显示对应的 emoji 图标
function getIcon(name: string): string {
	const m: Record<string, string> = {
		'微信钱包':'💳','支付宝':'💳','银行卡':'🏦','现金':'💵',
	};
	return Object.keys(m).find(k => name.includes(k)) ? m[Object.keys(m).find(k => name.includes(k))!] : '💰';
}

// 添加新账户
function onAddAccount() {
	if (newName.value.trim()) {
		addAccount(newName.value.trim(), parseFloat(newBalance.value) || 0);
		newName.value = '';
		newBalance.value = '';
		loadAccounts();
	}
	showAddModal.value = false;
}

// 长按/点击账户弹出操作菜单（目前支持删除）
function editAccount(item: Account) {
	uni.showActionSheet({
		itemList: ['删除账户'],
		success: (res) => {
			if (res.tapIndex === 0) {
				deleteAccount(item._id);
				loadAccounts();
			}
		},
	});
}

onShow(() => { loadAccounts(); });
loadAccounts();
</script>

<style lang="scss" scoped>
.page-accounts { padding: 30rpx; padding-bottom: 120rpx; }
.total-card {
	background: linear-gradient(135deg, #2979ff, #5b8ff9);
	border-radius: 20rpx; padding: 40rpx; text-align: center; color: #fff; margin-bottom: 30rpx;
}
.total-label { font-size: 26rpx; opacity: 0.8; display: block; }
.total-amount { font-size: 52rpx; font-weight: bold; display: block; margin-top: 16rpx; }

.account-item {
	display: flex; align-items: center; background: #fff;
	border-radius: 16rpx; padding: 30rpx; margin-bottom: 16rpx;
	box-shadow: 0 2rpx 8rpx rgba(0,0,0,0.04);
}
.account-icon {
	width: 72rpx; height: 72rpx; border-radius: 50%; background: #f5f5f5;
	display: flex; align-items: center; justify-content: center; font-size: 32rpx;
}
.account-info { flex: 1; margin-left: 20rpx; }
.account-name { font-size: 28rpx; font-weight: bold; display: block; }
.account-type { font-size: 22rpx; color: #999; display: block; margin-top: 4rpx; }
.account-balance { font-size: 30rpx; font-weight: bold; }

.btn-add { margin-top: 30rpx; padding: 0 30rpx; }
.modal-form { padding: 20rpx; }
.modal-input {
	border: 1rpx solid #eee; border-radius: 12rpx; padding: 20rpx;
	font-size: 28rpx; margin-bottom: 16rpx;
}
</style>

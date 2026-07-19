<template>
  <view class="page">
    <view class="balance-band"><text>账户总余额</text><text class="balance-value numeric">¥{{ store.totalBalance.toFixed(2) }}</text></view>
    <view class="account-list">
      <view v-for="account in store.accounts" :key="account.id" class="account-row" @click="edit(account)">
        <view class="account-icon">{{ iconFor(account.type) }}</view>
        <view class="account-copy"><text>{{ account.name }}</text><text>{{ account.type }}</text></view>
        <text class="account-balance numeric">¥{{ account.balance.toFixed(2) }}</text>
      </view>
    </view>
    <button class="add" @click="openCreate">添加账户</button>

    <u-modal :show="modalVisible" :title="editingId ? '编辑账户' : '添加账户'" show-cancel-button @confirm="submit" @cancel="modalVisible = false">
      <view class="form">
        <input v-model="form.name" placeholder="账户名称" maxlength="64" />
        <input v-model="form.type" placeholder="账户类型" maxlength="32" />
        <input v-model.number="form.balance" type="digit" placeholder="余额" />
        <button v-if="editingId" class="delete" @click="confirmDelete">删除账户</button>
      </view>
    </u-modal>
  </view>
</template>

<script setup lang="ts">
import { reactive, ref } from "vue";
import { onShow } from "@dcloudio/uni-app";
import { useAccountStore } from "@/stores/account";
import { useLedgerStore } from "@/stores/ledger";
import type { Account } from "@/types";

const store = useAccountStore();
const ledgerStore = useLedgerStore();
const modalVisible = ref(false);
const editingId = ref(0);
const form = reactive({ name: "", type: "其他", balance: 0 });

async function load() {
  if (!ledgerStore.currentId) await ledgerStore.fetchLedgers();
  if (ledgerStore.currentId) await store.fetchAccounts(ledgerStore.currentId);
}
onShow(() => void load());
function iconFor(type: string) { return type.includes("银行卡") ? "银" : type.includes("现金") ? "现" : "账"; }
function openCreate() { editingId.value = 0; Object.assign(form, { name: "", type: "其他", balance: 0 }); modalVisible.value = true; }
function edit(account: Account) { editingId.value = account.id; Object.assign(form, { name: account.name, type: account.type, balance: account.balance }); modalVisible.value = true; }
async function submit() {
  if (!form.name.trim() || !form.type.trim() || !ledgerStore.currentId) return;
  if (editingId.value) await store.update(editingId.value, { name: form.name.trim(), type: form.type.trim(), balance: Number(form.balance) });
  else await store.create({ ledger_id: ledgerStore.currentId, name: form.name.trim(), type: form.type.trim(), balance: Number(form.balance) });
  modalVisible.value = false;
  uni.showToast({ title: "已保存", icon: "success" });
}
function confirmDelete() {
  uni.showModal({ title: "删除账户", content: "确定删除这个账户吗？", success: async (result) => {
    if (!result.confirm || !editingId.value) return;
    await store.remove(editingId.value);
    modalVisible.value = false;
  } });
}
</script>

<style scoped>
.page { min-height: 100vh; padding: 28rpx; box-sizing: border-box; }
.balance-band { display: flex; flex-direction: column; padding: 34rpx; border-radius: var(--radius-lg); background: var(--color-surface); box-shadow: var(--shadow-sm); }
.balance-band > text:first-child { color: var(--color-text-secondary); font-size: 25rpx; }
.balance-value { margin-top: 18rpx; overflow: hidden; font-size: 56rpx; font-weight: 700; text-overflow: ellipsis; white-space: nowrap; }
.account-list { margin-top: 18rpx; overflow: hidden; border-radius: var(--radius-lg); background: var(--color-surface); box-shadow: var(--shadow-sm); }
.account-row { display: flex; align-items: center; min-height: 104rpx; padding: 0 24rpx; border-bottom: 1rpx solid var(--color-border-muted); }
.account-row:last-child { border-bottom: 0; }
.account-icon { display: flex; align-items: center; justify-content: center; width: 60rpx; height: 60rpx; border-radius: 20rpx; color: var(--color-primary); background: var(--color-primary-soft); font-weight: 600; }
.account-copy { display: flex; flex: 1; flex-direction: column; margin-left: 18rpx; }
.account-copy text:last-child { margin-top: 4rpx; color: var(--color-text-secondary); font-size: 22rpx; }
.account-balance { max-width: 240rpx; overflow: hidden; font-weight: 600; text-overflow: ellipsis; white-space: nowrap; }
.add { margin-top: 24rpx; color: #fff; background: var(--color-primary); border-radius: var(--radius-pill); }
.form { width: 100%; padding: 20rpx; box-sizing: border-box; }
.form input { height: 80rpx; margin-bottom: 14rpx; padding: 0 20rpx; border-radius: 20rpx; background: var(--color-surface-muted); }
.delete { margin-top: 18rpx; color: var(--color-danger); background: transparent; }
</style>

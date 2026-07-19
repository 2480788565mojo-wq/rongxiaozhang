<template>
  <view class="page">
    <button class="calculate" :loading="loading" @click="calculate">重新计算</button>
    <view v-if="!loading && !settlements.length" class="empty">当前没有需要结算的款项</view>
    <view v-for="(item, index) in settlements" :key="index" class="transfer">
      <text class="person">{{ item.from_user_name }}</text>
      <view class="direction"><text>支付</text><text class="amount">¥{{ item.amount.toFixed(2) }}</text></view>
      <text class="person right">{{ item.to_user_name }}</text>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { onLoad } from "@dcloudio/uni-app";
import { settleLedger } from "@/api/ledgers";

interface Settlement { from_user_name: string; to_user_name: string; amount: number; }
const ledgerId = ref(0);
const loading = ref(false);
const settlements = ref<Settlement[]>([]);
onLoad((query) => { ledgerId.value = Number(query?.id); void calculate(); });
async function calculate() {
  if (!ledgerId.value) return;
  loading.value = true;
  try { settlements.value = (await settleLedger(ledgerId.value)).settlements as Settlement[]; }
  finally { loading.value = false; }
}
</script>

<style scoped>
.page { min-height: 100vh; padding: 28rpx; box-sizing: border-box; }
.calculate { color: #fff; background: var(--color-primary); border-radius: var(--radius-pill); }
.empty { margin-top: 18rpx; padding: 140rpx 24rpx; border-radius: var(--radius-lg); color: var(--color-text-secondary); background: var(--color-surface); text-align: center; }
.transfer { display: grid; grid-template-columns: 1fr 160rpx 1fr; align-items: center; gap: 12rpx; margin-top: 18rpx; padding: 26rpx; border-radius: var(--radius-lg); background: var(--color-surface); box-shadow: var(--shadow-sm); }
.person { overflow: hidden; font-weight: 600; text-overflow: ellipsis; white-space: nowrap; }
.person.right { text-align: right; }
.direction { display: flex; flex-direction: column; align-items: center; color: var(--color-text-secondary); font-size: 22rpx; }
.amount { color: var(--color-primary); font-size: 28rpx; font-weight: 700; }
</style>

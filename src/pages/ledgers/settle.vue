<template>
  <view class="page">
    <button class="calculate" :loading="loading" @click="calculate">重新计算</button>
    <view v-if="loadError" class="load-error">{{ loadError }}</view>
    <view v-if="!loading && !loadError && !settlements.length" class="empty">当前没有需要结算的款项</view>
    <view v-for="(item, index) in settlements" :key="`${item.from_user_id}-${item.to_user_id}`" class="transfer">
      <view class="transfer-row">
        <text class="person">{{ item.from_user_name }}</text>
        <view class="direction"><text>支付</text><text class="amount">¥{{ item.amount.toFixed(2) }}</text></view>
        <text class="person right">{{ item.to_user_name }}</text>
      </view>
      <button
        v-if="canConfirm(item)"
        class="confirm-settle"
        :disabled="settlingIndex !== null"
        :loading="settlingIndex === index"
        @click="confirm(item, index)"
      >
        标记已结算
      </button>
      <text v-else class="manual">{{ manualHint(item) }}</text>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { onLoad } from "@dcloudio/uni-app";
import { confirmSettlement, settleLedger, type Settlement } from "@/api/ledgers";
import { useUserStore } from "@/stores/user";

const userStore = useUserStore();
const ledgerId = ref(0);
const loading = ref(false);
const settlingIndex = ref<number | null>(null);
const settlements = ref<Settlement[]>([]);
const loadError = ref("");

onLoad(async (query) => {
  await userStore.ensureUser();
  const id = Number(query?.id);
  if (!Number.isSafeInteger(id) || id <= 0) {
    loadError.value = "账本编号无效，请返回账本列表重试";
    return;
  }
  ledgerId.value = id;
  await calculate();
});

async function calculate() {
  if (!ledgerId.value) return;
  loading.value = true;
  loadError.value = "";
  try {
    settlements.value = (await settleLedger(ledgerId.value)).settlements;
  } catch (error) {
    // 失败时不能继续展示上一次的结算列表，避免用户按旧金额转账。
    settlements.value = [];
    loadError.value = error instanceof Error ? error.message : "结算计算失败，请重试";
  } finally {
    loading.value = false;
  }
}

function canConfirm(item: Settlement) {
  const current = userStore.user?.id;
  return Boolean(
    item.share_ids.length &&
      current &&
      (current === item.from_user_id || current === item.to_user_id),
  );
}

function manualHint(item: Settlement) {
  if (!item.share_ids.length) return "这笔是多人抵消后的转账，请到账单详情逐笔处理";
  return "这笔由其他成员确认";
}

async function confirm(item: Settlement, index: number) {
  if (settlingIndex.value !== null) return;
  settlingIndex.value = index;
  try {
    const response = await confirmSettlement(ledgerId.value, {
      from_user_id: item.from_user_id,
      to_user_id: item.to_user_id,
      share_ids: item.share_ids,
    });
    settlements.value = response.settlements;
    uni.showToast({ title: "已标记结算", icon: "success" });
  } catch (error) {
    uni.showToast({
      title: error instanceof Error ? error.message : "结算失败，请重试",
      icon: "none",
    });
    await calculate();
  } finally {
    settlingIndex.value = null;
  }
}
</script>

<style scoped>
.page { min-height: 100vh; padding: 28rpx; box-sizing: border-box; }
.calculate { width: 100%; height: var(--button-height-lg); border: 0; color: #fff; background: var(--color-primary); border-radius: var(--radius-pill); font-size: var(--button-font-lg); font-weight: 600; line-height: var(--button-height-lg); }
.empty { margin-top: 16rpx; padding: 130rpx 24rpx; border-radius: var(--radius-lg); color: var(--color-text-secondary); background: var(--color-surface); box-shadow: var(--shadow-sm); text-align: center; }
.load-error { margin-top: 16rpx; padding: 20rpx 22rpx; border-radius: var(--radius-lg); color: var(--color-danger); background: #fff0ef; font-size: 24rpx; }
.transfer { margin-top: 16rpx; padding: 24rpx; border-radius: var(--radius-lg); background: var(--color-surface); box-shadow: var(--shadow-sm); }
.transfer-row { display: grid; grid-template-columns: 1fr 160rpx 1fr; align-items: center; gap: 12rpx; }
.person { overflow: hidden; font-size: 27rpx; font-weight: 600; text-overflow: ellipsis; white-space: nowrap; }
.person.right { text-align: right; }
.direction { display: flex; flex-direction: column; align-items: center; color: var(--color-text-secondary); font-size: 22rpx; }
.amount { color: var(--color-primary); font-size: 28rpx; font-weight: 700; }
.confirm-settle { width: 100%; height: var(--button-height-md); margin-top: 18rpx; border: 0; border-radius: var(--radius-pill); color: #fff; background: var(--color-primary); font-size: var(--button-font-md); font-weight: 600; line-height: var(--button-height-md); }
.manual { display: block; margin-top: 16rpx; color: var(--color-text-secondary); font-size: 22rpx; line-height: 1.5; }
</style>

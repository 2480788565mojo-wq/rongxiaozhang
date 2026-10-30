<template>
  <view
    v-if="store.alertVisible"
    class="budget-overlay"
    :class="isBlocked ? 'is-blocked' : 'is-warning'"
  >
    <view class="budget-card">
      <view class="budget-icon">{{ isBlocked ? "!" : "%" }}</view>
      <text class="budget-title">
        {{ isBlocked ? "本月预算已超限" : `预算已使用 ${percentage}%` }}
      </text>
      <text v-if="store.alertData?.category" class="budget-category">
        {{ store.alertData.category }}
      </text>
      <text class="budget-detail">
        已花 ¥{{ spent }} / ¥{{ budget }}
      </text>
      <text v-if="remaining < 0" class="budget-remaining">
        超出 ¥{{ Math.abs(remaining).toFixed(2) }}
      </text>
      <view class="budget-actions">
        <button v-if="hasAction" class="budget-cancel" @click="store.cancelAlert">取消</button>
        <button class="budget-confirm" @click="store.confirmAlert">
          {{ hasAction ? "仍然记账" : "知道了" }}
        </button>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useBudgetStore } from "@/stores/budget";

const store = useBudgetStore();
const isBlocked = computed(() => store.alertData?.risk_level === "blocked");
const percentage = computed(() => store.alertData?.percentage ?? 0);
const spent = computed(() => store.alertData?.spent?.toFixed(2) ?? "0.00");
const budget = computed(() => store.alertData?.budget?.toFixed(2) ?? "0.00");
const remaining = computed(() => store.alertData?.remaining ?? 0);
const hasAction = computed(() => store.hasAlertAction);
</script>

<style scoped>
.budget-overlay {
  position: fixed;
  inset: 0;
  z-index: 1200;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 48rpx;
  box-sizing: border-box;
  background: rgba(20, 20, 24, 0.55);
}
.budget-overlay.is-blocked { background: rgba(255, 59, 48, 0.22); align-items: flex-start; padding-top: 180rpx; }
.budget-card {
  display: flex;
  width: 100%;
  max-width: 620rpx;
  padding: 42rpx 34rpx 30rpx;
  border-radius: 36rpx;
  align-items: center;
  flex-direction: column;
  background: var(--color-surface);
  box-shadow: 0 24rpx 70rpx rgba(0, 0, 0, 0.24);
}
.is-blocked .budget-card { border: 2rpx solid rgba(255, 59, 48, 0.35); }
.budget-icon {
  display: flex;
  width: 84rpx;
  height: 84rpx;
  border-radius: 50%;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 42rpx;
  font-weight: 700;
}
.is-warning .budget-icon { background: var(--color-warning); }
.is-blocked .budget-icon { background: var(--color-danger); }
.budget-title { margin-top: 24rpx; color: var(--color-text); font-size: 34rpx; font-weight: 700; text-align: center; }
.budget-category { margin-top: 18rpx; color: var(--color-text); font-size: 28rpx; font-weight: 600; }
.budget-detail { margin-top: 10rpx; color: var(--color-text-secondary); font-size: 25rpx; }
.budget-remaining { margin-top: 8rpx; color: var(--color-danger); font-size: 25rpx; font-weight: 600; }
.budget-actions { display: flex; width: 100%; margin-top: 32rpx; gap: 16rpx; }
.budget-actions button { flex: 1; height: var(--button-height-md); margin: 0; border: 0; border-radius: var(--radius-pill); font-size: var(--button-font-md); font-weight: 600; line-height: var(--button-height-md); }
.budget-cancel { color: var(--color-text-secondary); background: var(--color-surface-muted); }
.budget-confirm { color: #fff; background: var(--color-primary); }
.is-blocked .budget-confirm { background: var(--color-danger); }
</style>

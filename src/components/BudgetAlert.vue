<template>
  <u-modal
    :show="store.alertVisible"
    :title="isBlocked ? '预算已超限' : '预算提醒'"
    confirm-text="知道了"
    @confirm="store.dismissAlert"
  >
    <view class="budget-alert">
      <view class="budget-alert__icon" :class="isBlocked ? 'is-blocked' : 'is-warning'">
        {{ isBlocked ? "!" : "%" }}
      </view>
      <text class="budget-alert__title">
        {{ isBlocked ? "本月该分类预算已用尽" : `预算已使用 ${percentage}%` }}
      </text>
      <text v-if="store.alertData?.category" class="budget-alert__detail">
        {{ store.alertData.category }}：已花 ¥{{ spent }} / ¥{{ budget }}
      </text>
    </view>
  </u-modal>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useBudgetStore } from "@/stores/budget";

const store = useBudgetStore();
const isBlocked = computed(() => store.alertData?.risk_level === "blocked");
const percentage = computed(() => store.alertData?.percentage ?? 0);
const spent = computed(() => store.alertData?.spent?.toFixed(2) ?? "0.00");
const budget = computed(() => store.alertData?.budget?.toFixed(2) ?? "0.00");
</script>

<style scoped>
.budget-alert {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20rpx;
  padding: 24rpx 12rpx;
  text-align: center;
}
.budget-alert__icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 72rpx;
  height: 72rpx;
  border-radius: 50%;
  color: #fff;
  font-size: 36rpx;
  font-weight: 700;
}
.is-warning { background: var(--color-warning); }
.is-blocked { background: var(--color-danger); }
.budget-alert__title { color: var(--color-text); font-size: 30rpx; font-weight: 700; }
.budget-alert__detail { color: var(--color-text-secondary); font-size: 26rpx; }
</style>

<template>
  <view class="page">
    <view v-if="bill" class="detail">
      <view class="amount-block">
        <text class="type-label">{{ bill.type === "expense" ? "支出" : "收入" }}</text>
        <text class="amount" :class="bill.type">{{ bill.type === "expense" ? "-" : "+" }}¥{{ bill.amount.toFixed(2) }}</text>
        <text class="category">{{ bill.category }}{{ bill.subcategory ? ` · ${bill.subcategory}` : "" }}</text>
      </view>
      <view class="rows">
        <view class="row"><text>日期</text><text>{{ bill.bill_date }}</text></view>
        <view class="row"><text>账户</text><text>{{ bill.account || "未设置" }}</text></view>
        <view class="row"><text>备注</text><text>{{ bill.note || "无" }}</text></view>
        <view class="row"><text>录入方式</text><text>{{ bill.ai_parsed ? "AI 记账" : "手动记账" }}</text></view>
      </view>
      <view v-if="bill.shares.length" class="shares">
        <text class="section-title">AA 分摊</text>
        <view v-for="share in bill.shares" :key="share.user_id" class="share-row">
          <text>用户{{ share.user_id }}</text>
          <text>¥{{ share.share_amount.toFixed(2) }}</text>
          <text :class="share.settled ? 'settled' : 'pending'">{{ share.settled ? "已结算" : "待结算" }}</text>
        </view>
      </view>
      <view class="actions">
        <button class="edit-btn" @click="editBill">修改账单</button>
        <button class="delete-btn" :disabled="deleting" @click="onDelete">删除账单</button>
      </view>
    </view>
    <view v-else class="loading">{{ loading ? "加载中" : "账单不存在" }}</view>
</view>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { onLoad, onShow } from "@dcloudio/uni-app";
import { getBill, deleteBill } from "@/api/bills";
import { useBillStore } from "@/stores/bill";
import type { Bill } from "@/types";

const bill = ref<Bill | null>(null);
const loading = ref(true);
const deleting = ref(false);
const billStore = useBillStore();
let billId = 0;

onLoad((query) => { billId = Number(query?.id); });
onShow(async () => {
  loading.value = true;
  try { bill.value = await getBill(billId); }
  catch (error) { uni.showToast({ title: error instanceof Error ? error.message : "加载失败", icon: "none" }); }
  finally { loading.value = false; }
});
function editBill() { uni.navigateTo({ url: `/pages/add/index?id=${billId}` }); }
async function onDelete() {
  if (deleting.value) return;
  deleting.value = true;
  try {
  const res = await uni.showModal({ title: "确认删除", content: "确定要删除这笔账单吗？删除后无法恢复。", confirmText: "删除", confirmColor: "#E53935" });
  if (!res.confirm) return;
    await deleteBill(billId);
    billStore.remove(billId);
    uni.showToast({ title: "已删除", icon: "success" });
    setTimeout(() => uni.navigateBack(), 800);
  } catch (error) {
    uni.showToast({ title: error instanceof Error ? error.message : "删除失败", icon: "none" });
  } finally { deleting.value = false; }
}
</script>

<style scoped>
.page { min-height: 100vh; padding: 28rpx; box-sizing: border-box; }
.detail { overflow: hidden; border-radius: var(--radius-lg); background: var(--color-surface); box-shadow: var(--shadow-card); }
.amount-block {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 46rpx 24rpx 36rpx;
  border-bottom: 1rpx solid var(--color-border-muted);
  background: linear-gradient(135deg, #f4f9ff 0%, #ffffff 62%);
}
.type-label { color: var(--color-text-secondary); font-size: 24rpx; }
.amount { margin-top: 12rpx; font-family: var(--font-mono); font-size: 56rpx; font-weight: 700; }
.amount.expense { color: var(--color-danger); }
.amount.income { color: var(--color-success); }
.category { margin-top: 14rpx; color: var(--color-text); }
.rows, .shares { padding: 10rpx 26rpx; }
.row, .share-row { display: flex; align-items: center; justify-content: space-between; min-height: 86rpx; border-bottom: 1rpx solid var(--color-border-muted); }
.row text:first-child { color: var(--color-text-secondary); }
.section-title { display: block; padding: 22rpx 0 8rpx; font-size: 30rpx; font-weight: 600; }
.share-row { gap: 16rpx; }
.share-row text:nth-child(2) { margin-left: auto; }
.settled { color: var(--color-success); }
.pending { color: var(--color-warning); }
.loading { margin-top: 22rpx; padding: 130rpx 24rpx; border-radius: var(--radius-lg); color: var(--color-text-secondary); background: var(--color-surface); box-shadow: var(--shadow-sm); text-align: center; }
.actions { padding: 26rpx 0; text-align: center; }
.delete-btn { width: 60%; height: var(--button-height-lg); padding: 0; border-radius: var(--radius-pill); color: var(--color-danger); background: none; border: 1rpx solid var(--color-danger); font-size: var(--button-font-lg); font-weight: 600; line-height: var(--button-height-lg); }
.edit-btn { width: 60%; height: var(--button-height-lg); margin-bottom: 18rpx; border: 0; border-radius: var(--radius-pill); color: white; background: var(--color-primary); font-size: var(--button-font-lg); font-weight: 600; line-height: var(--button-height-lg); }
</style>

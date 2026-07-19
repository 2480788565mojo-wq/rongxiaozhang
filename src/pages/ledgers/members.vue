<template>
  <view class="page">
    <view v-for="member in ledger?.members || []" :key="member.user_id" class="member">
      <view class="avatar">{{ (member.nickname || "用").slice(0, 1) }}</view>
      <view class="copy">
        <text>{{ member.nickname || `用户${member.user_id}` }}</text>
        <text class="role">{{ roleName(member.role) }}</text>
      </view>
    </view>
    <view v-if="ledger?.invite_code" class="invite">邀请码：{{ ledger.invite_code }}</view>
  </view>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { onLoad } from "@dcloudio/uni-app";
import { getLedger } from "@/api/ledgers";
import type { Ledger, LedgerRole } from "@/types";

const ledger = ref<Ledger | null>(null);
onLoad(async (query) => { ledger.value = await getLedger(Number(query?.id)); });
function roleName(role: LedgerRole) { return role === "owner" ? "创建者" : role === "admin" ? "管理员" : "成员"; }
</script>

<style scoped>
.page { min-height: 100vh; padding: 28rpx; box-sizing: border-box; }
.member { display: flex; align-items: center; gap: 20rpx; min-height: 104rpx; padding: 0 22rpx; border-bottom: 1rpx solid var(--color-border-muted); background: var(--color-surface); }
.member:first-child { border-radius: var(--radius-lg) var(--radius-lg) 0 0; }
.member:last-of-type { border-bottom: 0; border-radius: 0 0 var(--radius-lg) var(--radius-lg); }
.avatar { display: flex; align-items: center; justify-content: center; width: 64rpx; height: 64rpx; border-radius: 22rpx; color: var(--color-primary); background: var(--color-primary-soft); font-weight: 600; }
.copy { display: flex; flex-direction: column; }
.role { margin-top: 4rpx; color: var(--color-text-secondary); font-size: 23rpx; }
.invite { margin-top: 20rpx; padding: 24rpx; border-radius: var(--radius-lg); color: var(--color-primary); background: var(--color-primary-soft); text-align: center; }
</style>

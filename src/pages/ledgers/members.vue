<template>
  <view class="page">
    <view class="member-list">
      <view v-for="member in ledger?.members || []" :key="member.user_id" class="member">
        <view class="avatar">{{ (member.nickname || "用").slice(0, 1) }}</view>
        <view class="copy">
          <text>{{ member.nickname || `用户${member.user_id}` }}</text>
          <text class="role">{{ roleName(member.role) }}</text>
        </view>
        <view v-if="canManage(member)" class="actions">
          <button
            v-if="canChangeRole(member)"
            class="action"
            :disabled="saving"
            @click="toggleRole(member)"
          >
            {{ member.role === "admin" ? "设为成员" : "设为管理员" }}
          </button>
          <button
            v-if="canRemove(member)"
            class="action danger"
            :disabled="saving"
            @click="remove(member)"
          >
            移除
          </button>
        </view>
      </view>
    </view>
    <view v-if="ledger?.invite_code" class="invite">
      <view>
        <text class="invite-label">邀请码</text>
        <text class="invite-code">{{ ledger.invite_code }}</text>
      </view>
      <button class="copy" @click="copyInvite">复制邀请码</button>
    </view>
    <text v-if="ledger?.invite_code" class="invite-hint">
      把邀请码发给对方，对方在“账本管理 → 加入共享账本”中输入即可添加。
    </text>
    <view v-if="loadError" class="load-error">{{ loadError }}</view>
  </view>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { onLoad } from "@dcloudio/uni-app";
import {
  getLedger,
  removeLedgerMember,
  updateMemberRole,
} from "@/api/ledgers";
import { useUserStore } from "@/stores/user";
import type { Ledger, LedgerMember, LedgerRole } from "@/types";

const userStore = useUserStore();
const ledger = ref<Ledger | null>(null);
const loadError = ref("");
const saving = ref(false);

const currentMember = computed(() =>
  ledger.value?.members.find((member) => member.user_id === userStore.user?.id),
);
const isOwner = computed(() => currentMember.value?.role === "owner");
const isAdmin = computed(() => currentMember.value?.role === "admin");

function roleName(role: LedgerRole) {
  return role === "owner" ? "创建者" : role === "admin" ? "管理员" : "成员";
}

function canManage(member: LedgerMember) {
  if (member.user_id === currentMember.value?.user_id) return false;
  if (!isOwner.value && !isAdmin.value) return false;
  return member.role !== "owner";
}

function canChangeRole(member: LedgerMember) {
  return isOwner.value && member.role !== "owner";
}

function canRemove(member: LedgerMember) {
  if (member.role === "owner") return false;
  if (isOwner.value) return true;
  return isAdmin.value && member.role === "member";
}

async function loadById(id: number) {
  loadError.value = "";
  try {
    ledger.value = await getLedger(id);
  } catch (error) {
    loadError.value = error instanceof Error ? error.message : "成员加载失败";
  }
}

onLoad(async (query) => {
  await userStore.ensureUser();
  const id = Number(query?.id);
  if (id) await loadById(id);
});

async function toggleRole(member: LedgerMember) {
  if (!ledger.value || saving.value) return;
  saving.value = true;
  try {
    ledger.value = await updateMemberRole(
      ledger.value.id,
      member.user_id,
      member.role === "admin" ? "member" : "admin",
    );
    uni.showToast({ title: "成员角色已更新", icon: "success" });
  } catch (error) {
    uni.showToast({
      title: error instanceof Error ? error.message : "更新失败",
      icon: "none",
    });
  } finally {
    saving.value = false;
  }
}

function remove(member: LedgerMember) {
  if (!ledger.value || saving.value) return;
  uni.showModal({
    title: "移除成员",
    content: `确定移除 ${member.nickname || `用户${member.user_id}`} 吗？`,
    success: async (result) => {
      if (!result.confirm || !ledger.value) return;
      saving.value = true;
      try {
        ledger.value = await removeLedgerMember(
          ledger.value.id,
          member.user_id,
        );
        uni.showToast({ title: "已移除成员", icon: "success" });
      } catch (error) {
        uni.showToast({
          title: error instanceof Error ? error.message : "移除失败",
          icon: "none",
        });
      } finally {
        saving.value = false;
      }
    },
  });
}

function copyInvite() {
  if (!ledger.value?.invite_code) return;
  uni.setClipboardData({
    data: ledger.value.invite_code,
    success: () => uni.showToast({ title: "邀请码已复制", icon: "none" }),
  });
}
</script>

<style scoped>
.page { min-height: 100vh; padding: 28rpx; box-sizing: border-box; }
.member-list { overflow: hidden; border-radius: var(--radius-lg); background: var(--color-surface); box-shadow: var(--shadow-sm); }
.member { display: flex; align-items: center; gap: 18rpx; min-height: 100rpx; padding: 12rpx 22rpx; border-bottom: 1rpx solid var(--color-border-muted); background: var(--color-surface); }
.member:last-child { border-bottom: 0; }
.avatar { display: flex; align-items: center; justify-content: center; width: 60rpx; height: 60rpx; flex: none; border-radius: 20rpx; color: var(--color-primary); background: var(--color-primary-soft); font-weight: 600; }
.copy { display: flex; flex: 1; min-width: 0; flex-direction: column; font-size: 27rpx; }
.role { margin-top: 4rpx; color: var(--color-text-secondary); font-size: 22rpx; }
.actions { display: flex; flex: none; gap: 8rpx; }
.action { height: var(--button-height-sm); margin: 0; padding: 0 14rpx; border: 0; border-radius: 14rpx; color: var(--color-primary); background: var(--color-primary-soft); font-size: 22rpx; line-height: var(--button-height-sm); }
.action.danger { color: var(--color-danger); background: #fff0ef; }
.invite { display: flex; align-items: center; justify-content: space-between; margin-top: 18rpx; padding: 22rpx; border-radius: var(--radius-lg); background: var(--color-primary-soft); }
.invite-label { display: block; color: var(--color-text-secondary); font-size: 22rpx; }
.invite-code { display: block; margin-top: 4rpx; color: var(--color-primary); font-size: 32rpx; font-weight: 700; letter-spacing: 4rpx; }
.copy { flex: none; height: var(--button-height-sm); margin: 0; padding: 0 18rpx; border: 0; border-radius: 16rpx; color: #fff; background: var(--color-primary); font-size: 22rpx; line-height: var(--button-height-sm); }
.invite-hint { display: block; margin-top: 12rpx; color: var(--color-text-secondary); font-size: 22rpx; line-height: 1.5; }
.load-error { margin-top: 16rpx; padding: 20rpx 22rpx; border-radius: var(--radius-lg); color: var(--color-danger); background: #fff0ef; font-size: 24rpx; }
</style>

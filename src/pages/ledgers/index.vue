<template>
  <view class="page">
    <view class="create-band">
      <input v-model="name" class="name-input" placeholder="新账本名称" maxlength="80" />
      <view class="type-control">
        <button :class="{ active: type === 'personal' }" @click="type = 'personal'">个人</button>
        <button :class="{ active: type === 'shared' }" @click="type = 'shared'">共享</button>
      </view>
      <button class="primary" :disabled="!name.trim()" @click="create">创建账本</button>
    </view>

    <view class="join-band">
      <input v-model.number="joinId" type="number" placeholder="账本编号" />
      <input v-model="inviteCode" placeholder="邀请码" maxlength="32" />
      <button @click="join">加入共享账本</button>
    </view>

    <view class="ledger-list">
      <view v-for="ledger in store.ledgers" :key="ledger.id" class="ledger-item">
        <view class="ledger-main" hover-class="pressable" @click="store.switchLedger(ledger.id)">
          <view>
            <text class="ledger-name">{{ ledger.name }}</text>
            <text class="ledger-meta">{{ ledger.type === "shared" ? `${ledger.member_count} 名成员` : "个人账本" }}</text>
          </view>
          <text v-if="store.currentId === ledger.id" class="current">当前</text>
        </view>
        <view v-if="ledger.type === 'shared'" class="ledger-actions">
          <button @click="openMembers(ledger.id)">成员</button>
          <button @click="openSettle(ledger.id)">结算</button>
          <button v-if="canManage(ledger)" @click="rotate(ledger.id)">轮换邀请码</button>
          <text v-if="ledger.invite_code">邀请码 {{ ledger.invite_code }}</text>
        </view>
      </view>
    </view>
</view>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { onShow } from "@dcloudio/uni-app";
import { useLedgerStore } from "@/stores/ledger";
import { useUserStore } from "@/stores/user";
import { rotateInviteCode } from "@/api/ledgers";
import type { LedgerType } from "@/types";

const store = useLedgerStore();
const userStore = useUserStore();
const name = ref("");
const type = ref<LedgerType>("personal");
const joinId = ref<number | null>(null);
const inviteCode = ref("");

onShow(async () => {
  await userStore.ensureUser();
  await store.fetchLedgers();
});

async function create() {
  try {
    await store.create(name.value.trim(), type.value);
    name.value = "";
    uni.showToast({ title: "创建成功", icon: "success" });
  } catch (error) {
    uni.showToast({ title: error instanceof Error ? error.message : "创建失败", icon: "none" });
  }
}

async function join() {
  if (!joinId.value || !inviteCode.value.trim()) return;
  try {
    await store.join(joinId.value, inviteCode.value.trim());
    inviteCode.value = "";
    uni.showToast({ title: "已加入账本", icon: "success" });
  } catch (error) {
    uni.showToast({ title: error instanceof Error ? error.message : "加入失败", icon: "none" });
  }
}

function canManage(ledger: typeof store.ledgers[number]) {
  const userId = userStore.user?.id;
  return Boolean(userId && ledger.members.some((member) => member.user_id === userId && ["owner", "admin"].includes(member.role)));
}

async function rotate(ledgerId: number) {
  try {
    await rotateInviteCode(ledgerId);
    await store.fetchLedgers();
    uni.showToast({ title: "邀请码已轮换", icon: "success" });
  } catch (error) {
    uni.showToast({ title: error instanceof Error ? error.message : "邀请码轮换失败", icon: "none" });
  }
}

function openMembers(id: number) { uni.navigateTo({ url: `/pages/ledgers/members?id=${id}` }); }
function openSettle(id: number) { uni.navigateTo({ url: `/pages/ledgers/settle?id=${id}` }); }
</script>

<style scoped>
.page { min-height: 100vh; padding: 28rpx; box-sizing: border-box; }
.create-band, .join-band { display: grid; gap: 14rpx; padding: 24rpx; border-radius: var(--radius-lg); background: var(--color-surface); box-shadow: var(--shadow-sm); }
.join-band { margin-top: 16rpx; }
.name-input, .join-band input { height: 78rpx; padding: 0 20rpx; border-radius: 18rpx; background: var(--color-surface-muted); font-size: 26rpx; }
.type-control { display: grid; grid-template-columns: 1fr 1fr; gap: 8rpx; }
.type-control { padding: 6rpx; border-radius: 22rpx; background: var(--color-surface-muted); }
.type-control button, .join-band button, .ledger-actions button { height: var(--button-height-md); margin: 0; border: 0; border-radius: 20rpx; background: transparent; font-size: var(--button-font-md); font-weight: 600; line-height: var(--button-height-md); }
.type-control button.active { color: var(--color-primary); background: var(--color-primary-soft); }
.primary, .join-band button { width: 100%; height: var(--button-height-lg); border: 0; border-radius: var(--radius-pill); color: #fff; background: var(--color-primary); box-shadow: 0 16rpx 32rpx rgba(74, 144, 226, .18); font-size: var(--button-font-lg); font-weight: 600; line-height: var(--button-height-lg); }
.ledger-list { margin-top: 22rpx; }
.ledger-item { margin-bottom: 14rpx; overflow: hidden; border-radius: var(--radius-lg); background: var(--color-surface); box-shadow: var(--shadow-sm); }
.ledger-main { display: flex; align-items: center; justify-content: space-between; padding: 22rpx; }
.ledger-main > view { display: flex; flex-direction: column; }
.ledger-name { font-size: 30rpx; font-weight: 600; }
.ledger-meta { margin-top: 6rpx; color: var(--color-text-secondary); font-size: 22rpx; }
.current { padding: 6rpx 12rpx; border-radius: var(--radius-pill); color: var(--color-success); background: #eaf8ee; font-size: 21rpx; }
.ledger-actions { display: flex; align-items: center; gap: 12rpx; padding: 14rpx 22rpx; border-top: 1rpx solid var(--color-border-muted); }
.ledger-actions button { width: 112rpx; height: var(--button-height-sm); border-radius: 16rpx; color: var(--color-primary); background: var(--color-primary-soft); font-size: var(--button-font-sm); line-height: var(--button-height-sm); }
.ledger-actions text { margin-left: auto; color: var(--color-text-secondary); font-size: 22rpx; }
</style>

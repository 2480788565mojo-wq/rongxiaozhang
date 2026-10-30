<template>
  <view class="page">
    <!-- AI 功能关闭态（审核期）：手动记账引导，页面不出现任何 AI 相关字样 -->
    <view v-if="!appStore.aiEnabled" class="manual-guide">
      <image class="guide-logo" src="/static/logo.jpg" mode="aspectFill" />
      <text class="guide-title">记一笔</text>
      <text class="guide-subtitle">填写金额、分类和账户，也可语音输入备注</text>
      <button class="primary-button" @click="goManualAdd">开始记账</button>
    </view>

    <!-- AI 功能开启态：智能记账界面 -->
    <template v-else>
    <view class="brand-row">
      <image class="brand-logo" src="/static/logo.jpg" mode="aspectFill" />
      <view class="brand-copy">
        <text class="brand-name">AI 智能记账</text>
        <view class="brand-status">
          <view class="status-dot" />
          <text>{{ userStore.isLoggedIn ? currentLedgerName : "登录后开始记账" }}</text>
        </view>
      </view>
      <picker
        v-if="ledgerStore.ledgers.length"
        :range="ledgerNames"
        :value="ledgerIndex"
        @change="onLedgerChange"
      >
        <view class="ledger-picker">
          <u-icon name="bookmark" color="#4A90E2" size="15" />
          <text>切换账本</text>
        </view>
      </picker>
    </view>

    <view v-if="!userStore.isLoggedIn" class="login-panel card">
      <view class="login-icon"><u-icon name="chat" color="#4A90E2" size="28" /></view>
      <text class="login-title">登录后开始智能记账</text>
      <text class="login-subtitle">用一句话记录收入和支出</text>
      <button class="primary-button" :loading="userStore.loading" @click="login">微信一键登录</button>
    </view>

    <template v-else>
      <view class="conversation">
        <view class="message-row assistant">
          <image class="message-avatar" src="/static/logo.jpg" mode="aspectFill" />
          <view class="message-bubble assistant-bubble">
            <text>告诉我这笔收支，我会帮你整理金额、分类、账户和日期。</text>
          </view>
        </view>

        <view v-if="sourceText && (parsing || clarificationQuestion || parsedItems.length || advisorMessage)" class="message-row user">
          <view class="message-bubble user-bubble"><text>{{ sourceText }}</text></view>
        </view>

        <view v-if="parsing" class="message-row assistant">
          <image class="message-avatar" src="/static/logo.jpg" mode="aspectFill" />
          <view class="message-bubble assistant-bubble typing-bubble" aria-label="AI 正在分析">
            <view class="typing-dots"><text /><text /><text /></view>
          </view>
        </view>

        <view v-if="clarificationQuestion && !parsing" class="message-row assistant">
          <image class="message-avatar" src="/static/logo.jpg" mode="aspectFill" />
          <view class="message-bubble assistant-bubble clarify-bubble">
            <text class="bubble-label">还需要一点信息</text>
            <text>{{ clarificationQuestion }}</text>
          </view>
        </view>

        <view v-if="advisorMessage && !parsing" class="message-row assistant">
          <image class="message-avatar" src="/static/logo.jpg" mode="aspectFill" />
          <view class="message-bubble assistant-bubble clarify-bubble">
            <text class="bubble-label">AI 理财顾问</text>
            <text>{{ advisorMessage.summary }}</text>
            <text v-for="action in advisorMessage.actions" :key="action">• {{ action }}</text>
          </view>
        </view>

        <view v-if="parsed && !isMulti" class="message-row assistant result-row">
          <image class="message-avatar" src="/static/logo.jpg" mode="aspectFill" />
          <view class="result-section card">
            <view class="section-heading">
              <view>
                <text class="section-title">请确认账单</text>
                <text class="section-subtitle">AI 已整理，可直接修改</text>
              </view>
              <view class="ready-tag"><u-icon name="checkmark" color="#34C759" size="14" /><text>已解析</text></view>
            </view>

            <view class="type-segment">
              <button class="segment-button expense-option" :class="{ active: parsed.type === 'expense' }" @click="parsed.type = 'expense'">支出</button>
              <button class="segment-button income-option" :class="{ active: parsed.type === 'income' }" @click="parsed.type = 'income'">收入</button>
            </view>

            <label class="field-row amount-row">
              <text class="field-label">金额</text>
              <view class="amount-input-wrap">
                <text class="currency">¥</text>
                <input v-model.number="parsed.amount" class="amount-input numeric" type="digit" />
              </view>
            </label>
            <label class="field-row"><text class="field-label">分类</text><input v-model="parsed.category" class="field-input" placeholder="请选择分类" /></label>
            <label class="field-row"><text class="field-label">细分</text><input v-model="parsed.subcategory" class="field-input" placeholder="选填" /></label>
            <label class="field-row"><text class="field-label">账户</text><input v-model="parsed.account" class="field-input" placeholder="选填" /></label>
            <label class="field-row"><text class="field-label">日期</text><input v-model="parsed.bill_date" class="field-input numeric" placeholder="YYYY-MM-DD" /></label>
            <label class="field-row"><text class="field-label">备注</text><input v-model="parsed.note" class="field-input" placeholder="选填" /></label>

            <view v-if="isSharedExpense" class="share-section">
              <view class="share-heading">
                <view>
                  <text class="share-title">AA 分摊</text>
                  <text class="share-subtitle">{{ aaAvailable ? '选择本次参与成员' : '至少需要两名成员才能 AA' }}</text>
                </view>
                <switch :checked="aaEnabled" :disabled="!aaAvailable" color="#4A90E2" @change="toggleAA" />
              </view>
              <checkbox-group v-if="aaEnabled" class="member-list" @change="onMembersChange">
                <label v-for="member in currentMembers" :key="member.user_id" class="member-row">
                  <checkbox :value="String(member.user_id)" :checked="selectedShareIds.includes(member.user_id)" color="#4A90E2" />
                  <text>{{ member.nickname || `用户${member.user_id}` }}</text>
                  <text class="member-role">{{ member.role === 'owner' ? '创建者' : '成员' }}</text>
                </label>
              </checkbox-group>
            </view>

            <button class="confirm-button" :disabled="!canConfirm || saving" :loading="saving" @click="saveBills(false)">确认记账</button>
          </view>
        </view>

        <view v-else-if="isMulti" class="message-row assistant result-row">
          <image class="message-avatar" src="/static/logo.jpg" mode="aspectFill" />
          <view class="result-section card batch-card">
            <view class="section-heading">
              <view>
                <text class="section-title">识别到 {{ parsedItems.length }} 笔</text>
                <text class="section-subtitle">请核对后一次确认，逐笔入账</text>
              </view>
              <view class="ready-tag"><u-icon name="checkmark" color="#34C759" size="14" /><text>已解析</text></view>
            </view>

            <view v-for="(item, index) in parsedItems" :key="index" class="batch-item">
              <view class="batch-item-head">
                <text class="batch-index">第 {{ index + 1 }} 笔</text>
                <text class="batch-amount numeric">¥{{ Number(item.amount || 0).toFixed(2) }}</text>
              </view>
              <view class="type-segment batch-type">
                <button class="segment-button expense-option" :class="{ active: item.type === 'expense' }" @click="item.type = 'expense'">支出</button>
                <button class="segment-button income-option" :class="{ active: item.type === 'income' }" @click="item.type = 'income'">收入</button>
              </view>
              <label class="field-row amount-row">
                <text class="field-label">金额</text>
                <view class="amount-input-wrap">
                  <text class="currency">¥</text>
                  <input v-model.number="item.amount" class="amount-input numeric" type="digit" />
                </view>
              </label>
              <label class="field-row"><text class="field-label">分类</text><input v-model="item.category" class="field-input" placeholder="请填写分类" /></label>
              <label class="field-row"><text class="field-label">细分</text><input v-model="item.subcategory" class="field-input" placeholder="选填" /></label>
              <label class="field-row"><text class="field-label">账户</text><input v-model="item.account" class="field-input" placeholder="选填" /></label>
              <label class="field-row"><text class="field-label">日期</text><input v-model="item.bill_date" class="field-input numeric" placeholder="YYYY-MM-DD" /></label>
              <label class="field-row"><text class="field-label">备注</text><input v-model="item.note" class="field-input" placeholder="选填" /></label>
            </view>

            <view v-if="isSharedLedger" class="batch-note">多笔账单暂不支持 AA 分摊；确认后可到账单详情逐笔处理。</view>
            <button class="confirm-button" :disabled="!canConfirm || saving" :loading="saving" @click="saveBills(false)">确认全部 {{ parsedItems.length }} 笔</button>
          </view>
        </view>
      </view>

      <view v-if="!parsing" class="composer-shell">
        <view v-if="voiceStatus" class="voice-status" :class="{ active: voiceRecording }">
          <view v-if="voiceRecording" class="recording-dot" />
          <text>{{ voiceStatus }}</text>
          <text class="input-count">{{ rawInput.length }}/500</text>
        </view>
        <view class="composer">
          <button
            class="voice-button"
            :class="{ recording: voiceRecording }"
            :disabled="saving"
            :aria-label="voiceButtonLabel"
            :title="voiceButtonLabel"
            @click="handleVoiceButton"
          >
            <u-icon :name="voiceRecording ? 'close' : 'mic'" color="currentColor" size="22" />
          </button>
          <textarea v-model="rawInput" :focus="rawInputFocused" @blur="rawInputFocused = false" class="speech-input" :placeholder="clarificationQuestion || '输入一笔收支…'" :maxlength="500" auto-height />
          <button class="analyze-button" :class="{ 'is-idle': !rawInput.trim() }" aria-label="发送并解析" title="发送并解析" @click="analyze">
            <u-icon name="arrow-upward" color="#FFFFFF" size="21" />
          </button>
        </view>
          </view>
    </template>
    </template>
    <BudgetAlert />
  </view>
</template>

<script setup lang="ts">
import { computed, onUnmounted, ref } from "vue";
import { onShow } from "@dcloudio/uni-app";
import { ApiError, getStoredToken } from "@/api/client";
import { confirmBill, transcribeStreamUrl } from "@/api/bills";
import BudgetAlert from "@/components/BudgetAlert.vue";
import { useBillStore } from "@/stores/bill";
import { useBudgetStore } from "@/stores/budget";
import { useLedgerStore } from "@/stores/ledger";
import { useUserStore } from "@/stores/user";
import { useAppStore } from "@/stores/app";
import type { ParsedBill, SSEEvent } from "@/types";
import { buildBatchConfirmKey } from "@/utils/bill-batch";
import { createSSEConnection, type SSEConnection } from "@/utils/sse";
import { useVoiceInput } from "@/composables/useVoiceInput";
import { keyboardVoiceHint } from "@/utils/speech";

const userStore = useUserStore();
const budgetStore = useBudgetStore();
const ledgerStore = useLedgerStore();
const billStore = useBillStore();
const appStore = useAppStore();
const rawInput = ref("");
const sourceText = ref("");
const sessionId = ref("");
const clarificationQuestion = ref("");
const parsed = ref<ParsedBill | null>(null);
const parsedItems = ref<ParsedBill[]>([]);
const advisorMessage = ref<{ summary: string; actions: string[] } | null>(null);
const parsing = ref(false);
const saving = ref(false);
const aaEnabled = ref(false);
const selectedShareIds = ref<number[]>([]);
const voice = useVoiceInput(rawInput);
const voiceRecording = voice.busy;
const voiceStatus = voice.status;
const rawInputFocused = ref(false);
let stream: SSEConnection | null = null;

const voiceButtonLabel = computed(() => {
  // #ifdef MP-WEIXIN
  return "使用键盘语音输入";
  // #endif
  return voiceRecording.value ? "停止语音输入" : "开始语音输入";
});

const ledgerNames = computed(() => ledgerStore.ledgers.map((item) => item.name));
const ledgerIndex = computed(() => Math.max(0, ledgerStore.ledgers.findIndex((item) => item.id === ledgerStore.currentId)));
const currentLedgerName = computed(() => ledgerStore.current?.name || "请选择账本");
const currentMembers = computed(() => ledgerStore.current?.members || []);
const isSharedLedger = computed(() => ledgerStore.current?.type === "shared");
const isMulti = computed(() => parsedItems.value.length > 1);
const aaAvailable = computed(() => currentMembers.value.length >= 2);
const isSharedExpense = computed(() => !isMulti.value && isSharedLedger.value && parsed.value?.type === "expense");
const canConfirm = computed(() => {
  const items = parsedItems.value;
  if (!items.length) return false;
  if (clarificationQuestion.value) return false;
  const complete = items.every((item) => Boolean(item.type && item.amount && item.category && item.bill_date));
  if (!complete) return false;
  return isMulti.value ? true : (!aaEnabled.value || selectedShareIds.value.length >= 2);
});

async function login() {
  try {
    await userStore.login();
    await ledgerStore.fetchLedgers();
  } catch (error) {
    uni.showToast({ title: error instanceof Error ? error.message : "登录失败", icon: "none" });
  }
}

async function ensureLedgers() {
  if (userStore.isLoggedIn && !ledgerStore.ledgers.length) await ledgerStore.fetchLedgers();
}

/** AI 关闭态：跳转到手动记账表单页 */
function goManualAdd() {
  uni.navigateTo({ url: "/pages/add/index" });
}

function stopVoiceInput(showStatus = true) { if (showStatus) voice.stop(); else voice.cancel(); }
function toggleVoiceInput() { voice.toggle(); }
function handleVoiceButton() {
  // #ifdef MP-WEIXIN
  rawInputFocused.value = true;
  uni.showToast({ title: keyboardVoiceHint(), icon: 'none', duration: 3000 });
  // #endif
  // #ifndef MP-WEIXIN
  toggleVoiceInput();
  // #endif
}

function onLedgerChange(event: any) {
  const ledger = ledgerStore.ledgers[Number(event.detail.value)];
  if (ledger) ledgerStore.switchLedger(ledger.id);
  aaEnabled.value = false;
  selectedShareIds.value = [];
}

function normalizeParsed(data: Partial<ParsedBill>): ParsedBill | null {
  if (!data.type || !data.amount || !data.category) return null;
  return {
    type: data.type,
    amount: Number(data.amount),
    category: data.category,
    subcategory: data.subcategory || null,
    account: data.account || null,
    note: data.note || null,
    bill_date: data.bill_date || new Date().toISOString().slice(0, 10),
  };
}

function normalizeItems(rawItems: unknown): ParsedBill[] {
  if (!Array.isArray(rawItems)) return [];
  return rawItems
    .map((item) => normalizeParsed((item || {}) as Partial<ParsedBill>))
    .filter((item): item is ParsedBill => Boolean(item));
}

function commitParsedItems(items: ParsedBill[]) {
  if (!items.length) return;
  parsedItems.value = items;
  parsed.value = items[0];
}

function applyParsedItems(rawItems: unknown) {
  const normalized = normalizeItems(rawItems);
  if (!normalized.length) return;
  commitParsedItems(normalized);
}

function askDraftMode(newItems: ParsedBill[], incomingSession: string) {
  const previousCount = parsedItems.value.length;
  uni.showModal({
    title: "这些账怎么处理？",
    content: `当前还有 ${previousCount} 笔未确认，新解析了 ${newItems.length} 笔。追加会加到末尾；新批次会替换当前草稿。`,
    confirmText: "追加",
    cancelText: "新批次",
    success: (result) => {
      if (result.confirm) {
        // 追加保留旧 session，已保存的旧条目仍能被幂等键识别。
        commitParsedItems([...parsedItems.value, ...newItems]);
        return;
      }
      // 新批次必须换 epoch，避免复用旧批次已保存的 session:index。
      sessionId.value = `${incomingSession || sessionId.value}-r${Date.now()}`;
      commitParsedItems(newItems);
    },
    fail: () => {
      // 不把 session 指向未确认的新解析，避免旧草稿用错键。
      uni.showToast({ title: "未选择，已保留原草稿", icon: "none" });
    },
  });
}

function handleStreamEvent(message: SSEEvent) {
  const data = message.data as any;
  if (message.event === "parsed") {
    const incomingSession = data.session_id || sessionId.value;
    const rawItems = Array.isArray(data.items) && data.items.length
      ? data.items
      : (data.parsed ? [data.parsed] : []);
    const normalized = normalizeItems(rawItems);
    // 追问补全不是新的一批，不能弹“追加/新批次”。
    if (
      !clarificationQuestion.value
      && parsedItems.value.length > 0
      && normalized.length > 0
    ) {
      askDraftMode(normalized, incomingSession);
    } else {
      sessionId.value = incomingSession;
      applyParsedItems(rawItems);
    }
  }
  if (message.event === "clarify") {
    clarificationQuestion.value = data.question;
    sessionId.value = data.session_id;
    rawInput.value = "";
    // 保留已经解析好的条目，只让用户补当前缺失的那一笔。
    parsing.value = false;
    stream?.close();
  }
  if (message.event === "awaiting_confirmation") {
    clarificationQuestion.value = "";
    if (Array.isArray(data.items) && data.items.length && !parsedItems.value.length) {
      applyParsedItems(data.items);
    }
    if (data.advice?.summary) {
      advisorMessage.value = {
        summary: data.advice.summary,
        actions: Array.isArray(data.advice.actions) ? data.advice.actions.slice(0, 3) : [],
      };
    }
    parsing.value = false;
    stream?.close();
  }
  if (message.event === "advice") {
    advisorMessage.value = {
      summary: data.summary || "暂时无法生成分析建议",
      actions: Array.isArray(data.actions) ? data.actions.slice(0, 3) : [],
    };
    parsing.value = false;
    stream?.close();
  }
  if (message.event === "error") {
    parsing.value = false;
    stream?.close();
    uni.showToast({ title: data.message || "解析失败", icon: "none" });
  }
}

function analyze() {
  if (voiceRecording.value) stopVoiceInput(false);
  const text = rawInput.value.trim();
  if (!text || !ledgerStore.currentId) return;
  parsing.value = true;
  advisorMessage.value = null;
  sourceText.value = sourceText.value ? `${sourceText.value}；补充：${text}` : text;
  stream?.close();
  stream = createSSEConnection(transcribeStreamUrl(), {
    method: "POST",
    token: getStoredToken(),
    data: { text, ledger_id: ledgerStore.currentId, session_id: sessionId.value || undefined },
    onEvent: handleStreamEvent,
    onError: (error) => {
      parsing.value = false;
      uni.showToast({
        title: error instanceof Error ? error.message : "AI 服务连接失败",
        icon: "none",
      });
    },
  });
}

function toggleAA(event: any) {
  const enabled = Boolean(event.detail.value);
  if (enabled && !aaAvailable.value) {
    aaEnabled.value = false;
    uni.showToast({ title: "至少需要两名成员才能 AA", icon: "none" });
    return;
  }
  aaEnabled.value = enabled;
  selectedShareIds.value = enabled
    ? currentMembers.value.map((member) => member.user_id)
    : [];
}

function onMembersChange(event: any) {
  selectedShareIds.value = (event.detail.value as string[]).map(Number);
}

function confirmParsedItem(item: ParsedBill, index: number, force: boolean) {
  const key = buildBatchConfirmKey(
    sessionId.value,
    index,
    parsedItems.value.length,
  );
  return confirmBill({
    ledger_id: ledgerStore.currentId,
    session_id: key.session_id,
    raw_input: sourceText.value.slice(0, 500),
    parsed: item,
    share_user_ids: !isMulti.value && aaEnabled.value ? selectedShareIds.value : [],
    is_batch_item: key.is_batch_item,
    force,
  });
}

async function saveBills(force = false) {
  if (!parsedItems.value.length || !canConfirm.value) return;
  const items = [...parsedItems.value];
  saving.value = true;
  let saved = 0;
  try {
    for (let index = 0; index < items.length; index += 1) {
      const item = items[index];
      try {
        const bill = await confirmParsedItem(item, index, force);
        billStore.prepend(bill);
        saved += 1;
      } catch (error) {
        if (!(error instanceof ApiError) || error.statusCode !== 409 || force) throw error;
        const data = error.data as any;
        const check = data?.budget_check || {};
        const riskLevel = data?.status === "blocked" ? "blocked" : "warning";
        const confirmed = await new Promise<boolean>((resolve) => {
          budgetStore.showAlert(
            {
              ...check,
              risk_level: check.risk_level || riskLevel,
              message: data?.message,
            },
            resolve,
          );
        });
        if (!confirmed) {
          uni.showToast({ title: `已记 ${saved} 笔，剩余未记`, icon: "none" });
          return;
        }
        const bill = await confirmParsedItem(item, index, true);
        billStore.prepend(bill);
        saved += 1;
      }
    }
    uni.showToast({ title: items.length > 1 ? `已记 ${items.length} 笔` : "记账成功", icon: "success" });
    resetForm();
  } catch (error) {
    uni.showToast({ title: error instanceof Error ? error.message : "保存失败", icon: "none" });
  } finally {
    saving.value = false;
  }
}

function resetForm() {
  stopVoiceInput(false);
  rawInput.value = "";
  sourceText.value = "";
  sessionId.value = "";
  clarificationQuestion.value = "";
  parsed.value = null;
  parsedItems.value = [];
  advisorMessage.value = null;
  aaEnabled.value = false;
  selectedShareIds.value = [];
}

onShow(() => {
  // 导航标题随开关动态切换：关闭态用中性标题，开启态显示完整名称
  uni.setNavigationBarTitle({ title: appStore.aiEnabled ? "AI 智能记账" : "记账" });
  if (appStore.aiEnabled) void ensureLedgers();
});
onUnmounted(() => {
  stream?.close();
  stopVoiceInput(false);
});
</script>

<style scoped>
.page { min-height: 100vh; padding: 24rpx 28rpx 340rpx; box-sizing: border-box; }
.manual-guide { display: flex; margin-top: 160rpx; padding: 56rpx 36rpx; flex-direction: column; align-items: center; text-align: center; }
.guide-logo { width: 116rpx; height: 116rpx; border-radius: 28rpx; }
.guide-title { margin-top: 28rpx; color: var(--color-text); font-size: 38rpx; font-weight: 700; }
.guide-subtitle { margin-top: 14rpx; color: var(--color-text-secondary); font-size: 26rpx; line-height: 1.6; }
.manual-guide .primary-button { width: 340rpx; margin-top: 44rpx; }
.card { border-radius: var(--radius-lg); background: var(--color-surface); box-shadow: var(--shadow-sm); }
.brand-row { display: flex; align-items: center; gap: 14rpx; }
.brand-logo { width: 68rpx; height: 68rpx; flex: none; border-radius: 18rpx; }
.brand-copy { display: flex; min-width: 0; flex: 1; flex-direction: column; }
.brand-name { color: var(--color-text); font-size: 32rpx; font-weight: 600; }
.brand-status { display: flex; align-items: center; gap: 8rpx; margin-top: 5rpx; color: var(--color-text-secondary); font-size: 22rpx; }
.brand-status text { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.status-dot { width: 10rpx; height: 10rpx; flex: none; border-radius: 50%; background: var(--color-success); }
.ledger-picker { display: flex; align-items: center; gap: 8rpx; padding: 10rpx 14rpx; border-radius: var(--radius-pill); color: var(--color-primary); background: var(--color-primary-soft); font-size: 22rpx; }
.login-panel { display: flex; margin-top: 28rpx; padding: 44rpx 32rpx; flex-direction: column; align-items: center; text-align: center; }
.login-icon { display: flex; align-items: center; justify-content: center; width: 84rpx; height: 84rpx; border-radius: 26rpx; background: var(--color-primary-soft); }
.login-title { margin-top: 22rpx; font-size: 34rpx; font-weight: 600; }
.login-subtitle { margin-top: 10rpx; color: var(--color-text-secondary); font-size: 24rpx; }
.primary-button, .confirm-button { width: 100%; height: var(--button-height-lg); border: 0; border-radius: var(--radius-pill); color: #fff; background: var(--color-primary); box-shadow: 0 16rpx 32rpx rgba(74, 144, 226, .18); font-size: var(--button-font-lg); font-weight: 600; line-height: var(--button-height-lg); }
.primary-button { width: 320rpx; margin-top: 28rpx; }
.conversation { margin-top: 28rpx; }
.message-row { display: flex; align-items: flex-start; margin-bottom: 20rpx; animation: message-enter var(--transition-standard) both; }
.message-row.user { justify-content: flex-end; }
.message-avatar { width: 60rpx; height: 60rpx; flex: none; margin-right: 12rpx; border-radius: 18rpx; }
.message-bubble { max-width: 540rpx; padding: 18rpx 22rpx; box-sizing: border-box; font-size: 28rpx; line-height: 1.55; }
.assistant-bubble { border: 1rpx solid #eef3fa; border-radius: 8rpx 26rpx 26rpx 26rpx; color: var(--color-text); background: var(--color-surface); box-shadow: var(--shadow-sm); }
.user-bubble { border-radius: 26rpx 8rpx 26rpx 26rpx; color: #fff; background: var(--color-primary); box-shadow: 0 10rpx 22rpx rgba(74, 144, 226, .20); }
.bubble-label { display: block; margin-bottom: 8rpx; color: var(--color-warning); font-size: 23rpx; font-weight: 600; }
.typing-bubble { min-width: 112rpx; }
.typing-dots { display: flex; align-items: center; justify-content: center; gap: 9rpx; height: 28rpx; }
.typing-dots text { width: 11rpx; height: 11rpx; border-radius: 50%; background: #b8b8bd; animation: typing-dot 280ms ease alternate infinite; }
.typing-dots text:nth-child(2) { animation-delay: 80ms; }
.typing-dots text:nth-child(3) { animation-delay: 160ms; }
.result-row { align-items: flex-start; }
.result-section { width: calc(100% - 72rpx); min-width: 0; padding: 28rpx; box-sizing: border-box; border: 1rpx solid #eef3fa; box-shadow: var(--shadow-card); }
.batch-card { padding-bottom: 26rpx; }
.batch-item { margin-top: 18rpx; padding-top: 18rpx; border-top: 1rpx solid var(--color-border-muted); }
.batch-item:first-of-type { margin-top: 8rpx; padding-top: 0; border-top: 0; }
.batch-item-head { display: flex; align-items: center; justify-content: space-between; gap: 12rpx; }
.batch-index { color: var(--color-text-secondary); font-size: 23rpx; font-weight: 600; }
.batch-amount { font-size: 30rpx; font-weight: 700; }
.batch-type { width: 100%; margin: 14rpx 0 4rpx; }
.batch-note { margin-top: 18rpx; padding: 16rpx 18rpx; border-radius: 16rpx; background: var(--color-surface-muted); color: var(--color-text-secondary); font-size: 22rpx; line-height: 1.6; }
.batch-card .field-row:last-child { border-bottom: 0; }
.section-heading, .share-heading { display: flex; align-items: center; justify-content: space-between; }
.section-heading > view:first-child, .share-heading > view:first-child { display: flex; min-width: 0; flex-direction: column; }
.section-title { font-size: 32rpx; font-weight: 600; }
.section-subtitle, .share-subtitle { margin-top: 6rpx; color: var(--color-text-secondary); font-size: 22rpx; }
.ready-tag { display: flex; align-items: center; gap: 5rpx; padding: 8rpx 13rpx; border-radius: var(--radius-pill); color: var(--color-success); background: #eaf8ee; font-size: 21rpx; }
.type-segment { display: grid; grid-template-columns: 1fr 1fr; gap: 8rpx; margin: 24rpx 0 8rpx; padding: 6rpx; border-radius: 22rpx; background: var(--color-surface-muted); }
.segment-button { height: var(--button-height-md); margin: 0; border: 0; border-radius: 20rpx; color: var(--color-text-secondary); background: transparent; font-size: var(--button-font-md); font-weight: 600; line-height: var(--button-height-md); }
.expense-option.active { color: var(--color-danger); background: #fff0ef; }
.income-option.active { color: #248c41; background: #eaf8ee; }
.field-row { display: flex; align-items: center; min-height: 92rpx; border-bottom: 1rpx solid var(--color-border-muted); }
.field-label { width: 108rpx; flex: none; color: var(--color-text-secondary); font-size: 25rpx; }
.field-input { min-width: 0; flex: 1; color: var(--color-text); font-size: 26rpx; text-align: right; }
.amount-input-wrap { display: flex; min-width: 0; flex: 1; align-items: center; justify-content: flex-end; }
.currency { color: var(--color-text); font-size: 32rpx; font-weight: 700; }
.amount-input { width: 230rpx; color: var(--color-text); font-size: 42rpx; font-weight: 700; text-align: right; }
.share-section { margin-top: 24rpx; padding-top: 22rpx; border-top: 1rpx solid var(--color-border); }
.share-title { font-weight: 600; }
.member-list { display: flex; margin-top: 14rpx; flex-direction: column; }
.member-row { display: flex; align-items: center; gap: 14rpx; min-height: 76rpx; }
.member-role { margin-left: auto; color: var(--color-text-secondary); font-size: 22rpx; }
.confirm-button { margin-top: 24rpx; }
.composer-shell { position: fixed; right: 24rpx; bottom: calc(110rpx + constant(safe-area-inset-bottom)); bottom: calc(110rpx + env(safe-area-inset-bottom)); left: 24rpx; z-index: 80; padding: 12rpx; border: 1rpx solid var(--color-border-muted); border-radius: 28rpx; background: var(--color-surface); box-shadow: var(--shadow-card); }
.composer { display: flex; align-items: flex-end; gap: 12rpx; }
.voice-button, .analyze-button { display: flex; width: var(--button-height-md); height: var(--button-height-md); flex: none; margin: 0; padding: 0; align-items: center; justify-content: center; border-radius: 50%; line-height: var(--button-height-md); }
.voice-button { color: var(--color-primary); background: var(--color-primary-soft); }
.voice-button.recording { color: #fff; background: var(--color-danger); }
.analyze-button { color: #fff; background: var(--color-primary); }
/* 未输入文字时按钮保持可见，仅降低透明度示意待激活 */
.analyze-button.is-idle { opacity: 0.5; }
.speech-input { min-width: 0; min-height: var(--button-height-md); max-height: 170rpx; flex: 1; padding: 18rpx 8rpx; box-sizing: border-box; color: var(--color-text); font-size: 28rpx; line-height: 40rpx; }
.voice-status { display: flex; align-items: center; gap: 10rpx; min-height: 38rpx; padding: 0 10rpx 8rpx; color: var(--color-text-secondary); font-size: 21rpx; }
.voice-status.active { color: var(--color-danger); }
.recording-dot { width: 12rpx; height: 12rpx; flex: none; border-radius: 50%; background: var(--color-danger); }
.input-count { margin-left: auto; color: var(--color-text-secondary); font-family: var(--font-mono); font-size: 20rpx; }
button[disabled] { opacity: .42; }
@keyframes message-enter { from { opacity: 0; transform: translateY(10rpx); } to { opacity: 1; transform: translateY(0); } }
@keyframes typing-dot { from { opacity: .35; transform: translateY(2rpx); } to { opacity: 1; transform: translateY(-2rpx); } }
</style>

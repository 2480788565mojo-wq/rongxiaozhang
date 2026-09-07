<template>
  <view class="page">
    <!-- AI 功能关闭态（审核期）：手动记账引导，页面不出现任何 AI 相关字样 -->
    <view v-if="!appStore.aiEnabled" class="manual-guide">
      <image class="guide-logo" src="/static/logo.jpg" mode="aspectFill" />
      <text class="guide-title">记一笔</text>
      <text class="guide-subtitle">手动填写金额、分类和账户，快速记录每笔收支</text>
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

        <view v-if="sourceText && (parsing || clarificationQuestion || parsed || advisorMessage)" class="message-row user">
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

        <view v-if="parsed" class="message-row assistant result-row">
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
                <view><text class="share-title">AA 分摊</text><text class="share-subtitle">选择本次参与成员</text></view>
                <switch :checked="aaEnabled" color="#4A90E2" @change="toggleAA" />
              </view>
              <checkbox-group v-if="aaEnabled" class="member-list" @change="onMembersChange">
                <label v-for="member in currentMembers" :key="member.user_id" class="member-row">
                  <checkbox :value="String(member.user_id)" :checked="selectedShareIds.includes(member.user_id)" color="#4A90E2" />
                  <text>{{ member.nickname || `用户${member.user_id}` }}</text>
                  <text class="member-role">{{ member.role === 'owner' ? '创建者' : '成员' }}</text>
                </label>
              </checkbox-group>
            </view>

            <button class="confirm-button" :disabled="!canConfirm || saving" :loading="saving" @click="saveBill(false)">确认记账</button>
          </view>
        </view>
      </view>

      <view v-if="!parsing && !parsed" class="composer-shell">
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
            @click="toggleVoiceInput"
          >
            <u-icon :name="voiceRecording ? 'close' : 'mic'" color="currentColor" size="22" />
          </button>
          <textarea v-model="rawInput" class="speech-input" :placeholder="clarificationQuestion || '输入一笔收支…'" :maxlength="500" auto-height />
          <button class="analyze-button" :class="{ 'is-idle': !rawInput.trim() }" aria-label="发送并解析" title="发送并解析" @click="analyze">
            <u-icon name="arrow-upward" color="#FFFFFF" size="21" />
          </button>
        </view>
      </view>
    </template>
    </template>
  </view>
</template>

<script setup lang="ts">
import { computed, onUnmounted, ref } from "vue";
import { onShow } from "@dcloudio/uni-app";
import { ApiError, getStoredToken } from "@/api/client";
import { confirmBill, transcribeStreamUrl } from "@/api/bills";
import { useBillStore } from "@/stores/bill";
import { useLedgerStore } from "@/stores/ledger";
import { useUserStore } from "@/stores/user";
import { useAppStore } from "@/stores/app";
import type { ParsedBill, SSEEvent } from "@/types";
import { createSSEConnection, type SSEConnection } from "@/utils/sse";
import { joinSpeechText, speechErrorMessage } from "@/utils/speech";

const userStore = useUserStore();
const ledgerStore = useLedgerStore();
const billStore = useBillStore();
const appStore = useAppStore();
const rawInput = ref("");
const sourceText = ref("");
const sessionId = ref("");
const clarificationQuestion = ref("");
const parsed = ref<ParsedBill | null>(null);
const advisorMessage = ref<{ summary: string; actions: string[] } | null>(null);
const parsing = ref(false);
const saving = ref(false);
const aaEnabled = ref(false);
const selectedShareIds = ref<number[]>([]);
const voiceRecording = ref(false);
const voiceStatus = ref("");
let stream: SSEConnection | null = null;
let speechBaseText = "";
let speechDraftText = "";
let h5Recognition: any = null;
let speechSequence = 0;
let speechRequest = 0;
let activeSpeechSession = 0;

const voiceButtonLabel = computed(() => voiceRecording.value ? "停止语音输入" : "开始语音输入");

const ledgerNames = computed(() => ledgerStore.ledgers.map((item) => item.name));
const ledgerIndex = computed(() => Math.max(0, ledgerStore.ledgers.findIndex((item) => item.id === ledgerStore.currentId)));
const currentLedgerName = computed(() => ledgerStore.current?.name || "请选择账本");
const currentMembers = computed(() => ledgerStore.current?.members || []);
const isSharedExpense = computed(() => ledgerStore.current?.type === "shared" && parsed.value?.type === "expense");
const canConfirm = computed(() => {
  const value = parsed.value;
  return Boolean(value?.type && value.amount && value.category && value.bill_date) && (!aaEnabled.value || selectedShareIds.value.length >= 2);
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

function updateSpeechDraft(text: string, speechSession = activeSpeechSession) {
  if (!speechSession || speechSession !== activeSpeechSession) return;
  speechDraftText = text.trim();
  rawInput.value = joinSpeechText(speechBaseText, speechDraftText).slice(0, 500);
}

function finishVoiceInput(finalText?: string, speechSession = activeSpeechSession) {
  if (!speechSession || speechSession !== activeSpeechSession) return;
  if (finalText?.trim()) updateSpeechDraft(finalText, speechSession);
  activeSpeechSession = 0;
  voiceRecording.value = false;
  voiceStatus.value = speechDraftText ? "语音已转成文字，可继续修改" : "";
}

function handleVoiceError(code: string, speechSession = activeSpeechSession) {
  if (speechSession && speechSession !== activeSpeechSession) return;
  if (speechSession) {
    activeSpeechSession = 0;
  }
  voiceRecording.value = false;
  voiceStatus.value = "";
  uni.showToast({ title: speechErrorMessage(code), icon: "none", duration: 3000 });
}

function beginSpeechSession() {
  speechBaseText = rawInput.value;
  speechDraftText = "";
  parsed.value = null;
  voiceStatus.value = "正在听，请开始说话…";
  activeSpeechSession = ++speechSequence;
  voiceRecording.value = true;
  return activeSpeechSession;
}

// #ifdef H5
function startH5VoiceInput() {
  const target = window as any;
  const Recognition = target.SpeechRecognition || target.webkitSpeechRecognition;
  if (!Recognition) {
    handleVoiceError("unsupported");
    return;
  }
  const requestId = ++speechRequest;
  voiceStatus.value = "正在请求麦克风权限…";
  const recognition = new Recognition();
  let speechSession = 0;
  h5Recognition = recognition;
  recognition.lang = "zh-CN";
  recognition.continuous = true;
  recognition.interimResults = true;
  recognition.onstart = () => {
    if (requestId !== speechRequest || h5Recognition !== recognition) {
      try { recognition.stop(); } catch { /* The recognition request was already closed. */ }
      return;
    }
    speechSession = beginSpeechSession();
  };
  recognition.onresult = (event: any) => {
    let finalText = "";
    let interimText = "";
    for (let index = 0; index < event.results.length; index += 1) {
      const text = event.results[index][0]?.transcript || "";
      if (event.results[index].isFinal) finalText += text;
      else interimText += text;
    }
    updateSpeechDraft(`${finalText}${interimText}`, speechSession);
  };
  recognition.onerror = (event: any) => {
    if (h5Recognition === recognition) h5Recognition = null;
    if (speechSession || requestId === speechRequest) handleVoiceError(event.error || "unknown", speechSession);
  };
  recognition.onend = () => {
    if (h5Recognition === recognition) h5Recognition = null;
    finishVoiceInput(undefined, speechSession);
  };
  try {
    recognition.start();
  } catch {
    if (h5Recognition === recognition) h5Recognition = null;
    handleVoiceError("unknown", speechSession);
  }
}
// #endif

// #ifdef MP-WEIXIN
function startWechatVoiceInput() {
  uni.showToast({ title: "当前版本暂不支持语音输入", icon: "none" });
}
// #endif

function startVoiceInput() {
  if (activeSpeechSession || h5Recognition) return;
  // #ifdef H5
  startH5VoiceInput();
  // #endif
  // #ifdef MP-WEIXIN
  startWechatVoiceInput();
  // #endif
  // #ifndef H5
  // #ifndef MP-WEIXIN
  handleVoiceError("unsupported");
  // #endif
  // #endif
}

function stopVoiceInput(showStatus = true) {
  const speechSession = activeSpeechSession;
  const recognition = h5Recognition;
  speechRequest += 1;
  voiceRecording.value = false;
  if (!showStatus) {
    activeSpeechSession = 0;
    voiceStatus.value = "";
  } else if (speechSession) {
    voiceStatus.value = "正在完成语音识别…";
  }
  if (!speechSession && !recognition) {
    if (!showStatus) voiceStatus.value = "";
    return;
  }
  try {
    recognition?.stop();
  } catch {
    if (showStatus) finishVoiceInput(undefined, speechSession);
  }
}

function toggleVoiceInput() {
  if (voiceRecording.value) stopVoiceInput();
  else startVoiceInput();
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

function handleStreamEvent(message: SSEEvent) {
  const data = message.data as any;
  if (message.event === "parsed") {
    sessionId.value = data.session_id || sessionId.value;
    const normalized = normalizeParsed(data.parsed || {});
    if (normalized) parsed.value = normalized;
  }
  if (message.event === "clarify") {
    clarificationQuestion.value = data.question;
    sessionId.value = data.session_id;
    rawInput.value = "";
    parsing.value = false;
    stream?.close();
  }
  if (message.event === "awaiting_confirmation") {
    clarificationQuestion.value = "";
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
  aaEnabled.value = Boolean(event.detail.value);
  selectedShareIds.value = aaEnabled.value ? currentMembers.value.map((member) => member.user_id) : [];
}

function onMembersChange(event: any) {
  selectedShareIds.value = (event.detail.value as string[]).map(Number);
}

async function saveBill(force: boolean) {
  if (!parsed.value || !canConfirm.value) return;
  saving.value = true;
  try {
    const bill = await confirmBill({
      ledger_id: ledgerStore.currentId,
      session_id: sessionId.value,
      raw_input: sourceText.value,
      parsed: parsed.value,
      share_user_ids: aaEnabled.value ? selectedShareIds.value : [],
      force,
    });
    billStore.prepend(bill);
    uni.showToast({ title: "记账成功", icon: "success" });
    resetForm();
  } catch (error) {
    if (error instanceof ApiError && error.statusCode === 409) {
      const data = error.data as any;
      uni.showModal({
        title: data?.status === "blocked" ? "预算已超限" : "预算提醒",
        content: data?.message || "确定仍然记账吗？",
        confirmText: "仍然记账",
        success: (result) => {
          if (result.confirm) void saveBill(true);
        },
      });
    } else {
      uni.showToast({ title: error instanceof Error ? error.message : "保存失败", icon: "none" });
    }
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
.manual-guide { display: flex; margin-top: 180rpx; padding: 64rpx 40rpx; flex-direction: column; align-items: center; text-align: center; }
.guide-logo { width: 120rpx; height: 120rpx; border-radius: 30rpx; }
.guide-title { margin-top: 32rpx; color: var(--color-text); font-size: 40rpx; font-weight: 700; }
.guide-subtitle { margin-top: 16rpx; color: var(--color-text-secondary); font-size: 27rpx; line-height: 1.6; }
.manual-guide .primary-button { width: 360rpx; margin-top: 48rpx; }
.card { border-radius: var(--radius-lg); background: var(--color-surface); box-shadow: var(--shadow-sm); }
.brand-row { display: flex; align-items: center; gap: 16rpx; }
.brand-logo { width: 72rpx; height: 72rpx; flex: none; border-radius: 20rpx; }
.brand-copy { display: flex; min-width: 0; flex: 1; flex-direction: column; }
.brand-name { color: var(--color-text); font-size: 34rpx; font-weight: 600; }
.brand-status { display: flex; align-items: center; gap: 8rpx; margin-top: 5rpx; color: var(--color-text-secondary); font-size: 22rpx; }
.brand-status text { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.status-dot { width: 10rpx; height: 10rpx; flex: none; border-radius: 50%; background: var(--color-success); }
.ledger-picker { display: flex; align-items: center; gap: 8rpx; padding: 12rpx 16rpx; border-radius: var(--radius-pill); color: var(--color-primary); background: var(--color-primary-soft); font-size: 22rpx; }
.login-panel { display: flex; margin-top: 32rpx; padding: 48rpx 32rpx; flex-direction: column; align-items: center; text-align: center; }
.login-icon { display: flex; align-items: center; justify-content: center; width: 88rpx; height: 88rpx; border-radius: 28rpx; background: var(--color-primary-soft); }
.login-title { margin-top: 24rpx; font-size: 36rpx; font-weight: 600; }
.login-subtitle { margin-top: 10rpx; color: var(--color-text-secondary); font-size: 25rpx; }
.primary-button, .confirm-button { height: 84rpx; border-radius: var(--radius-pill); color: #fff; background: var(--color-primary); font-size: 29rpx; font-weight: 600; line-height: 84rpx; }
.primary-button { width: 320rpx; margin-top: 32rpx; }
.conversation { margin-top: 34rpx; }
.message-row { display: flex; align-items: flex-start; margin-bottom: 24rpx; animation: message-enter var(--transition-standard) both; }
.message-row.user { justify-content: flex-end; }
.message-avatar { width: 64rpx; height: 64rpx; flex: none; margin-right: 14rpx; border-radius: 20rpx; }
.message-bubble { max-width: 520rpx; padding: 20rpx 24rpx; box-sizing: border-box; font-size: 29rpx; line-height: 1.55; }
.assistant-bubble { border-radius: 8rpx 28rpx 28rpx 28rpx; color: var(--color-text); background: var(--color-surface); box-shadow: var(--shadow-sm); }
.user-bubble { border-radius: 28rpx 8rpx 28rpx 28rpx; color: #fff; background: var(--color-primary); }
.bubble-label { display: block; margin-bottom: 8rpx; color: var(--color-warning); font-size: 23rpx; font-weight: 600; }
.typing-bubble { min-width: 112rpx; }
.typing-dots { display: flex; align-items: center; justify-content: center; gap: 9rpx; height: 28rpx; }
.typing-dots text { width: 11rpx; height: 11rpx; border-radius: 50%; background: #b8b8bd; animation: typing-dot 280ms ease alternate infinite; }
.typing-dots text:nth-child(2) { animation-delay: 80ms; }
.typing-dots text:nth-child(3) { animation-delay: 160ms; }
.result-row { align-items: flex-start; }
.result-section { width: calc(100% - 78rpx); min-width: 0; padding: 30rpx; box-sizing: border-box; }
.section-heading, .share-heading { display: flex; align-items: center; justify-content: space-between; }
.section-heading > view:first-child, .share-heading > view:first-child { display: flex; min-width: 0; flex-direction: column; }
.section-title { font-size: 34rpx; font-weight: 600; }
.section-subtitle, .share-subtitle { margin-top: 6rpx; color: var(--color-text-secondary); font-size: 23rpx; }
.ready-tag { display: flex; align-items: center; gap: 5rpx; padding: 8rpx 13rpx; border-radius: var(--radius-pill); color: var(--color-success); background: #eaf8ee; font-size: 21rpx; }
.type-segment { display: grid; grid-template-columns: 1fr 1fr; gap: 8rpx; margin: 28rpx 0 8rpx; padding: 6rpx; border-radius: 24rpx; background: var(--color-surface-muted); }
.segment-button { height: 68rpx; margin: 0; border-radius: 20rpx; color: var(--color-text-secondary); background: transparent; font-size: 27rpx; line-height: 68rpx; }
.expense-option.active { color: var(--color-danger); background: #fff0ef; }
.income-option.active { color: #248c41; background: #eaf8ee; }
.field-row { display: flex; align-items: center; min-height: 96rpx; border-bottom: 1rpx solid var(--color-border-muted); }
.field-label { width: 112rpx; flex: none; color: var(--color-text-secondary); font-size: 26rpx; }
.field-input { min-width: 0; flex: 1; color: var(--color-text); font-size: 27rpx; text-align: right; }
.amount-input-wrap { display: flex; min-width: 0; flex: 1; align-items: center; justify-content: flex-end; }
.currency { color: var(--color-text); font-size: 34rpx; font-weight: 700; }
.amount-input { width: 230rpx; color: var(--color-text); font-size: 44rpx; font-weight: 700; text-align: right; }
.share-section { margin-top: 28rpx; padding-top: 24rpx; border-top: 1rpx solid var(--color-border); }
.share-title { font-weight: 600; }
.member-list { display: flex; margin-top: 16rpx; flex-direction: column; }
.member-row { display: flex; align-items: center; gap: 14rpx; min-height: 80rpx; }
.member-role { margin-left: auto; color: var(--color-text-secondary); font-size: 23rpx; }
.confirm-button { margin-top: 30rpx; }
.composer-shell { position: fixed; right: 24rpx; bottom: calc(110rpx + constant(safe-area-inset-bottom)); bottom: calc(110rpx + env(safe-area-inset-bottom)); left: 24rpx; z-index: 80; padding: 14rpx; border: 1rpx solid var(--color-border-muted); border-radius: 36rpx; background: var(--color-surface); box-shadow: 0 -4rpx 24rpx rgba(0, 0, 0, .05); }
.composer { display: flex; align-items: flex-end; gap: 12rpx; }
.voice-button, .analyze-button { display: flex; width: 72rpx; height: 72rpx; flex: none; margin: 0; padding: 0; align-items: center; justify-content: center; border-radius: 50%; line-height: 72rpx; }
.voice-button { color: var(--color-primary); background: var(--color-primary-soft); }
.voice-button.recording { color: #fff; background: var(--color-danger); }
.analyze-button { color: #fff; background: var(--color-primary); }
/* 未输入文字时按钮保持可见，仅降低透明度示意待激活 */
.analyze-button.is-idle { opacity: 0.5; }
.speech-input { min-width: 0; min-height: 72rpx; max-height: 180rpx; flex: 1; padding: 15rpx 8rpx; box-sizing: border-box; color: var(--color-text); font-size: 29rpx; line-height: 42rpx; }
.voice-status { display: flex; align-items: center; gap: 10rpx; min-height: 40rpx; padding: 0 10rpx 10rpx; color: var(--color-text-secondary); font-size: 22rpx; }
.voice-status.active { color: var(--color-danger); }
.recording-dot { width: 12rpx; height: 12rpx; flex: none; border-radius: 50%; background: var(--color-danger); }
.input-count { margin-left: auto; color: var(--color-text-secondary); font-family: var(--font-mono); font-size: 20rpx; }
button[disabled] { opacity: .42; }
@keyframes message-enter { from { opacity: 0; transform: translateY(10rpx); } to { opacity: 1; transform: translateY(0); } }
@keyframes typing-dot { from { opacity: .35; transform: translateY(2rpx); } to { opacity: 1; transform: translateY(-2rpx); } }
</style>

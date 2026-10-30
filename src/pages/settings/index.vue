<template>
  <view class="page">
    <view class="profile">
      <image src="/static/logo.jpg" mode="aspectFill" />
      <view><text class="name">{{ userStore.user?.nickname || "荣小账用户" }}</text><text>{{ ledgerStore.current?.name || "未选择账本" }}</text></view>
    </view>
    <view class="menu">
      <view hover-class="pressable" @click="go('/pages/ledgers/index')"><text>账本管理</text><text>›</text></view>
      <view hover-class="pressable" @click="go('/pages/accounts/index')"><text>账户管理</text><text>›</text></view>
      <view hover-class="pressable" @click="go('/pages/categories/index')"><text>分类管理</text><text>›</text></view>
      <view v-if="appStore.aiEnabled" @click="go('/pages/insights/index')"><text>消费洞察</text><text>›</text></view>
    </view>
    <view class="menu">
      <view hover-class="pressable" @click="go('/subpackages/import/index')"><text>导入 Excel 账单</text><text>›</text></view>
      <view hover-class="pressable" @click="exportCsv"><text>导出 CSV</text><text>›</text></view>
      <view hover-class="pressable" @click="exportJson"><text>导出 JSON 备份</text><text>›</text></view>
      <view hover-class="pressable" @click="exportServer"><text>导出账号数据（服务器）</text><text>›</text></view>
    </view>
    <view class="menu">
      <view class="danger-row" hover-class="pressable" @click="deleteAccountPermanently"><text>永久删除账号</text><text>›</text></view>
    </view>
    <button class="logout" @click="logout">退出登录</button>
    <text class="version">荣小账 v2.0.0 · 云端同步</text>
    <BudgetAlert />
</view>
</template>

<script setup lang="ts">
import { onShow } from "@dcloudio/uni-app";
import BudgetAlert from "@/components/BudgetAlert.vue";
import { getBills } from "@/api/bills";
import { getAccounts } from "@/api/accounts";
import { deleteAccount, exportAccount } from "@/api/auth";
import { getCategories } from "@/api/categories";
import { useLedgerStore } from "@/stores/ledger";
import { useUserStore } from "@/stores/user";
import { useAppStore } from "@/stores/app";
import type { Bill } from "@/types";
import { escapeCsvCell } from "@/utils/csv";

const userStore = useUserStore();
const ledgerStore = useLedgerStore();
const appStore = useAppStore();
onShow(async () => {
  await userStore.ensureUser();
  if (!ledgerStore.currentId && userStore.isLoggedIn) await ledgerStore.fetchLedgers();
});
function go(url: string) { uni.navigateTo({ url }); }
async function allBills(): Promise<Bill[]> {
  const result: Bill[] = [];
  let page = 1;
  while (ledgerStore.currentId) {
    const response = await getBills({ ledger_id: ledgerStore.currentId, page, page_size: 100 });
    result.push(...response.items);
    if (result.length >= response.total) break;
    page += 1;
  }
  return result;
}
async function exportCsv() {
  const bills = await allBills();
  if (!bills.length) return void uni.showToast({ title: "暂无数据可导出", icon: "none" });
  const rows = bills.map((bill) => [bill.bill_date, bill.type === "expense" ? "支出" : "收入", bill.category, bill.subcategory, bill.amount, bill.account, bill.note].map(escapeCsvCell).join(","));
  downloadText(`\ufeff日期,类型,分类,细分,金额,账户,备注\n${rows.join("\n")}`, `荣小账_${today()}.csv`, "text/csv");
}
async function exportJson() {
  if (!ledgerStore.currentId) return;
  const [bills, accounts, categories] = await Promise.all([allBills(), getAccounts(ledgerStore.currentId), getCategories(ledgerStore.currentId)]);
  downloadText(JSON.stringify({ version: "2.0", exported_at: new Date().toISOString(), ledger: ledgerStore.current, bills, accounts, categories }, null, 2), `荣小账备份_${today()}.json`, "application/json");
}
function today() { return new Date().toISOString().slice(0, 10); }
function downloadText(content: string, filename: string, mime: string) {
  // #ifdef H5
  const blob = new Blob([content], { type: `${mime};charset=utf-8` });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a"); anchor.href = url; anchor.download = filename; anchor.click(); URL.revokeObjectURL(url);
  // #endif
  // #ifndef H5
  const wxApi = (globalThis as any).wx;
  const path = `${wxApi.env.USER_DATA_PATH}/${filename}`;
  wxApi.getFileSystemManager().writeFile({ filePath: path, data: content, encoding: "utf8", success: () => uni.openDocument({ filePath: path, showMenu: true }) });
  // #endif
}
async function exportServer() {
  try {
    const data = await exportAccount();
    downloadText(
      JSON.stringify(data, null, 2),
      `荣小账账号数据_${today()}.json`,
      "application/json",
    );
  } catch (error) {
    uni.showToast({
      title: error instanceof Error ? error.message : "导出失败，请重试",
      icon: "none",
    });
  }
}

function deleteAccountPermanently() {
  uni.showModal({
    title: "永久删除账号",
    content: "账号、账单、预算、分类和账户数据都会被删除，无法恢复。确定继续吗？",
    confirmText: "永久删除",
    confirmColor: "#ff3b30",
    success: async (result) => {
      if (!result.confirm) return;
      try {
        await deleteAccount();
        userStore.logout();
        uni.showToast({ title: "账号已删除", icon: "none" });
        setTimeout(() => uni.reLaunch({ url: "/pages/index/index" }), 500);
      } catch (error) {
        uni.showToast({
          title: error instanceof Error ? error.message : "删除失败，请重试",
          icon: "none",
        });
      }
    },
  });
}

function logout() { userStore.logout(); uni.showToast({ title: "已退出", icon: "none" }); }
</script>

<style scoped>
.page { min-height: 100vh; padding: 28rpx 28rpx 70rpx; box-sizing: border-box; }
.profile { display: flex; align-items: center; gap: 20rpx; padding: 30rpx; border-radius: var(--radius-lg); background: var(--color-surface); box-shadow: var(--shadow-sm); }
.profile image { width: 90rpx; height: 90rpx; border-radius: 26rpx; }
.profile > view { display: flex; flex-direction: column; }
.name { font-size: 32rpx; font-weight: 600; }
.profile view text:last-child { margin-top: 6rpx; color: var(--color-text-secondary); font-size: 22rpx; }
.menu { margin-top: 16rpx; overflow: hidden; border-radius: var(--radius-lg); background: var(--color-surface); box-shadow: var(--shadow-sm); }
.menu view { display: flex; align-items: center; justify-content: space-between; min-height: 90rpx; padding: 0 28rpx; border-bottom: 1rpx solid var(--color-border-muted); font-size: 27rpx; }
.menu view:last-child { border-bottom: 0; }
.menu view text:last-child { color: var(--color-text-secondary); font-size: 36rpx; }
.menu .danger-row { color: var(--color-danger); }
.logout { width: 100%; height: var(--button-height-lg); margin-top: 22rpx; border: 0; color: var(--color-danger); background: #fff0ef; border-radius: var(--radius-pill); font-size: var(--button-font-lg); font-weight: 600; line-height: var(--button-height-lg); }
.version { display: block; margin-top: 8rpx; color: var(--color-text-secondary); font-size: 22rpx; text-align: center; }
</style>

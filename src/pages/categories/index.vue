<template>
  <view class="page">
    <view class="tabs"><button :class="{ active: activeType === 'expense' }" @click="activeType = 'expense'">支出</button><button :class="{ active: activeType === 'income' }" @click="activeType = 'income'">收入</button></view>
    <view v-if="loadError" class="load-error"><text>{{ loadError }}</text><button class="retry-load" :disabled="loading" @click="load">重新加载</button></view>
    <view v-for="parent in tree" :key="parent.key" class="group">
      <view class="parent-row"><view><text class="parent-name">{{ parent.name }}</text><text class="source">{{ parent.custom ? "自定义" : "预置" }}</text></view><view><button @click="openAdd(parent.name)">添加子类</button><button v-if="parent.custom" @click="edit(parent.id, parent.name)">重命名</button></view></view>
      <view v-for="child in parent.children" :key="child.key" class="child-row"><text>{{ child.name }}</text><view v-if="child.custom"><button @click="edit(child.id, child.name)">重命名</button><button class="danger" @click="remove(child.id)">删除</button></view></view>
      <button v-if="parent.custom" class="remove-parent" @click="remove(parent.id)">删除该大类</button>
    </view>
    <button class="add-parent" @click="openAdd('')">添加大类</button>
    <u-modal :show="modalVisible" :title="editingId ? '重命名分类' : parentName ? '添加子类' : '添加大类'" :confirm-text="saving ? '保存中' : '确定'" :show-cancel-button="!saving" @confirm="submit" @cancel="cancelModal">
      <view class="form"><input v-model="name" :disabled="saving" placeholder="分类名称" maxlength="64" /><text v-if="submitError" class="form-error">{{ submitError }}</text></view>
    </u-modal>
</view>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { onShow } from "@dcloudio/uni-app";
import { CATEGORY_PRESETS } from "@/constants/categories";
import { useCategoryStore } from "@/stores/category";
import { useLedgerStore } from "@/stores/ledger";
import type { BillType } from "@/types";

const presets = CATEGORY_PRESETS;
const store = useCategoryStore();
const ledgerStore = useLedgerStore();
const activeType = ref<BillType>("expense");
const modalVisible = ref(false);
const parentName = ref("");
const editingId = ref(0);
const name = ref("");
const loading = ref(false);
const saving = ref(false);
const loadError = ref("");
const submitError = ref("");
type CategoryChild = { key: string; id: number; name: string; custom: boolean };
type CategoryGroup = { key: string; id: number; name: string; custom: boolean; children: CategoryChild[] };
const tree = computed(() => {
  const result: CategoryGroup[] = Object.entries(presets[activeType.value]).map(([parent, children]) => ({ key: `preset-parent:${activeType.value}:${parent}`, id: 0, name: parent, custom: false, children: children.map((child) => ({ key: `preset-child:${activeType.value}:${parent}:${child}`, id: 0, name: child, custom: false })) }));
  const custom = store.categories.filter((item) => item.type === activeType.value);
  custom.filter((item) => !item.parent_name).forEach((item) => result.push({ key: `custom-parent:${item.id}`, id: item.id, name: item.name, custom: true, children: [] }));
  custom.filter((item) => item.parent_name).forEach((item) => { const parent = result.find((source) => source.name === item.parent_name); if (parent) parent.children.push({ key: `custom-child:${item.id}`, id: item.id, name: item.name, custom: true }); });
  return result;
});
async function load() {
  loading.value = true;
  loadError.value = "";
  try {
    if (!ledgerStore.currentId) await ledgerStore.fetchLedgers();
    if (ledgerStore.currentId) await store.fetchCategories(ledgerStore.currentId);
    else loadError.value = "请先创建或加入账本";
  } catch (error) {
    loadError.value = error instanceof Error ? error.message : "分类加载失败，请重试";
  } finally { loading.value = false; }
}
onShow(() => void load());
function openAdd(parent: string) { editingId.value = 0; parentName.value = parent; name.value = ""; submitError.value = ""; modalVisible.value = true; }
function edit(id: number, oldName: string) {
  const target = store.categories.find((item) => item.id === id);
  editingId.value = id;
  parentName.value = target?.parent_name || "";
  name.value = oldName;
  submitError.value = "";
  modalVisible.value = true;
}
function hasNameConflict(value: string) {
  if (!parentName.value) {
    return tree.value.some((parent) => parent.name === value && (!editingId.value || parent.id !== editingId.value));
  }
  const parent = tree.value.find((item) => item.name === parentName.value);
  return parent?.children.some((child) => child.name === value && (!editingId.value || child.id !== editingId.value)) ?? false;
}
async function submit() {
  if (saving.value) return;
  const value = name.value.trim();
  submitError.value = "";
  if (!value) { submitError.value = "请输入分类名称"; uni.showToast({ title: "请输入分类名称", icon: "none" }); return; }
  // 从补载账本开始锁定，避免网络慢时连续点确定产生重复请求。
  saving.value = true;
  try {
    if (!ledgerStore.currentId) await ledgerStore.fetchLedgers();
    if (!ledgerStore.currentId) { submitError.value = "请先创建或加入账本"; return; }
    if (hasNameConflict(value)) {
      submitError.value = parentName.value ? "该大类下已有同名子类" : "同名大类已存在";
      uni.showToast({ title: submitError.value, icon: "none" });
      return;
    }
    if (editingId.value) await store.rename(editingId.value, value);
    else await store.create(ledgerStore.currentId, activeType.value, parentName.value, value);
    modalVisible.value = false;
    uni.showToast({ title: editingId.value ? "分类已更新" : "分类已添加", icon: "success" });
  } catch (error) {
    submitError.value = error instanceof Error ? error.message : "保存失败，请重试";
    modalVisible.value = true;
  } finally { saving.value = false; }
}
function cancelModal() { if (!saving.value) { modalVisible.value = false; submitError.value = ""; } }
function remove(id: number) {
  if (!id) return;
  uni.showModal({
    title: "删除分类",
    content: "删除大类会同时删除其自定义子类。",
    success: async (result) => {
      if (!result.confirm) return;
      try {
        await store.remove(id);
      } catch (error) {
        uni.showToast({
          title: error instanceof Error ? error.message : "删除失败，请重试",
          icon: "none",
        });
      }
    },
  });
}
</script>

<style scoped>
.page { min-height: 100vh; padding: 24rpx 28rpx 80rpx; box-sizing: border-box; }
.tabs { display: grid; grid-template-columns: 1fr 1fr; gap: 8rpx; padding: 6rpx; border-radius: 22rpx; background: var(--color-surface-muted); }
.tabs button { height: var(--button-height-md); margin: 0; border: 0; border-radius: 20rpx; background: transparent; font-size: var(--button-font-md); font-weight: 600; line-height: var(--button-height-md); }
.tabs button:first-child.active { color: var(--color-danger); background: #fff0ef; }
.tabs button:last-child.active { color: #248c41; background: #eaf8ee; }
.group { margin-top: 16rpx; overflow: hidden; border-radius: var(--radius-lg); background: var(--color-surface); box-shadow: var(--shadow-sm); }
.parent-row, .child-row { display: flex; align-items: center; justify-content: space-between; min-height: 88rpx; padding: 0 20rpx; border-bottom: 1rpx solid var(--color-border-muted); }
.parent-row > view { display: flex; align-items: center; gap: 10rpx; }
.parent-name { font-weight: 600; }
.source { padding: 5rpx 10rpx; border-radius: var(--radius-pill); color: var(--color-text-secondary); background: var(--color-surface-muted); font-size: 20rpx; }
.parent-row button, .child-row button { display: inline-block; width: auto; height: var(--button-height-sm); margin: 0 0 0 8rpx; padding: 0 16rpx; border: 0; border-radius: 16rpx; color: var(--color-primary); background: transparent; font-size: var(--button-font-sm); font-weight: 600; line-height: var(--button-height-sm); }
.child-row { padding-left: 42rpx; }
.danger, .remove-parent { color: var(--color-danger) !important; }
.remove-parent { margin: 10rpx auto; background: transparent; font-size: 22rpx; }
.add-parent { width: 100%; height: var(--button-height-lg); margin-top: 22rpx; border: 0; color: #fff; background: var(--color-primary); border-radius: var(--radius-pill); font-size: var(--button-font-lg); font-weight: 600; line-height: var(--button-height-lg); }
.form { width: 100%; padding: 20rpx; box-sizing: border-box; }
.form input { height: 78rpx; padding: 0 20rpx; border-radius: 18rpx; background: var(--color-surface-muted); font-size: 26rpx; }
.form-error { display: block; margin-top: 12rpx; color: var(--color-danger); font-size: 23rpx; }
.load-error { display: flex; align-items: center; justify-content: space-between; margin-top: 16rpx; padding: 20rpx 22rpx; border-radius: var(--radius-lg); color: var(--color-danger); background: #fff0ef; font-size: 24rpx; }
.retry-load { margin: 0; padding: 0 18rpx; color: var(--color-primary); background: transparent; font-size: 23rpx; }
</style>

<template>
  <view class="page">
    <view class="tabs"><button :class="{ active: activeType === 'expense' }" @click="activeType = 'expense'">支出</button><button :class="{ active: activeType === 'income' }" @click="activeType = 'income'">收入</button></view>
    <view v-for="parent in tree" :key="parent.key" class="group">
      <view class="parent-row"><view><text class="parent-name">{{ parent.name }}</text><text class="source">{{ parent.custom ? "自定义" : "预置" }}</text></view><view><button @click="openAdd(parent.name)">添加子类</button><button v-if="parent.custom" @click="edit(parent.id, parent.name)">重命名</button></view></view>
      <view v-for="child in parent.children" :key="child.key" class="child-row"><text>{{ child.name }}</text><view v-if="child.custom"><button @click="edit(child.id, child.name)">重命名</button><button class="danger" @click="remove(child.id)">删除</button></view></view>
      <button v-if="parent.custom" class="remove-parent" @click="remove(parent.id)">删除该大类</button>
    </view>
    <button class="add-parent" @click="openAdd('')">添加大类</button>
    <u-modal :show="modalVisible" :title="editingId ? '重命名分类' : parentName ? '添加子类' : '添加大类'" show-cancel-button @confirm="submit" @cancel="modalVisible = false">
      <view class="form"><input v-model="name" placeholder="分类名称" maxlength="64" /></view>
    </u-modal>
  </view>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { onShow } from "@dcloudio/uni-app";
import { useCategoryStore } from "@/stores/category";
import { useLedgerStore } from "@/stores/ledger";
import type { BillType } from "@/types";

const presets = {
  expense: { "餐饮美食": ["早餐", "午餐", "晚餐", "外卖", "奶茶饮品"], "交通出行": ["公交地铁", "打车", "加油"], "购物消费": ["服装鞋包", "家居日用", "数码电器"], "居住物业": ["房租/房贷", "水费", "电费"], "休闲娱乐": ["电影演出", "运动健身", "旅游度假"], "人情社交": ["红包礼金", "送礼"], "医疗健康": ["看病挂号", "药品"], "教育学习": ["课程培训", "书籍"], "通讯": ["话费", "流量套餐"] },
  income: { "工资收入": ["工资", "奖金", "补贴"], "副业收入": ["兼职", "红包收入"], "其他收入": ["退款", "闲置出售", "其他"] },
};
const store = useCategoryStore();
const ledgerStore = useLedgerStore();
const activeType = ref<BillType>("expense");
const modalVisible = ref(false);
const parentName = ref("");
const editingId = ref(0);
const name = ref("");
type CategoryChild = { key: string; id: number; name: string; custom: boolean };
type CategoryGroup = { key: string; id: number; name: string; custom: boolean; children: CategoryChild[] };
const tree = computed(() => {
  const result: CategoryGroup[] = Object.entries(presets[activeType.value]).map(([parent, children]) => ({ key: `preset-parent:${activeType.value}:${parent}`, id: 0, name: parent, custom: false, children: children.map((child) => ({ key: `preset-child:${activeType.value}:${parent}:${child}`, id: 0, name: child, custom: false })) }));
  const custom = store.categories.filter((item) => item.type === activeType.value);
  custom.filter((item) => !item.parent_name).forEach((item) => result.push({ key: `custom-parent:${item.id}`, id: item.id, name: item.name, custom: true, children: [] }));
  custom.filter((item) => item.parent_name).forEach((item) => { const parent = result.find((source) => source.name === item.parent_name); if (parent) parent.children.push({ key: `custom-child:${item.id}`, id: item.id, name: item.name, custom: true }); });
  return result;
});
async function load() { if (!ledgerStore.currentId) await ledgerStore.fetchLedgers(); if (ledgerStore.currentId) await store.fetchCategories(ledgerStore.currentId); }
onShow(() => void load());
function openAdd(parent: string) { editingId.value = 0; parentName.value = parent; name.value = ""; modalVisible.value = true; }
function edit(id: number, oldName: string) {
  const target = store.categories.find((item) => item.id === id);
  editingId.value = id;
  parentName.value = target?.parent_name || "";
  name.value = oldName;
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
  const value = name.value.trim();
  if (!value || !ledgerStore.currentId) return;
  if (hasNameConflict(value)) {
    uni.showToast({ title: parentName.value ? "该大类下已有同名子类" : "同名大类已存在", icon: "none" });
    return;
  }
  if (editingId.value) await store.rename(editingId.value, value);
  else await store.create(ledgerStore.currentId, activeType.value, parentName.value, value);
  modalVisible.value = false;
}
function remove(id: number) { if (!id) return; uni.showModal({ title: "删除分类", content: "删除大类会同时删除其自定义子类。", success: async (result) => { if (result.confirm) await store.remove(id); } }); }
</script>

<style scoped>
.page { min-height: 100vh; padding: 24rpx 28rpx 80rpx; box-sizing: border-box; }
.tabs { display: grid; grid-template-columns: 1fr 1fr; gap: 8rpx; padding: 6rpx; border-radius: 24rpx; background: var(--color-surface-muted); }
.tabs button { height: 66rpx; margin: 0; border: 0; border-radius: 20rpx; background: transparent; line-height: 66rpx; }
.tabs button:first-child.active { color: var(--color-danger); background: #fff0ef; }
.tabs button:last-child.active { color: #248c41; background: #eaf8ee; }
.group { margin-top: 18rpx; overflow: hidden; border-radius: var(--radius-lg); background: var(--color-surface); box-shadow: var(--shadow-sm); }
.parent-row, .child-row { display: flex; align-items: center; justify-content: space-between; min-height: 88rpx; padding: 0 22rpx; border-bottom: 1rpx solid var(--color-border-muted); }
.parent-row > view { display: flex; align-items: center; gap: 10rpx; }
.parent-name { font-weight: 600; }
.source { padding: 5rpx 10rpx; border-radius: var(--radius-pill); color: var(--color-text-secondary); background: var(--color-surface-muted); font-size: 20rpx; }
.parent-row button, .child-row button { display: inline-block; width: auto; height: 54rpx; margin: 0 0 0 8rpx; padding: 0 12rpx; color: var(--color-primary); background: transparent; font-size: 22rpx; line-height: 54rpx; }
.child-row { padding-left: 46rpx; }
.danger, .remove-parent { color: var(--color-danger) !important; }
.remove-parent { margin: 10rpx auto; background: transparent; font-size: 22rpx; }
.add-parent { margin-top: 24rpx; color: #fff; background: var(--color-primary); border-radius: var(--radius-pill); }
.form { width: 100%; padding: 20rpx; box-sizing: border-box; }
.form input { height: 80rpx; padding: 0 20rpx; border-radius: 20rpx; background: var(--color-surface-muted); }
</style>

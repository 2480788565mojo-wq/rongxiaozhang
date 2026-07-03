<template>
	<view class="page-categories">
		<view class="tip">
			<text>预置分类不可修改，自定义分类可重命名和删除</text>
		</view>

		<view class="cat-section">
			<view class="section-header">
				<text class="section-title">支出分类</text>
				<text class="add-btn" @click="showAddTop('expense')">+ 添加大类</text>
			</view>
			<view class="cat-group" v-for="parent in expenseList" :key="parent.key">
				<view class="parent-row">
					<view class="parent-info">
						<text class="parent-name">{{ parent.name }}</text>
						<text class="tag-preset" v-if="!parent.isCustom">预置</text>
						<text class="tag-custom" v-else>自定义</text>
					</view>
					<view class="parent-actions">
						<text class="action-btn" @click="showSubInput(parent)">+ 子类</text>
						<template v-if="parent.isCustom">
							<text class="action-btn rename" @click="showRename(parent)">R</text>
							<text class="action-btn danger" @click="confirmDelete(parent)">X</text>
						</template>
					</view>
				</view>
				<view class="child-list" v-if="parent.children.length > 0">
					<view class="child-row" v-for="child in parent.children" :key="child.key">
						<text class="child-name">{{ child.name }}</text>
						<text class="tag-preset" v-if="!child.isCustom">预置</text>
						<text class="tag-custom" v-else>自定义</text>
						<view class="child-actions" v-if="child.isCustom">
							<text class="action-btn rename" @click="showRename(child)">R</text>
							<text class="action-btn danger" @click="confirmDelete(child)">X</text>
						</view>
					</view>
				</view>
			</view>
		</view>

		<view class="cat-section">
			<view class="section-header">
				<text class="section-title">收入分类</text>
				<text class="add-btn" @click="showAddTop('income')">+ 添加大类</text>
			</view>
			<view class="cat-group" v-for="parent in incomeList" :key="parent.key">
				<view class="parent-row">
					<view class="parent-info">
						<text class="parent-name">{{ parent.name }}</text>
						<text class="tag-preset" v-if="!parent.isCustom">预置</text>
						<text class="tag-custom" v-else>自定义</text>
					</view>
					<view class="parent-actions">
						<text class="action-btn" @click="showSubInput(parent)">+ 子类</text>
						<template v-if="parent.isCustom">
							<text class="action-btn rename" @click="showRename(parent)">R</text>
							<text class="action-btn danger" @click="confirmDelete(parent)">X</text>
						</template>
					</view>
				</view>
				<view class="child-list" v-if="parent.children.length > 0">
					<view class="child-row" v-for="child in parent.children" :key="child.key">
						<text class="child-name">{{ child.name }}</text>
						<text class="tag-preset" v-if="!child.isCustom">预置</text>
						<text class="tag-custom" v-else>自定义</text>
						<view class="child-actions" v-if="child.isCustom">
							<text class="action-btn rename" @click="showRename(child)">R</text>
							<text class="action-btn danger" @click="confirmDelete(child)">X</text>
						</view>
					</view>
				</view>
			</view>
		</view>
		<u-modal :show="showAddModal" title="添加大类" @confirm="confirmAddTop" @cancel="showAddModal = false">
			<view class="modal-form">
				<view class="modal-field">
					<text class="field-label">类型:</text>
					<text class="field-value">{{ addTopType === 'expense' ? '支出' : '收入' }}</text>
				</view>
				<view class="modal-field">
					<text class="field-label">名称:</text>
					<input class="field-input" v-model="addTopName" placeholder="输入大类名称" />
				</view>
			</view>
		</u-modal>

		<u-modal :show="showSubModal" title="添加子分类" @confirm="confirmAddSub" @cancel="showSubModal = false">
			<view class="modal-form">
				<view class="modal-field">
					<text class="field-label">所属大类:</text>
					<text class="field-value">{{ subParentName }}</text>
				</view>
				<view class="modal-field">
					<text class="field-label">名称:</text>
					<input class="field-input" v-model="addSubName" placeholder="输入子分类名称" />
				</view>
			</view>
		</u-modal>

		<u-modal :show="showRenameModal" title="重命名" @confirm="confirmRename" @cancel="showRenameModal = false">
			<view class="modal-form">
				<view class="modal-field">
					<text class="field-label">新名称:</text>
					<input class="field-input" v-model="renameName" placeholder="输入新名称" />
				</view>
			</view>
		</u-modal>

		<u-modal :show="showDeleteModal" title="确认删除" :content="deleteTip"
			@confirm="doDelete" @cancel="showDeleteModal = false"></u-modal>
	</view>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { onShow } from '@dcloudio/uni-app';
import {
	getPresetCategories,
	getCustomCategories,
	addCustomCategory,
	updateCustomCategoryName,
	deleteCustomCategory,
} from '@/utils/store';

interface CatChild {
	key: string;
	name: string;
	isCustom: boolean;
	_id?: string;
}

interface CatItem {
	key: string;
	name: string;
	isCustom: boolean;
	_id?: string;
	children: CatChild[];
}

const expenseList = ref<CatItem[]>([]);
const incomeList = ref<CatItem[]>([]);

const showAddModal = ref(false);
const addTopType = ref<'expense' | 'income'>('expense');
const addTopName = ref('');
const showSubModal = ref(false);
const subParentName = ref('');
const addSubName = ref('');
const showRenameModal = ref(false);
const renameTarget = ref<{ _id: string } | null>(null);
const renameName = ref('');
const showDeleteModal = ref(false);
const deleteTarget = ref<{ _id: string; name: string } | null>(null);
const deleteTip = ref('');

function buildList(type: 'expense' | 'income'): CatItem[] {
	const presets = getPresetCategories()[type];
	const customs = getCustomCategories().filter(c => c.type === type);
	const result: CatItem[] = [];
	let ki = 0;

	presets.forEach(p => {
		const item: CatItem = { key: 'p' + ki++, name: p.name, isCustom: false, children: [] };
		p.children.forEach(ch => {
			item.children.push({ key: 'pc' + ki++, name: ch, isCustom: false });
		});
		result.push(item);
	});

	const customParents = customs.filter(c => c.parentName === '');
	customParents.forEach(cp => {
		const item: CatItem = { key: 'c' + ki++, name: cp.name, isCustom: true, _id: cp._id, children: [] };
		customs.filter(c => c.parentName === cp.name).forEach(ch => {
			item.children.push({ key: 'cc' + ki++, name: ch.name, isCustom: true, _id: ch._id });
		});
		result.push(item);
	});

	customs.filter(c => c.parentName !== '').forEach(cc => {
		const p = result.find(r => r.name === cc.parentName);
		if (p && !p.children.some(ch => ch.name === cc.name)) {
			p.children.push({ key: 'cc' + ki++, name: cc.name, isCustom: true, _id: cc._id });
		}
	});

	return result;
}

function loadData() {
	expenseList.value = buildList('expense');
	incomeList.value = buildList('income');
}

onShow(() => { loadData(); });
loadData();

function showAddTop(type: 'expense' | 'income') {
	addTopType.value = type;
	addTopName.value = '';
	showAddModal.value = true;
}

function confirmAddTop() {
	const name = addTopName.value.trim();
	if (!name) { uni.showToast({ title: '请输入名称', icon: 'none' }); return; }
	const r = addCustomCategory(addTopType.value, '', name);
	if (!r) { uni.showToast({ title: '名称已存在或冲突', icon: 'none' }); return; }
	uni.showToast({ title: '添加成功', icon: 'success' });
	showAddModal.value = false;
	loadData();
}

function showSubInput(parent: CatItem) {
	subParentName.value = parent.name;
	addSubName.value = '';
	showSubModal.value = true;
}

function confirmAddSub() {
	const name = addSubName.value.trim();
	if (!name) { uni.showToast({ title: '请输入名称', icon: 'none' }); return; }
	const type = expenseList.value.some(e => e.key === subParentName.value) ? 'expense' : 'income';
	const r = addCustomCategory(type, subParentName.value, name);
	if (!r) { uni.showToast({ title: '名称已存在或冲突', icon: 'none' }); return; }
	uni.showToast({ title: '添加成功', icon: 'success' });
	showSubModal.value = false;
	loadData();
}

function showRename(item: CatItem | CatChild) {
	renameTarget.value = { _id: item._id || '' };
	renameName.value = item.name;
	showRenameModal.value = true;
}

function confirmRename() {
	if (!renameTarget.value) return;
	const name = renameName.value.trim();
	if (!name) { uni.showToast({ title: '请输入名称', icon: 'none' }); return; }
	const ok = updateCustomCategoryName(renameTarget.value._id, name);
	if (!ok) { uni.showToast({ title: '名称已存在或冲突', icon: 'none' }); return; }
	uni.showToast({ title: '重命名成功', icon: 'success' });
	showRenameModal.value = false;
	loadData();
}

function confirmDelete(item: CatItem | CatChild) {
	if (!item._id) return;
	deleteTarget.value = { _id: item._id, name: item.name };
	deleteTip.value = '确定要删除 "' + item.name + '" 吗？';
	showDeleteModal.value = true;
}

function doDelete() {
	if (!deleteTarget.value) return;
	deleteCustomCategory(deleteTarget.value._id);
	uni.showToast({ title: '已删除', icon: 'success' });
	showDeleteModal.value = false;
	loadData();
}
</script>

<style lang="scss" scoped>
.page-categories { padding: 20rpx 30rpx 120rpx; }
.tip { background: #eef6ff; padding: 20rpx; border-radius: 12rpx; margin-bottom: 24rpx; }
.tip text { font-size: 24rpx; color: #2979ff; }

.cat-section {
	background: #fff; border-radius: 16rpx; margin-bottom: 24rpx; overflow: hidden;
	box-shadow: 0 2rpx 8rpx rgba(0,0,0,0.04);
}
.section-header {
	display: flex; justify-content: space-between; align-items: center;
	padding: 24rpx 30rpx; border-bottom: 2rpx solid #f5f5f5;
}
.section-title { font-size: 30rpx; font-weight: bold; }
.add-btn { font-size: 26rpx; color: #2979ff; }

.parent-row {
	display: flex; justify-content: space-between; align-items: center;
	padding: 24rpx 30rpx; background: #fafbff; border-bottom: 1rpx solid #f0f0f0;
}
.parent-info { display: flex; align-items: center; gap: 12rpx; }
.parent-name { font-size: 28rpx; font-weight: bold; }
.parent-actions { display: flex; align-items: center; gap: 16rpx; }

.child-row {
	display: flex; align-items: center; padding: 18rpx 30rpx 18rpx 60rpx;
	border-bottom: 1rpx solid #f8f8f8;
}
.child-name { font-size: 26rpx; flex: 1; }

.tag-preset {
	font-size: 20rpx; color: #999; background: #f5f5f5;
	padding: 2rpx 12rpx; border-radius: 6rpx;
}
.tag-custom {
	font-size: 20rpx; color: #2979ff; background: #eef6ff;
	padding: 2rpx 12rpx; border-radius: 6rpx;
}
.action-btn { font-size: 24rpx; color: #2979ff; padding: 4rpx 8rpx; }
.action-btn.danger { color: #dd524d; }

.modal-form { padding: 30rpx; }
.modal-field { margin-bottom: 24rpx; }
.field-label { font-size: 26rpx; color: #666; display: block; margin-bottom: 8rpx; }
.field-value { font-size: 28rpx; }
.field-input {
	font-size: 26rpx; border: 1rpx solid #ddd; border-radius: 8rpx;
	padding: 12rpx 16rpx; width: 100%; box-sizing: border-box;
}
</style>


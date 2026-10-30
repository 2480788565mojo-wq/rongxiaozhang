<template>
	<view class="page-add">
		<view class="page-heading">
			<text class="heading-title">{{ editId ? '修改账单' : '手动记一笔' }}</text>
			<text class="heading-subtitle">填写账单明细</text>
		</view>
		<view v-if="loadError" class="load-error">{{ loadError }}</view>
		<view class="form-section">
			<!-- 收支类型切换：支出 / 收入 -->
			<view class="type-switch">
				<button class="type-btn" :class="{ active: formData.type === 'expense' }" @click="switchType('expense')">支出</button>
				<button class="type-btn" :class="{ active: formData.type === 'income' }" @click="switchType('income')">收入</button>
			</view>

			<!-- 金额输入框 -->
			<view class="amount-input" :class="formData.type">
				<text class="currency">¥</text>
				<input type="digit" v-model="formData.amount" placeholder="0.00" class="amount-field" />
			</view>

			<view class="form-list">
				<!-- 选择分类：先选大类再选子类 -->
				<view class="form-item" @click="selectParent">
					<text class="form-label">分类</text>
					<text class="form-value">{{ selectedCategory || '请选择' }}</text>
					<text class="arrow">&gt;</text>
				</view>
				<!-- 选择账户 -->
				<view class="form-item" @click="showAccount = true">
					<text class="form-label">账户</text>
					<text class="form-value">{{ formData.account || '未设置（可选）' }}</text>
					<text class="arrow">&gt;</text>
				</view>
				<!-- 选择日期，默认今天 -->
				<picker mode="date" :value="formData.date" @change="onDateChange">
					<view class="form-item" style="border-bottom: none;">
						<text class="form-label">日期</text>
						<text class="form-value">{{ formData.date }}</text>
						<text class="arrow">&gt;</text>
					</view>
				</picker>
				<!-- 备注，选填 -->
				<view class="form-item">
					<text class="form-label">备注</text>
					<input type="text" v-model="formData.note" :focus="noteFocused" @blur="noteFocused = false" :disabled="voiceBusy" :maxlength="256" placeholder="选填，可语音输入" class="note-input" />
				</view>
			</view>
		</view>

		<view class="voice-section">
      <button class="voice-button" :disabled="saving || loading" @click="handleVoiceInput">{{ voiceBusy ? '结束语音输入' : '语音输入备注' }}</button>
      <text>{{ voiceStatus || '说出账单说明，自动转成备注；金额和分类请手动填写。' }}</text>
    </view>
    <view class="btn-save">
			<u-button class="save-button" :disabled="loading || !!loadError || saving || voiceBusy" :loading="saving" type="primary" size="large" @click="saveBill">保存</u-button>
		</view>

		<u-picker :show="showAccount" :columns="[accountList]" @confirm="onAccountConfirm" @cancel="showAccount = false" keyName="name"></u-picker>

		<!-- 分类选择弹窗 -->
		<view v-if="showCategory" class="cat-mask" @click="showCategory = false">
			<view class="cat-popup" @click.stop>
				<view class="cat-header">
					<text class="cat-title">{{ catStep === 'parent' ? '选择分类' : '选择子分类' }}</text>
					<text class="cat-close" @click="showCategory = false">✕</text>
				</view>
				<scroll-view scroll-y class="cat-list" style="height: 56vh;">
					<view
						v-for="(item, idx) in catStep === 'parent' ? parentOptions : childOptions"
						:key="idx"
						class="cat-item"
						@click="onCatSelect(idx)"
					>
						<text>{{ item }}</text>
					</view>
				</scroll-view>
			</view>
		</view>
</view>
</template>

<script setup lang="ts">
// 导入 Vue 响应式 API 和项目数据操作函数
import { ref, reactive, toRef } from 'vue';
import { useVoiceInput } from '@/composables/useVoiceInput';
import { buildCategoryOptions } from '@/constants/categories';
import { keyboardVoiceHint } from '@/utils/speech';
import { getAccounts } from '@/api/accounts';
import type { Bill, ParsedBill } from '@/types';
import { onLoad, onShow } from '@dcloudio/uni-app';
import { getBill, createBill as createBillApi, updateBill as updateBillApi } from '@/api/bills';
import { useBillStore } from '@/stores/bill';
import { useCategoryStore } from '@/stores/category';
import { useLedgerStore } from '@/stores/ledger';
import { useUserStore } from '@/stores/user';

const userStore = useUserStore();
const ledgerStore = useLedgerStore();
const billStore = useBillStore();
const categoryStore = useCategoryStore();

// 表单数据：类型（支出/收入）、金额、分类、账户、日期、备注
const formData = reactive({
	type: 'expense' as 'expense' | 'income',
	amount: '',
	category: '',
  subcategory: '',
	account: '',
	date: `${new Date().getFullYear()}-${String(new Date().getMonth() + 1).padStart(2, '0')}-${String(new Date().getDate()).padStart(2, '0')}`,
	note: '',
});

const { busy: voiceBusy, status: voiceStatus, toggle: toggleVoice, cancel: cancelVoice } = useVoiceInput(toRef(formData, 'note'), 256);
const noteFocused = ref(false);
const editId = ref(0);
const originalBill = ref<Bill | null>(null);
const loading = ref(false);
const loadError = ref('');
const saving = ref(false);
const showAccount = ref(false);
const selectedCategory = ref('');
const showCategory = ref(false);
const catStep = ref<'parent' | 'child'>('parent');
const parentOptions = ref<string[]>([]);
const childOptions = ref<string[]>([]);
const selectedParent = ref<{ name: string; children: string[] } | null>(null);
const currentParents = ref<{name: string; children: string[]}[]>([]);

// 选择大类：预置分类和云端自定义分类合并展示
function selectParent() {
	const all = buildCategoryOptions(formData.type, categoryStore.categories);
	parentOptions.value = all.map(c => c.name);
	currentParents.value = all.map(c => ({ name: c.name, children: c.children }));
	catStep.value = 'parent';
	showCategory.value = true;
}

async function loadCategories() {
  const ledgerId = originalBill.value?.ledger_id || ledgerStore.currentId;
  if (!userStore.isLoggedIn || !ledgerId) return;
  try {
    await categoryStore.fetchCategories(ledgerId);
  } catch {
    // 分类接口失败时仍可用预置分类记账，不阻塞保存。
  }
}

function onCatSelect(idx: number) {
	if (catStep.value === 'parent') {
		const parent = currentParents.value[idx];
		if (parent && parent.children.length > 0) {
			selectedParent.value = parent;
			childOptions.value = parent.children;
			catStep.value = 'child';
		} else if (parent) {
			selectedCategory.value = parent.name;
			formData.category = parent.name;
      formData.subcategory = '';
			showCategory.value = false;
		}
	} else {
		const child = childOptions.value[idx];
		if (child && selectedParent.value) {
			selectedCategory.value = selectedParent.value.name + ' › ' + child;
			formData.category = selectedParent.value.name;
      formData.subcategory = child;
		}
		showCategory.value = false;
	}
}

const accountList = ref<{name: string; value: string}[]>([{ name: '不指定账户', value: '' }]);

// 加载账户列表供用户选择
async function loadAccounts() {
  const ledgerId = originalBill.value?.ledger_id || ledgerStore.currentId;
  if (!userStore.isLoggedIn || !ledgerId) return;
  try {
    accountList.value = [{ name: '不指定账户', value: '' }, ...(await getAccounts(ledgerId)).map(a => ({ name: a.name, value: a.name }))];
    if (formData.account && !accountList.value.some(a => a.name === formData.account)) accountList.value.push({ name: formData.account, value: formData.account });
  } catch { uni.showToast({ title: '账户加载失败，请稍后重试', icon: 'none' }); }
}

// 切换支出/收入类型时，清空已选的分类
function switchType(type: 'expense' | 'income') {
	formData.type = type;
	selectedCategory.value = '';
	formData.category = '';
  formData.subcategory = '';
}

// 用户从 picker 中选择了账户
function onAccountConfirm(e: any) {
	formData.account = e.value[0]?.value || '';
	showAccount.value = false;
}

// 用户选择了日期
function handleVoiceInput() {
  // #ifdef MP-WEIXIN
  noteFocused.value = true;
  uni.showToast({ title: keyboardVoiceHint(), icon: 'none', duration: 3000 });
  // #endif
  // #ifndef MP-WEIXIN
  toggleVoice();
  // #endif
}

function onDateChange(e: any) {
	formData.date = (e.detail.value || '').slice(0, 10);
}

// 保存账单：先校验金额/分类/账户是否已填写，再保存或更新
async function saveBill() {
  if (loading.value || loadError.value || saving.value || voiceBusy.value) return;
  cancelVoice();
	if (!Number.isFinite(Number(formData.amount)) || Number(formData.amount) <= 0 || Number(formData.amount) > 100000000) {
		uni.showToast({ title: '请输入金额', icon: 'none' });
		return;
	}
	if (!formData.category) {
		uni.showToast({ title: '请选择分类', icon: 'none' });
		return;
	}
	if (!userStore.isLoggedIn || !(originalBill.value?.ledger_id || ledgerStore.currentId)) {
		uni.showToast({ title: '请先登录', icon: 'none' });
		return;
	}

	const billData = {
		ledger_id: originalBill.value?.ledger_id || ledgerStore.currentId,
		type: formData.type,
		amount: parseFloat(parseFloat(formData.amount).toFixed(2)),
		category: formData.category,
		subcategory: formData.subcategory || null,
		account: formData.account || null,
		note: formData.note.trim() || null,
		bill_date: formData.date,
	};

  saving.value = true;
	try {
		if (editId.value && originalBill.value) {
      // 只发送改动的字段，避免无意重算已经结算的 AA 分摊。
      const changes: Partial<ParsedBill> = {};
      for (const key of ['type', 'amount', 'category', 'subcategory', 'account', 'note', 'bill_date'] as const) {
        if (billData[key] !== originalBill.value[key]) (changes as any)[key] = billData[key];
      }
      if (Object.keys(changes).length) billStore.prepend(await updateBillApi(editId.value, changes));
		} else {
			const created = await createBillApi(billData);
			billStore.prepend(created);
		}
		uni.showToast({ title: editId.value ? '更新成功' : '保存成功', icon: 'success' });
		setTimeout(() => uni.navigateBack(), 800);
	} catch (e: any) {
		uni.showToast({ title: e?.message || '保存失败', icon: 'none' });
	} finally { saving.value = false; }
}

// 编辑时从云端读取，不能再从已废弃的本地账单缓存回填。
onLoad(async (query) => {
  if (!query?.id) return;
  editId.value = Number(query.id);
  if (!Number.isSafeInteger(editId.value) || editId.value <= 0) { loadError.value = '账单编号无效'; return; }
  loading.value = true;
  try {
    const bill = await getBill(editId.value);
    originalBill.value = bill;
    Object.assign(formData, { type: bill.type, amount: String(bill.amount), category: bill.category, subcategory: bill.subcategory || '',
      account: bill.account || '', date: bill.bill_date, note: bill.note || '' });
    selectedCategory.value = [bill.category, bill.subcategory].filter(Boolean).join(' › ');
    await Promise.all([loadAccounts(), loadCategories()]);
  } catch (error) { loadError.value = error instanceof Error ? error.message : '无法读取账单'; }
  finally { loading.value = false; }
});
onShow(async () => {
  if (editId.value) return;
  if (!ledgerStore.currentId && userStore.isLoggedIn) {
    try { await ledgerStore.fetchLedgers(); } catch { loadError.value = '账本加载失败，请重新进入'; return; }
  }
  await Promise.all([loadAccounts(), loadCategories()]);
});
</script>

<style lang="scss" scoped>
.page-add { min-height: 100vh; padding: 24rpx 28rpx 80rpx; box-sizing: border-box; }
.page-heading { display: flex; margin-bottom: 22rpx; flex-direction: column; }
.heading-title { color: var(--color-text); font-size: 40rpx; font-weight: 600; }
.heading-subtitle { margin-top: 6rpx; color: var(--color-text-secondary); font-size: 22rpx; }
.form-section { padding: 28rpx; border-radius: var(--radius-lg); background: var(--color-surface); box-shadow: var(--shadow-sm); }
.type-switch {
	display: grid; grid-template-columns: 1fr 1fr; gap: 8rpx; width: 280rpx; margin: 0 auto 34rpx;
	padding: 6rpx; border-radius: 22rpx; background: var(--color-surface-muted);
}
.type-btn {
	height: var(--button-height-md); margin: 0; padding: 0; border: 0; border-radius: 20rpx; color: var(--color-text-secondary);
	background: transparent; font-size: var(--button-font-md); font-weight: 600; line-height: var(--button-height-md); text-align: center;
}
.type-btn:first-child.active { color: var(--color-danger); background: #fff0ef; }
.type-btn:last-child.active { color: #248c41; background: #eaf8ee; }
.amount-input {
	display: flex; align-items: center; justify-content: center; min-height: 140rpx; margin-bottom: 28rpx;
	border-bottom: 1rpx solid var(--color-border-muted);
}
.currency { margin-right: 10rpx; color: var(--color-text); font-size: 44rpx; font-weight: 700; }
.amount-field { width: 400rpx; height: 96rpx; color: var(--color-danger); font-family: var(--font-mono); font-size: 60rpx; font-weight: 700; text-align: center; }
.amount-input.income .amount-field { color: var(--color-success); }
.form-list { overflow: hidden; }
.form-item {
	display: flex; align-items: center; min-height: 86rpx; padding: 0 8rpx;
	border-bottom: 1rpx solid var(--color-border-muted);
}
.form-label { width: 116rpx; color: var(--color-text-secondary); font-size: 25rpx; }
.form-value { flex: 1; overflow: hidden; color: var(--color-text); font-size: 26rpx; text-align: right; text-overflow: ellipsis; white-space: nowrap; }
.note-input { flex: 1; color: var(--color-text); font-size: 26rpx; text-align: right; }
.arrow { margin-left: 10rpx; color: var(--color-primary); font-size: 28rpx; }
.btn-save { margin-top: 26rpx; }
.save-button { width: 100% !important; height: var(--button-height-lg) !important; border: 0 !important; border-radius: var(--radius-pill) !important; color: #fff !important; background: var(--color-primary) !important; box-shadow: 0 16rpx 32rpx rgba(var(--color-primary-rgb), .20) !important; font-size: var(--button-font-lg) !important; font-weight: 600; line-height: var(--button-height-lg) !important; }

.cat-mask { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,.45); z-index: 999; display: flex; align-items: flex-end; }
.cat-popup { width: 100%; max-height: 70vh; background: #fff; border-radius: 28rpx 28rpx 0 0; display: flex; flex-direction: column; }
.cat-header { display: flex; align-items: center; justify-content: space-between; padding: 26rpx 30rpx; border-bottom: 1rpx solid #f0f0f0; }
.cat-title { font-size: 30rpx; font-weight: 600; color: #333; }
.cat-close { font-size: 32rpx; color: #999; padding: 4rpx 8rpx; }
.cat-list { max-height: 56vh; }
.cat-item { display: flex; align-items: center; min-height: 86rpx; padding: 0 30rpx; border-bottom: 1rpx solid #f5f5f5; }
.cat-item:active { background: #f9f9f9; }
.cat-item text { font-size: 27rpx; color: #333; }
.load-error { padding: 22rpx; color: var(--color-danger); }
.voice-section { margin-top: 22rpx; padding: 22rpx; border-radius: var(--radius-lg); background: var(--color-surface); box-shadow: var(--shadow-sm); }
.voice-button { height: var(--button-height-md); border: 0; border-radius: var(--radius-pill); color: var(--color-primary); background: var(--color-primary-soft); font-size: var(--button-font-md); font-weight: 600; line-height: var(--button-height-md); }
.voice-section text { display: block; margin-top: 12rpx; font-size: 22rpx; color: var(--color-text-secondary); }
</style>

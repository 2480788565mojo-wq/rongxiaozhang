<template>
  <view class="page">
    <text class="title">导入 Excel / CSV 账单</text>
    <text class="hint">导入到：{{ targetLedgerName || ledgerStore.current?.name || '请先登录并选择账本' }}</text>
    <view class="card instructions">
      <text>支持 .xlsx / .xls / .csv，最大 20MB，每次最多 10000 条账单。</text>
      <text>自动识别常见账单格式，也可选择工作表、调整列对应。无需先改成固定模板。</text>
      <text>导入前请核对日期、收支和金额；公式请先粘贴为数值。</text>
    </view>
    <button class="primary" :disabled="reading || saving" :loading="reading" @click="chooseFile">{{ filename ? '重新选择账单文件' : '选择账单文件' }}</button>
    <text class="hint">微信中请先将文件发送到聊天或文件传输助手，再从聊天文件中选择。</text>
    <text v-if="reading" class="hint">正在读取和转换表格，请稍候…</text>
    <view v-if="error" class="error card">{{ error }}</view>

    <view v-if="inspection" class="card file-card">
      <text class="filename">{{ filename }}</text>
      <picker class="sheet-picker" :range="inspection.sheetNames" :value="inspection.sheetNames.indexOf(sheetName)" :disabled="reading || saving || sessionStarted" @change="changeSheet">
        <view class="picker-value">工作表：{{ sheetName }} {{ sessionStarted ? '' : '›' }}</view>
      </picker>
      <text class="hint">{{ inspection.warning }}</text>
      <button size="mini" class="edit-mapping" :disabled="reading || saving || sessionStarted" @click="mappingOpen = !mappingOpen">{{ mappingOpen ? '收起列对应' : '调整列对应' }}</button>
      <text v-if="sessionStarted" class="hint">已开始保存，列对应已锁定。暂停后可在本页继续导入。</text>
    </view>

    <view v-if="mappingOpen && inspection" class="card mapping-card">
      <text class="filename">核对列对应</text>
      <text class="hint">选择每项来自表格的哪一列。列名后附有内容示例；没有的可选项选“不使用”。</text>
      <view class="mapping-row"><text>表头在第几行（无表头填 0）</text><input class="header-row" type="number" :value="headerInput" :disabled="reading || sessionStarted" @input="setHeaderInput" /></view>
      <button size="mini" :disabled="reading || sessionStarted" @click="detectHeader">按此表头重新识别</button>
      <view class="mapping-row"><text>账单从第几行开始</text><input class="start-row" type="number" :value="startInput" :disabled="reading || sessionStarted" @input="setStartInput" /></view>
      <text class="field-label">如何区分收入和支出</text>
      <picker class="amount-mode" :range="modeLabels" :value="modeIndex" :disabled="reading || sessionStarted" @change="changeMode"><view class="picker-value">{{ modeLabels[modeIndex] }} ›</view></picker>
      <view v-for="field in fields" :key="field.key" class="field">
        <text class="field-label">{{ field.label }}</text>
        <picker :class="'column-' + field.key" :range="columnLabels" :value="columnIndex(field.key)" :disabled="reading || sessionStarted" @change="changeColumn(field.key, $event)">
          <view class="picker-value">{{ columnLabels[columnIndex(field.key)] }} ›</view>
        </picker>
      </view>
      <button class="primary apply-mapping" :disabled="reading || saving || sessionStarted" @click="applyMapping">按此对应生成预览</button>
    </view>

    <view v-if="rows.length" class="card preview-card">
      <text class="filename">账单预览</text>
      <text class="hint">共 {{ rows.length }} 行，有效 {{ summary.valid }} 行，待修正 {{ summary.errors }} 行，已跳过 {{ summary.skipped }} 行，已导入 {{ summary.saved }} 笔。</text>
      <text class="hint">表内相同内容 {{ summary.duplicates }} 行，默认不勾选。请勿重复导入已保存的文件。</text>
      <text v-if="mappingDirty" class="warning hint">列对应已调整，请重新生成预览后再导入。</text>
      <view class="selection-actions">
        <button size="mini" :disabled="saving || reading" @click="selectValid">选择有效且不重复的行</button>
        <button size="mini" :disabled="saving || reading" @click="clearSelection">清空选择</button>
      </view>
      <text class="hint">本次选择 {{ summary.selected }} 笔：支出 ¥{{ (summary.expense / 100).toFixed(2) }}，收入 ¥{{ (summary.income / 100).toFixed(2) }}</text>
      <button class="primary confirm-import" :loading="saving" :disabled="saving || reading || mappingDirty || !summary.selected" @click="confirmImport">{{ saving ? '正在导入 ' + progressDone + ' / ' + progressTotal : '确认导入 ' + summary.selected + ' 笔' }}</button>
      <view v-if="saving" class="progress-box">
        <progress :percent="progressPercent" stroke-width="5" activeColor="#4A90E2" />
        <text class="hint">{{ saveMode === 'single' ? '当前服务逐笔保存，速度较慢，请留在本页。' : '正在分批保存，请留在本页。' }}</text>
        <button class="pause-import" size="mini" :disabled="pauseRequested" @click="pauseRequested = true">{{ pauseRequested ? '当前一批完成后暂停…' : '暂停导入' }}</button>
      </view>
      <text v-if="resultMessage" class="result">{{ resultMessage }}</text>
      <button v-if="summary.saved && !saving" @click="openBills">查看账单</button>
      <view class="pagination">
        <button size="mini" class="prev-page" :disabled="page <= 1" @click="page--">上一页</button>
        <picker :range="pageLabels" :value="page - 1" @change="changePage"><text>第 {{ page }} / {{ pageCount }} 页 ▾</text></picker>
        <button size="mini" class="next-page" :disabled="page >= pageCount" @click="page++">下一页</button>
          </view>
</view>
      <text class="hint">每页显示 50 行，翻页保留勾选。可点击页码跳转。</text>
      <checkbox-group :key="page" @change="changeSelection">
        <label v-for="row in visibleRows" :key="row.rowNumber" class="preview-row">
          <checkbox :value="String(row.rowNumber)" :checked="row.selected" :disabled="saving || reading || !row.bill || row.saved" color="#4A90E2" />
          <view class="row-content">
            <text>第 {{ row.rowNumber }} 行{{ row.saved ? ' · 已导入' : row.skipped ? ' · 已跳过' : '' }}</text>
            <template v-if="row.bill">
              <text>{{ row.bill.bill_date }} · {{ row.bill.type === 'expense' ? '支出' : '收入' }} ¥{{ row.bill.amount.toFixed(2) }}</text>
              <text>{{ row.bill.category }}{{ row.bill.subcategory ? ' / ' + row.bill.subcategory : '' }} · {{ row.bill.account || '未设置账户' }}</text>
              <text v-if="row.bill.note">{{ row.bill.note }}</text>
              <text v-if="row.duplicate" class="warning">与表内其他行内容相同，请核对</text>
            </template>
            <text v-else :class="row.skipped ? 'hint' : 'error'">{{ row.error }}</text>
          </view>
        </label>
      </checkbox-group>
  </view>
</template>

<script setup lang="ts">
import { computed, ref, shallowRef, triggerRef } from 'vue';
import { onShow, onUnload } from '@dcloudio/uni-app';
import { readExcelWorkbook, inspectExcelSheet, convertExcelSheet, MAX_FILE_BYTES,
  type ImportRow, type ExcelWorkbook, type SheetInspection, type ColumnMapping, type ImportField, type AmountMode } from './excel-import';
import { makeImportKey, saveImportRows, type ImportSaveRow } from './import-runner';
import { useLedgerStore } from '@/stores/ledger';
import { useBillStore } from '@/stores/bill';
import { useUserStore } from '@/stores/user';
const ledgerStore = useLedgerStore(); const billStore = useBillStore(); const userStore = useUserStore();
// 全量表格不做深度响应；只把当前页 50 行交给微信视图层，保存每批完成后再刷新。
const rows = shallowRef<(ImportRow & ImportSaveRow)[]>([]);
const inspection = shallowRef<SheetInspection | null>(null);
const mapping = ref<ColumnMapping>({ headerRow: -1, startRow: 1, columns: {}, amountMode: 'unknown' });
const filename = ref(''); const sheetName = ref(''); const error = ref('');
const reading = ref(false); const saving = ref(false); const resultMessage = ref('');
const targetLedgerName = ref(''); const mappingOpen = ref(false); const mappingDirty = ref(false);
const headerInput = ref('0'); const startInput = ref('1'); const sessionStarted = ref(false);
const page = ref(1); const pauseRequested = ref(false); const progressDone = ref(0); const progressTotal = ref(0);
const saveMode = ref<'batch' | 'single'>('batch');
let workbook: ExcelWorkbook | null = null;
let targetLedgerId = 0; let targetToken = ''; let unloaded = false;
const fields: { key: ImportField; label: string }[] = [
  { key: 'bill_date', label: '日期（必选）' }, { key: 'type', label: '收入 / 支出类型' },
  { key: 'amount', label: '金额' }, { key: 'income', label: '收入金额（收支分列时）' }, { key: 'expense', label: '支出金额（收支分列时）' },
  { key: 'category', label: '分类（可选）' }, { key: 'subcategory', label: '子分类（可选）' },
  { key: 'account', label: '账户（可选）' }, { key: 'note', label: '备注（可选）' }, { key: 'status', label: '交易状态（可选）' },
];
const modes: AmountMode[] = ['type', 'signed', 'split', 'expense', 'income', 'unknown'];
const modeLabels = ['根据收入 / 支出类型列', '正金额为收入，负金额为支出', '收入、支出分别在两列', '全部记为支出', '全部记为收入', '尚未确定，请选择'];
const modeIndex = computed(() => modes.indexOf(mapping.value.amountMode));
const columnLabels = computed(() => ['不使用', ...(inspection.value?.columnOptions.map(column => column.label + (column.samples.length ? '：' + column.samples.join(' / ').slice(0, 50) : '')) || [])]);
const summary = computed(() => {
  const value = { valid: 0, errors: 0, skipped: 0, saved: 0, selected: 0, duplicates: 0, income: 0, expense: 0 };
  for (const row of rows.value) {
    if (row.bill) value.valid++; else if (row.skipped) value.skipped++; else value.errors++;
    if (row.duplicate) value.duplicates++;
    if (row.saved) value.saved++;
    if (row.bill && row.selected && !row.saved) { value.selected++; value[row.bill.type] += Math.round(row.bill.amount * 100); }
  }
  return value;
});
const pageCount = computed(() => Math.max(1, Math.ceil(rows.value.length / 50)));
const pageLabels = computed(() => Array.from({ length: pageCount.value }, (_, i) => '第 ' + (i + 1) + ' 页'));
const visibleRows = computed(() => rows.value.slice((page.value - 1) * 50, page.value * 50));
const progressPercent = computed(() => progressTotal.value ? Math.round(progressDone.value / progressTotal.value * 100) : 0);
const identityChanged = () => targetLedgerId !== ledgerStore.currentId || !userStore.isLoggedIn || targetToken !== userStore.token;
onShow(async () => {
  if (!userStore.isLoggedIn || ledgerStore.currentId) return;
  try { await ledgerStore.fetchLedgers(); } catch { error.value = '账本加载失败，请重新进入'; }
});
onUnload(() => { unloaded = true; pauseRequested.value = true; workbook = null; });
function openBills() { uni.switchTab({ url: '/pages/bills/index' }); }
function selectValid() {
  if (saving.value || reading.value) return;
  rows.value.forEach(row => { row.selected = Boolean(row.bill && !row.duplicate && !row.saved); }); triggerRef(rows);
}
function clearSelection() {
  if (saving.value || reading.value) return;
  rows.value.forEach(row => { row.selected = false; }); triggerRef(rows);
}
function changeSelection(event: any) {
  if (saving.value || reading.value) return;
  const selected = new Set(event.detail.value as string[]);
  for (const row of visibleRows.value) row.selected = Boolean(row.bill && !row.saved && selected.has(String(row.rowNumber)));
  triggerRef(rows);
}
function changePage(event: any) { page.value = Math.min(pageCount.value, Math.max(1, Number(event.detail.value) + 1)); }
function columnIndex(field: ImportField) { return (inspection.value?.columnOptions.findIndex(column => column.index === mapping.value.columns[field]) ?? -1) + 1; }
function changeColumn(field: ImportField, event: any) {
  if (sessionStarted.value || reading.value) return;
  const column = inspection.value?.columnOptions[Number(event.detail.value) - 1];
  if (column) mapping.value.columns[field] = column.index; else delete mapping.value.columns[field];
  mappingDirty.value = true;
}
function changeMode(event: any) {
  if (sessionStarted.value || reading.value) return;
  mapping.value.amountMode = modes[Number(event.detail.value)] || 'unknown'; mappingDirty.value = true;
}
function setHeaderInput(event: any) { headerInput.value = String(event.detail.value); mappingDirty.value = true; }
function setStartInput(event: any) { startInput.value = String(event.detail.value); mappingDirty.value = true; }
function useInspection(next: SheetInspection) {
  inspection.value = next; sheetName.value = next.sheetName;
  mapping.value = { ...next.mapping, columns: { ...next.mapping.columns } };
  headerInput.value = String(next.mapping.headerRow + 1); startInput.value = String(next.mapping.startRow);
  mappingOpen.value = next.needsMapping; mappingDirty.value = true;
}
function detectHeader() {
  if (!workbook || reading.value || sessionStarted.value) return;
  try {
    if (!/^\d+$/.test(headerInput.value)) throw new Error('请填写表头行号，无表头填 0');
    useInspection(inspectExcelSheet(workbook, sheetName.value, Number(headerInput.value) - 1)); mappingOpen.value = true; error.value = '';
  } catch (e) { error.value = message(e); }
}
async function changeSheet(event: any) {
  if (!workbook || reading.value || saving.value || sessionStarted.value) return;
  const name = inspection.value?.sheetNames[Number(event.detail.value)]; if (!name) return;
  rows.value = []; resultMessage.value = ''; error.value = '';
  try { useInspection(inspectExcelSheet(workbook, name)); if (!inspection.value?.needsMapping) await applyMapping(); }
  catch (e) { error.value = message(e); }
}
function message(error: unknown) { return error instanceof Error ? error.message : '读取失败，请重试'; }
async function buildPreview() {
  if (!workbook) return;
  if (!/^\d+$/.test(headerInput.value) || !/^[1-9]\d*$/.test(startInput.value)) throw new Error('请填写正确的表头行和数据起始行');
  const chosen: ColumnMapping = { ...mapping.value, headerRow: Number(headerInput.value) - 1, startRow: Number(startInput.value), columns: { ...mapping.value.columns } };
  const result = await convertExcelSheet(workbook, sheetName.value, chosen);
  if (unloaded) return;
  const sessionId = Array.from({ length: 32 }, () => Math.floor(Math.random() * 16).toString(16)).join('');
  rows.value = result.rows.map(row => ({ ...row, importKey: makeImportKey(sessionId, row.rowNumber), selected: Boolean(row.bill && !row.duplicate), saved: false }));
  page.value = 1; mappingDirty.value = false; mappingOpen.value = false; resultMessage.value = '';
}
async function applyMapping() {
  if (reading.value || saving.value || sessionStarted.value) return;
  reading.value = true; error.value = '';
  try { await buildPreview(); } catch (e) { error.value = message(e); mappingOpen.value = true; }
  finally { reading.value = false; }
}
async function preview(data: ArrayBuffer, name: string) {
  workbook = readExcelWorkbook(data); filename.value = name; rows.value = []; resultMessage.value = ''; sessionStarted.value = false;
  targetLedgerId = ledgerStore.currentId; targetLedgerName.value = ledgerStore.current?.name || '当前账本'; targetToken = userStore.token;
  useInspection(inspectExcelSheet(workbook));
  if (!inspection.value?.needsMapping) await buildPreview();
}
async function chooseFile() {
  if (reading.value || saving.value) return;
  if (!userStore.isLoggedIn || !ledgerStore.currentId) { error.value = '请先登录并选择账本'; return; }
  if (sessionStarted.value) {
    const answer = await uni.showModal({ title: '开始新的导入', content: '当前文件已开始保存。继续请用本页的确认导入；重新选文件会开始新的导入，重复选择可能造成重复账单。确定重新选择？', confirmText: '重新选择' });
    if (!answer.confirm || unloaded) return;
  }
  // 一旦开始选择新文件，旧预览立即失效，避免新文件读取失败时误把旧文件再次提交。
  rows.value = []; inspection.value = null; workbook = null; filename.value = ''; sheetName.value = '';
  mappingDirty.value = false; resultMessage.value = ''; error.value = '';
  error.value = '';
  // #ifdef MP-WEIXIN
  reading.value = true;
  const wxApi = (globalThis as any).wx;
  wxApi.chooseMessageFile({ count: 1, type: 'file', extension: ['xlsx', 'xls', 'csv'],
    success: (result: any) => {
      const file = result.tempFiles?.[0];
      if (!file || !/\.(xlsx?|csv)$/i.test(file.name) || file.size > MAX_FILE_BYTES) { error.value = '请选择 20MB 以内的 .xlsx、.xls 或 .csv 文件'; reading.value = false; return; }
      wxApi.getFileSystemManager().readFile({ filePath: file.path,
        success: async (result: any) => {
          try { if (!unloaded) await preview(result.data, file.name); }
          catch (e) { error.value = message(e); } finally { reading.value = false; }
        },
        fail: () => { error.value = '文件读取失败，请重新选择'; reading.value = false; },
      });
    },
    fail: (e: any) => { if (!String(e.errMsg).includes('cancel')) error.value = '无法选择文件，请重试'; reading.value = false; },
  });
  return;
  // #endif
  // #ifdef H5
  const picker = document.createElement('input'); picker.type = 'file'; picker.accept = '.xlsx,.xls,.csv';
  picker.onchange = async () => {
    const file = picker.files?.[0]; if (!file) return; reading.value = true;
    try {
      if (!/\.(xlsx?|csv)$/i.test(file.name) || file.size > MAX_FILE_BYTES) throw new Error('请选择 20MB 以内的 .xlsx、.xls 或 .csv 文件');
      const data = await file.arrayBuffer(); if (!unloaded) await preview(data, file.name);
    } catch (e) { error.value = message(e); } finally { reading.value = false; }
  };
  picker.click();
  // #endif
}
async function confirmImport() {
  if (saving.value || reading.value || mappingDirty.value || !summary.value.selected) return;
  if (identityChanged()) { error.value = '账本或登录状态已变化，请重新选择文件'; return; }
  saving.value = true; error.value = ''; resultMessage.value = ''; pauseRequested.value = false;
  progressDone.value = 0; progressTotal.value = summary.value.selected;
  try {
    const answer = await uni.showModal({ title: '确认导入', content: '将 ' + summary.value.selected + ' 笔账单导入“' + targetLedgerName.value + '”，请确认已核对金额和日期。', confirmText: '导入' });
    if (!answer.confirm || unloaded) return;
    if (identityChanged()) throw new Error('账本或登录状态已变化，请重新选择文件');
    sessionStarted.value = true; mappingOpen.value = false;
    const result = await saveImportRows(rows.value, targetLedgerId, {
      shouldStop: () => unloaded || pauseRequested.value || identityChanged(),
      onProgress: (completed, total, mode) => { progressDone.value = completed; progressTotal.value = total; saveMode.value = mode; triggerRef(rows); },
    });
    resultMessage.value = (result.paused ? '已暂停，' : '') + '已导入 ' + summary.value.saved + ' 笔账单。' + (result.paused ? '留在本页可继续导入剩余记录。' : '返回账单页可按对应月份查看。');
    if (identityChanged()) error.value = '账本或登录状态已变化，已停止后续导入';
  } catch (e) {
    triggerRef(rows);
    error.value = '已导入 ' + summary.value.saved + ' 笔，其余尚未完成：' + message(e) + '。可在本页重试，已导入的记录不会重复保存。';
  } finally {
    triggerRef(rows); saving.value = false;
    if (summary.value.saved) billStore.clear();
  }
}
</script>

<style scoped>
.page { padding: 28rpx 28rpx 80rpx; }
.title { display: block; font-size: 38rpx; font-weight: 600; }
.card { margin-top: 22rpx; padding: 22rpx; border-radius: var(--radius-lg); background: var(--color-surface); box-shadow: var(--shadow-sm); }
.instructions text, .hint { display: block; margin: 12rpx 0; font-size: 24rpx; line-height: 1.7; color: var(--color-text-secondary); }
.primary { width: 100%; height: var(--button-height-lg); margin-top: 22rpx; border: 0; background: var(--color-primary); color: white; font-size: var(--button-font-lg); font-weight: 600; border-radius: var(--radius-pill); line-height: var(--button-height-lg); }
.filename { display: block; word-break: break-all; font-size: 27rpx; font-weight: 600; }
.selection-actions, .pagination { display: flex; align-items: center; gap: 10rpx; margin: 20rpx 0; }
.selection-actions button { height: var(--button-height-sm); flex: 1; margin: 0; padding: 0 10rpx; border: 0; border-radius: 16rpx; font-size: var(--button-font-sm); font-weight: 600; line-height: var(--button-height-sm); }
.pagination { justify-content: space-between; font-size: var(--button-font-sm); }
.pagination button { height: var(--button-height-sm); margin: 0; padding: 0 18rpx; border: 0; border-radius: var(--radius-pill); font-size: var(--button-font-sm); line-height: var(--button-height-sm); }
.preview-row { display: flex; gap: 12rpx; padding: 20rpx 0; border-bottom: 1rpx solid var(--color-border); align-items: flex-start; }
.row-content { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 8rpx; font-size: 24rpx; overflow-wrap: anywhere; }
.error { color: var(--color-danger); font-size: 24rpx; }
.warning { color: var(--color-warning); }
.result { display: block; margin: 18rpx 0; color: var(--color-success); font-size: 26rpx; }
.field-label { display: block; margin-top: 20rpx; font-size: 25rpx; }
.picker-value { padding: 18rpx 14rpx; margin: 10rpx 0; background: var(--color-bg); border: 1rpx solid var(--color-border); border-radius: 16rpx; font-size: 25rpx; overflow-wrap: anywhere; }
.mapping-row { margin: 18rpx 0; font-size: 25rpx; }
.mapping-row input { margin-top: 10rpx; padding: 14rpx; border: 1rpx solid var(--color-border); border-radius: 16rpx; }
.progress-box { margin-top: 22rpx; }
</style>

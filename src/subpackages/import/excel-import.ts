import * as XLSX from 'xlsx';
import type { ParsedBill } from '@/types';

export const MAX_IMPORT_ROWS = 10000;
export const MAX_FILE_BYTES = 20 * 1024 * 1024;
export type ImportField = 'bill_date' | 'type' | 'amount' | 'income' | 'expense' | 'category' | 'subcategory' | 'account' | 'note' | 'status';
export type AmountMode = 'type' | 'signed' | 'split' | 'expense' | 'income' | 'unknown';
export interface ColumnMapping {
  /** 表头从零计数，无表头为 -1；起始数据行与 Excel 一致，从 1 计数。 */
  headerRow: number;
  startRow: number;
  columns: Partial<Record<ImportField, number>>;
  amountMode: AmountMode;
}
export interface ExcelWorkbook { readonly book: XLSX.WorkBook }
export interface SheetInspection {
  sheetName: string;
  sheetNames: string[];
  mapping: ColumnMapping;
  columnOptions: { index: number; label: string; samples: string[] }[];
  needsMapping: boolean;
  warning: string;
}
export interface ImportRow {
  rowNumber: number;
  bill: ParsedBill | null;
  error: string;
  duplicate: boolean;
  skipped?: boolean;
}
export interface ImportPreview { sheetName: string; rows: ImportRow[] }

const aliases: Record<ImportField, string[]> = {
  bill_date: ['日期','交易日期','交易时间','交易创建时间','交易完成时间','付款时间','支付时间','记账日期','记账时间','入账日期','入账时间','账单日期','发生日期','发生时间','时间','date','datetime','bill_date','posting date','transaction date'],
  type: ['类型','收支','收/支','收支类型','收支方向','收入/支出','交易方向','借贷标志','借/贷','资金方向','type','direction'],
  amount: ['金额','金额(元)','交易金额','交易金额(元)','交易金额(人民币)','金额(人民币)','发生额','发生金额','本币金额','人民币金额','amount'],
  income: ['收入','收入金额','收入(元)','收入金额(元)','收入(+)','贷方','贷方金额','贷方发生额','存入','存入金额','credit','income'],
  expense: ['支出','支出金额','支出(元)','支出金额(元)','支出(-)','借方','借方金额','借方发生额','支取','支取金额','debit','expense'],
  category: ['分类','类别','一级分类','交易分类','交易类型','消费类别','category'],
  subcategory: ['细分','子分类','子类','二级分类','subcategory'],
  account: ['账户','账户名称','账号','支付方式','收付款方式','付款方式','资金渠道','account'],
  note: ['备注','说明','摘要','交易摘要','商品','商品说明','商品名称','用途','note','description','memo'],
  status: ['状态','交易状态','订单状态','支付状态','当前状态','status'],
};
const text = (value: unknown) => String(value ?? '').trim();
const normalize = (value: unknown) => text(value).replace(/[\s\uFEFF_（）()[\]：:/]/g, '').toLowerCase();
const aliasLookup = new Map<string, ImportField>();
for (const [field, names] of Object.entries(aliases)) for (const name of names) aliasLookup.set(normalize(name), field as ImportField);
type IndexedRow = { index: number; cells: Map<number, XLSX.CellObject> };
type SheetIndex = { rows: IndexedRow[]; maxColumn: number };
const indexCache = new WeakMap<XLSX.WorkSheet, SheetIndex>();

/** 只遍历实际存在的单元格，避免带几十万行空白格式的文件拖慢小程序。 */
function indexSheet(workbook: ExcelWorkbook, sheetName: string): SheetIndex {
  const sheet = workbook.book.Sheets[sheetName];
  if (!sheet) throw new Error('找不到所选工作表');
  const cached = indexCache.get(sheet);
  if (cached) return cached;
  const rows = new Map<number, IndexedRow>();
  let maxColumn = 0;
  for (const address of Object.keys(sheet)) {
    if (!/^[A-Z]+[1-9]\d*$/.test(address)) continue;
    const cell = sheet[address] as XLSX.CellObject;
    if (!cell || (!cell.f && !text(cell.v))) continue;
    const { r, c } = XLSX.utils.decode_cell(address);
    if (c >= 200) throw new Error('表格超过 200 列，请仅保留账单明细');
    maxColumn = Math.max(maxColumn, c);
    let row = rows.get(r);
    if (!row) { row = { index: r, cells: new Map() }; rows.set(r, row); }
    row.cells.set(c, cell);
  }
  const result = { rows: [...rows.values()].sort((a, b) => a.index - b.index), maxColumn };
  indexCache.set(sheet, result);
  return result;
}

export function readExcelWorkbook(data: ArrayBuffer): ExcelWorkbook {
  if (!data.byteLength || data.byteLength > MAX_FILE_BYTES) throw new Error('请选择 20MB 以内的非空 Excel 文件');
  let book: XLSX.WorkBook;
  try {
    // 保留公式标记用于拒绝公式；不设置 sheetRows，防止超量账单被悄悄截断。
    book = XLSX.read(data, { type: 'array', cellDates: false, cellFormula: true });
  } catch { throw new Error('无法读取表格，请确认文件未加密且格式正确'); }
  if (!book.SheetNames.length) throw new Error('文件中没有工作表');
  return { book };
}

function parseDate(value: unknown, date1904: boolean): string {
  let parts: number[];
  const raw = text(value);
  if (/^\d{8}$/.test(raw)) parts = [Number(raw.slice(0, 4)), Number(raw.slice(4, 6)), Number(raw.slice(6, 8))];
  else if (typeof value === 'number') {
    const date = XLSX.SSF.parse_date_code(value, { date1904 });
    if (!date) throw new Error('日期无效');
    parts = [date.y, date.m, date.d];
  } else {
    const match = raw.match(/^(\d{4})[-/.年](\d{1,2})[-/.月](\d{1,2})日?(?:[ T](\d{1,2}):(\d{2})(?::(\d{2})(?:\.\d{1,3})?)?(?:Z|[+-]\d{2}:?\d{2})?)?$/);
    if (match) {
      parts = match.slice(1, 4).map(Number);
      if (Number(match[4] || 0) > 23 || Number(match[5] || 0) > 59 || Number(match[6] || 0) > 59) throw new Error('日期中的时间无效');
    } else {
      const reversed = raw.match(/^(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})$/);
      if (!reversed) throw new Error('无法识别日期，请使用年-月-日或 Excel 日期');
      const [, first, second, year] = reversed.map(Number);
      if (first <= 12 && second <= 12 && first !== second) throw new Error('日期格式有歧义，请改为年-月-日');
      parts = first > 12 ? [year, second, first] : [year, first, second];
    }
  }
  const [y, m, d] = parts;
  const date = new Date(y, m - 1, d);
  if (y < 1900 || y > 2100 || date.getFullYear() !== y || date.getMonth() !== m - 1 || date.getDate() !== d) throw new Error('日期无效');
  return `${y}-${String(m).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
}

/** 先转成整数“分”，再输出元，避免小数运算引入分的误差。 */
function amountInCents(value: unknown, allowZero = false): number {
  let normalized = text(value).replace(/^[¥￥]\s*/, '').replace(/\s*(?:元|CNY|RMB)$/i, '').trim();
  if (/^\(.*\)$/.test(normalized)) normalized = `-${normalized.slice(1, -1)}`;
  if (!/^[+-]?(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d{1,2})?$/.test(normalized)) throw new Error('金额格式无效，最多两位小数');
  const negative = normalized.startsWith('-');
  const [whole, fraction = ''] = normalized.replace(/[,+-]/g, '').split('.');
  const cents = Number(whole) * 100 + Number(fraction.padEnd(2, '0'));
  if (!Number.isSafeInteger(cents) || Math.abs(cents) > 10000000000 || (!allowZero && cents === 0)) throw new Error('金额需大于 0 且不超过一亿元');
  return negative ? -cents : cents;
}
function direction(value: unknown): ParsedBill['type'] | null {
  const raw = normalize(value);
  if (['支出','expense','借','借方','debit','付款','付','转出','出账','-'].includes(raw)) return 'expense';
  if (['收入','income','贷','贷方','credit','收款','收','转入','入账','+'].includes(raw)) return 'income';
  return null;
}
function headerColumns(row: IndexedRow): ColumnMapping['columns'] {
  const columns: ColumnMapping['columns'] = {};
  // 实际账单可能恰好把“日期/金额”写在备注里，有数值或日期内容的行不能当表头。
  if ([...row.cells.values()].some(cell => isAmount(cell) || /^\d{4}[-/.年]\d{1,2}[-/.月]\d{1,2}/.test(text(cell.v)))) return columns;
  for (const [column, cell] of row.cells) {
    const field = aliasLookup.get(normalize(cell.v));
    if (!field || cell.f) continue;
    // 支付宝同时含业务“类型”和“收/支”，明确的资金方向优先。
    const priorType = text(row.cells.get(columns.type ?? -1)?.v);
    const clearerDirection = field === 'type' && normalize(priorType) === '类型' && normalize(cell.v) !== '类型';
    if (columns[field] === undefined || clearerDirection) columns[field] = column;
  }
  return columns;
}
function headerScore(columns: ColumnMapping['columns']): number {
  return (columns.bill_date !== undefined ? 4 : 0) +
    (columns.amount !== undefined ? 3 : 0) + (columns.type !== undefined ? 2 : 0) +
    (columns.income !== undefined ? 3 : 0) + (columns.expense !== undefined ? 3 : 0) +
    Object.keys(columns).length / 100;
}
function resemblesDate(cell: XLSX.CellObject | undefined, date1904: boolean): boolean {
  if (!cell || cell.f) return false;
  if (typeof cell.v === 'number' && cell.v < 20000) return false;
  try { parseDate(cell.v, date1904); return true; } catch { return false; }
}
function isAmount(cell: XLSX.CellObject | undefined): boolean {
  if (!cell || cell.f) return false;
  try { amountInCents(cell.v, true); return true; } catch { return false; }
}
function inferColumns(rows: IndexedRow[], maxColumn: number, columns: ColumnMapping['columns'], date1904: boolean): void {
  const sample = rows.filter(row => row.cells.size >= 2).slice(0, 40);
  if (!sample.length) return;
  // 多列都很像金额/日期时留空，交给用户对应，不能因为列靠前就猜中。
  const uniqueCandidate = (predicate: (cell: XLSX.CellObject | undefined) => boolean) => {
    const used = new Set(Object.values(columns));
    const candidates: number[] = [];
    for (let c = 0; c <= maxColumn; c++) {
      if (!used.has(c) && sample.filter(row => predicate(row.cells.get(c))).length / sample.length >= 0.8) candidates.push(c);
    }
    return candidates.length === 1 ? candidates[0] : undefined;
  };
  if (columns.bill_date === undefined) columns.bill_date = uniqueCandidate(cell => resemblesDate(cell, date1904));
  if (columns.type === undefined) columns.type = uniqueCandidate(cell => Boolean(direction(cell?.v)));
  if (columns.amount === undefined && columns.income === undefined && columns.expense === undefined) columns.amount = uniqueCandidate(isAmount);
  for (const key of Object.keys(columns) as ImportField[]) if (columns[key] === undefined) delete columns[key];
}
function inferMode(columns: ColumnMapping['columns'], rows: IndexedRow[]): AmountMode {
  if (columns.income !== undefined && columns.expense !== undefined) return 'split';
  if (columns.type !== undefined && columns.amount !== undefined) return 'type';
  if (columns.income !== undefined && columns.amount === undefined) return 'income';
  if (columns.expense !== undefined && columns.amount === undefined) return 'expense';
  if (columns.amount !== undefined && rows.some(row => /^[+-]/.test(text(row.cells.get(columns.amount!)?.v)) || /^\(\d/.test(text(row.cells.get(columns.amount!)?.v)))) return 'signed';
  return 'unknown';
}
function mappingProblem(mapping: ColumnMapping, maxColumn: number): string {
  if (!Number.isInteger(mapping.startRow) || mapping.startRow < 1) return '请填写正确的数据起始行';
  if (!Number.isInteger(mapping.headerRow) || mapping.headerRow < -1 || mapping.headerRow >= mapping.startRow - 1) return '表头行应在数据起始行之前';
  const columns = mapping.columns;
  const chosen = Object.values(columns).filter((value): value is number => value !== undefined);
  if (chosen.some(value => !Number.isInteger(value) || value < 0 || value > maxColumn)) return '所选列不存在，请重新对应';
  if (new Set(chosen).size !== chosen.length) return '同一列不能同时对应多个字段';
  if (columns.bill_date === undefined) return '请对应日期列';
  if (mapping.amountMode === 'unknown') return '请确认金额如何表示收入和支出';
  if (mapping.amountMode === 'split') return columns.income === undefined || columns.expense === undefined ? '请对应收入金额列和支出金额列' : '';
  const amountColumn = columns.amount ?? (mapping.amountMode === 'income' ? columns.income : mapping.amountMode === 'expense' ? columns.expense : undefined);
  if (amountColumn === undefined) return '请对应金额列';
  if (mapping.amountMode === 'type' && columns.type === undefined) return '请对应收入/支出类型列';
  return '';
}

export function inspectExcelSheet(workbook: ExcelWorkbook, sheetName = workbook.book.SheetNames[0], headerRow?: number): SheetInspection {
  const { rows, maxColumn } = indexSheet(workbook, sheetName);
  let foundRow = -1;
  let columns: ColumnMapping['columns'] = {};
  if (headerRow !== undefined) {
    if (!Number.isInteger(headerRow) || headerRow < -1) throw new Error('表头行无效');
    foundRow = headerRow;
    const row = rows.find(item => item.index === headerRow);
    if (row) columns = headerColumns(row);
  } else {
    let best = 0;
    for (const row of rows) {
      const candidate = headerColumns(row);
      const score = headerScore(candidate);
      // 单个“收入/支出”值不是表头；至少两个列名，并包含日期或金额列。
      if (Object.keys(candidate).length >= 2 && score > best && score >= 5) {
        columns = candidate; foundRow = row.index; best = score;
        // 以最早完整表头为准，不能让后面更丰富的重复表头把前半份账单截掉。
        if (candidate.bill_date !== undefined && (candidate.amount !== undefined || candidate.income !== undefined || candidate.expense !== undefined)) break;
      }
    }
  }
  let dataRows = rows.filter(row => row.index > foundRow);
  let startRow = foundRow >= 0 ? foundRow + 2 : (dataRows[0]?.index ?? 0) + 1;
  const date1904 = Boolean(workbook.book.Workbook?.WBProps?.date1904);
  if (headerRow === undefined && foundRow < 0 && dataRows.length > 1) {
    const first = dataRows[0]; const next = dataRows[1];
    // 完全陌生的列名也能作为表头呈现，用户稍后可更改起始行或手动指定表头。
    if (first.cells.size >= 2 && [...first.cells.values()].every(cell => !isAmount(cell) && !resemblesDate(cell, date1904) && !direction(cell.v)) &&
      [...next.cells.values()].some(cell => resemblesDate(cell, date1904))) {
      foundRow = first.index; startRow = first.index + 2; dataRows = dataRows.slice(1);
    }
  }
  inferColumns(dataRows, maxColumn, columns, date1904);
  const mapping: ColumnMapping = { headerRow: foundRow, startRow, columns, amountMode: inferMode(columns, dataRows) };
  const problem = mappingProblem(mapping, maxColumn);
  const headerCells = rows.find(row => row.index === foundRow)?.cells;
  const columnOptions = Array.from({ length: maxColumn + 1 }, (_, index) => ({
    index,
    label: `${XLSX.utils.encode_col(index)} · ${text(headerCells?.get(index)?.v) || '未命名列'}`,
    samples: dataRows.slice(0, 8).map(row => text(row.cells.get(index)?.v)).filter(Boolean).slice(0, 3),
  }));
  return { sheetName, sheetNames: [...workbook.book.SheetNames], mapping, columnOptions, needsMapping: Boolean(problem), warning: problem ? `${problem}，请核对列对应后再生成预览` : '已自动识别，请在导入前核对日期、收支和金额' };
}

class SkippedRow extends Error {}
function shouldSkip(row: IndexedRow, mapping: ColumnMapping): string {
  const get = (field: ImportField) => text(row.cells.get(mapping.columns[field] ?? -1)?.v);
  const rawType = get('type'); const status = get('status');
  if (/不计收支|不计入收支|不计|中性交易/.test(rawType)) return '不计收支的交易已跳过';
  if (/失败|关闭|取消|撤销|作废|待支付|等待付款|未支付|处理中|退款中|failed|closed|cancelled|pending/i.test(status)) return '未成功完成或已关闭的交易已跳过';
  const columns = headerColumns(row);
  if (Object.keys(columns).length >= 2 && headerScore(columns) >= 5) return '重复表头已跳过';
  const first = text([...row.cells.values()][0]?.v); const date = get('bill_date');
  if (/^(合计|总计|小计|本页合计|累计|汇总|统计)(?:[：:\s]|$)/.test(first) || /^(合计|总计|小计)$/.test(date)) return '汇总行已跳过';
  if (row.cells.size === 1 && /^(说明|备注|提示|注意|温馨提示|[-=]{3,})/.test(first)) return '说明行已跳过';
  return '';
}
function convertRow(row: IndexedRow, mapping: ColumnMapping, date1904: boolean, seen: Set<string>): ImportRow {
  const result: ImportRow = { rowNumber: row.index + 1, bill: null, error: '', duplicate: false };
  const value = (field: ImportField) => row.cells.get(mapping.columns[field] ?? -1)?.v;
  try {
    if ([...row.cells.values()].some(cell => cell.f)) throw new Error('含公式，请复制并粘贴为数值后导入');
    const skip = shouldSkip(row, mapping);
    if (skip) throw new SkippedRow(skip);
    let type: ParsedBill['type']; let cents: number;
    if (mapping.amountMode === 'split') {
      const income = text(value('income')) ? amountInCents(value('income'), true) : 0;
      const expense = text(value('expense')) ? amountInCents(value('expense'), true) : 0;
      if (income && expense) throw new Error('收入和支出金额同时存在，请核对后拆成两行');
      if (income < 0 || expense < 0) throw new Error('分列金额应为正数，请核对收支方向');
      if (!income && !expense) throw new Error('收入和支出金额均为空或零');
      type = income ? 'income' : 'expense'; cents = income || expense;
    } else {
      const amountColumn = mapping.columns.amount ?? (mapping.amountMode === 'income' ? mapping.columns.income : mapping.columns.expense);
      cents = amountInCents(row.cells.get(amountColumn ?? -1)?.v);
      if (mapping.amountMode === 'signed') type = cents < 0 ? 'expense' : 'income';
      else if (mapping.amountMode === 'income' || mapping.amountMode === 'expense') type = mapping.amountMode;
      else {
        const parsedType = direction(value('type'));
        if (!parsedType) throw new Error('无法确定收入或支出，请核对类型列');
        type = parsedType;
      }
      if (cents < 0 && type === 'income') throw new Error('负金额与收入方向冲突，请核对');
    }
    if (/退款|退还|退货|refunded/i.test(text(value('status'))) && type !== 'income') throw new SkippedRow('退款交易需要核对收支，已跳过原支出以免重复计账');
    const bill: ParsedBill = {
      type, amount: Math.abs(cents) / 100, bill_date: parseDate(value('bill_date'), date1904),
      category: text(value('category')) || (type === 'expense' ? '其他支出' : '其他收入'),
      subcategory: text(value('subcategory')) || null, account: text(value('account')) || null, note: text(value('note')) || null,
    };
    for (const key of ['category','subcategory','account','note'] as const) if ((bill[key]?.length || 0) > (key === 'note' ? 256 : 64)) throw new Error(`${key === 'note' ? '备注' : '分类或账户'}文字过长`);
    const fingerprint = JSON.stringify(bill);
    result.bill = bill; result.duplicate = seen.has(fingerprint); seen.add(fingerprint);
  } catch (error) {
    result.error = error instanceof Error ? error.message : '此行格式错误';
    if (error instanceof SkippedRow) result.skipped = true;
  }
  return result;
}
function prepareConversion(workbook: ExcelWorkbook, sheetName: string, mapping: ColumnMapping) {
  const index = indexSheet(workbook, sheetName);
  const problem = mappingProblem(mapping, index.maxColumn);
  if (problem) throw new Error(`${problem}，请检查列对应`);
  const rows = index.rows.filter(row => row.index >= mapping.startRow - 1);
  if (!rows.length) throw new Error('表格中没有账单明细');
  for (const row of rows) {
    const repeated = headerColumns(row);
    if (Object.keys(repeated).length < 2 || headerScore(repeated) < 5) continue;
    if ((Object.keys(repeated) as ImportField[]).some(field => mapping.columns[field] !== undefined && mapping.columns[field] !== repeated[field])) {
      throw new Error(`第 ${row.index + 1} 行出现不同列顺序的表头，请把不同结构的明细分到不同工作表再导入`);
    }
  }
  return { rows, date1904: Boolean(workbook.book.Workbook?.WBProps?.date1904) };
}
function appendRow(rows: ImportRow[], row: ImportRow, count: { value: number }): void {
  // 说明/汇总不占账单名额；错误账单仍计入上限，禁止只读取前一万条。
  if (!row.skipped && ++count.value > MAX_IMPORT_ROWS) throw new Error('每次最多导入 10000 条账单，请拆分文件后重试；本次尚未导入');
  rows.push(row);
}
export async function convertExcelSheet(workbook: ExcelWorkbook, sheetName: string, mapping: ColumnMapping): Promise<ImportPreview> {
  const prepared = prepareConversion(workbook, sheetName, mapping);
  const rows: ImportRow[] = []; const seen = new Set<string>(); const count = { value: 0 };
  for (let i = 0; i < prepared.rows.length; i++) {
    appendRow(rows, convertRow(prepared.rows[i], mapping, prepared.date1904, seen), count);
    // 每 200 行把控制权还给小程序，使加载提示和页面操作保持响应。
    if ((i + 1) % 200 === 0) await new Promise<void>(resolve => setTimeout(resolve, 0));
  }
  return { sheetName, rows };
}
/** 兼容旧调用；新页面使用 inspect + convert，让用户能够调整列对应。 */
export function parseExcelBills(data: ArrayBuffer): ImportPreview {
  const workbook = readExcelWorkbook(data);
  const inspection = inspectExcelSheet(workbook);
  if (inspection.needsMapping) throw new Error(inspection.warning);
  const prepared = prepareConversion(workbook, inspection.sheetName, inspection.mapping);
  const rows: ImportRow[] = []; const seen = new Set<string>(); const count = { value: 0 };
  for (const row of prepared.rows) appendRow(rows, convertRow(row, inspection.mapping, prepared.date1904, seen), count);
  return { sheetName: inspection.sheetName, rows };
}

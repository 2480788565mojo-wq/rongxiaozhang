import { createBill, importBills, type BillImportItem } from '@/api/bills';
import { ApiError } from '@/api/client';
import type { ParsedBill } from '@/types';

export interface ImportSaveRow {
  rowNumber: number;
  bill: ParsedBill | null;
  importKey: string;
  selected: boolean;
  saved: boolean;
}
export interface SaveOptions {
  shouldStop?: () => boolean;
  onProgress?: (completed: number, total: number, mode: 'batch' | 'single') => void;
}
export const IMPORT_BATCH_SIZE = 100;

// 旧服务端仅允许三位尾号；把行号分组编码进批次编号，兼容大表格且重试不换键。
export function makeImportKey(sessionId: string, rowNumber: number): string {
  if (!/^[a-f0-9]{32}$/.test(sessionId) || !Number.isSafeInteger(rowNumber) || rowNumber < 1 || rowNumber > 0xffffffff) {
    throw new Error('导入编号无效，请重新选择文件');
  }
  const group = Math.floor((rowNumber - 1) / 999).toString(16).padStart(8, '0');
  return `excel:${sessionId.slice(0, 24)}${group}:${(rowNumber - 1) % 999 + 1}`;
}

function confirmSingleBill(response: unknown, bill: ParsedBill, ledgerId: number): void {
  const returned = response as Record<string, unknown> | null | undefined;
  if (!returned || typeof returned !== 'object' || !Number.isSafeInteger(returned.id) || Number(returned.id) <= 0) {
    throw new Error('服务器未确认这笔账单，请用原编号重试');
  }
  const expected: Record<string, unknown> = { ...bill, ledger_id: ledgerId };
  const textFields = new Set(['category', 'subcategory', 'account', 'note']);
  const normalizedText = (value: unknown) => typeof value === 'string' ? value.trim() || null : value ?? null;
  // 旧接口可只返回编号；若附带账单内容，必须核对，防止同键返回旧内容却显示成功。
  for (const field of ['ledger_id', 'type', 'amount', 'category', 'subcategory', 'account', 'note', 'bill_date']) {
    if (!Object.prototype.hasOwnProperty.call(returned, field)) continue;
    const actual = textFields.has(field) ? normalizedText(returned[field]) : returned[field];
    const submitted = textFields.has(field) ? normalizedText(expected[field]) : expected[field];
    if (actual !== submitted) throw new Error('服务器返回的账单内容与本次导入不一致，请核对账单');
  }
}

export async function saveImportRows(rows: ImportSaveRow[], ledgerId: number, options: SaveOptions = {}) {
  const pending = rows.filter(row => row.bill && row.selected && !row.saved);
  let completed = 0;
  let mode: 'batch' | 'single' = 'batch';
  const progress = () => options.onProgress?.(completed, pending.length, mode);
  try {
    for (let offset = 0; offset < pending.length; offset += IMPORT_BATCH_SIZE) {
      if (options.shouldStop?.()) return { completed, paused: true, mode };
      const batch = pending.slice(offset, offset + IMPORT_BATCH_SIZE);
      const items: BillImportItem[] = batch.map(row => ({ ...row.bill!, import_key: row.importKey }));
      if (mode === 'batch') {
        try {
          const response = await importBills(ledgerId, items);
          const returned = response?.items;
          const byKey = new Map(returned?.map(item => [item.import_key, item]));
          if (!returned || returned.length !== batch.length || byKey.size !== batch.length ||
            batch.some(row => !Number.isSafeInteger(byKey.get(row.importKey)?.bill_id) || Number(byKey.get(row.importKey)?.bill_id) <= 0)) {
            throw new Error('服务器未完整确认这批账单，请用原编号重试');
          }
          batch.forEach(row => { row.saved = true; row.selected = false; });
          completed += batch.length;
          progress();
          continue;
        } catch (error) {
          // 仅缺少新路由才兼容回退。超时可能已入库，必须保留同键等待用户重试。
          if (!(error instanceof ApiError) || ![404, 405].includes(error.statusCode)) throw error;
          mode = 'single';
          progress();
        }
      }
      for (const row of batch) {
        if (options.shouldStop?.()) return { completed, paused: true, mode };
        const response = await createBill({ ...row.bill!, ledger_id: ledgerId, import_key: row.importKey });
        confirmSingleBill(response, row.bill!, ledgerId);
        row.saved = true;
        row.selected = false;
        completed += 1;
        if (completed % 10 === 0 || completed === pending.length) progress();
      }
      progress();
    }
    return { completed, paused: false, mode };
  } finally { progress(); }
}

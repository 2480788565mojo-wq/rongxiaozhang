import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError } from '@/api/client';
import { createBill, importBills } from '@/api/bills';
import { makeImportKey, saveImportRows, type ImportSaveRow } from './import-runner';

vi.mock('@/api/bills', () => ({ createBill: vi.fn(), importBills: vi.fn() }));
function records(count: number): ImportSaveRow[] {
  return Array.from({ length: count }, (_, index) => ({
    rowNumber: index + 1, selected: true, saved: false,
    importKey: makeImportKey('0123456789abcdef0123456789abcdef', index + 1),
    bill: { bill_date: '2026-09-23', type: 'expense', amount: index + 1, category: '餐饮', subcategory: null, account: null, note: null },
  }));
}
beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(importBills).mockImplementation(async (ledgerId, items) => ({ items: items.map((item, index) => ({ import_key: item.import_key, bill_id: index + 1, created: true })) }));
});
describe('大表格分批保存', () => {
  it('5000 条按每批最多100条提交，全部保存且编号不重复', async () => {
    const rows = records(5000);
    const result = await saveImportRows(rows, 1);
    expect(importBills).toHaveBeenCalledTimes(50);
    expect(vi.mocked(importBills).mock.calls.every(([, items]) => items.length <= 100)).toBe(true);
    expect(new Set(rows.map(row => row.importKey)).size).toBe(5000);
    expect(result.paused).toBe(false);
    expect(rows.every(row => row.saved && !row.selected)).toBe(true);
  });
  it('第1000行以后的编号仍兼容旧服务器的三位尾号规则', () => {
    const keys = [1, 999, 1000, 10000, 30000].map(row => makeImportKey('0123456789abcdef0123456789abcdef', row));
    expect(keys.every(key => /^excel:[0-9a-f]{32}:\d{1,3}$/.test(key))).toBe(true);
    expect(new Set(keys).size).toBe(keys.length);
  });
  it('第二批失败后仅重试未完成行并复用原编号', async () => {
    const rows = records(205);
    vi.mocked(importBills).mockRejectedValueOnce(new Error('网络中断'));
    await expect(saveImportRows(rows, 1)).rejects.toThrow('网络中断');
    expect(rows.some(row => row.saved)).toBe(false);
    const firstKeys = vi.mocked(importBills).mock.calls[0][1].map(item => item.import_key);
    vi.mocked(importBills).mockClear();
    vi.mocked(importBills).mockImplementationOnce(async (_, items) => ({ items: items.map((item, index) => ({ import_key: item.import_key, bill_id: index + 1, created: false })) }))
      .mockRejectedValueOnce(new Error('第二批中断'));
    await expect(saveImportRows(rows, 1)).rejects.toThrow('第二批中断');
    expect(rows.filter(row => row.saved)).toHaveLength(100);
    expect(vi.mocked(importBills).mock.calls[0][1].map(item => item.import_key)).toEqual(firstKeys);
    const failedKeys = vi.mocked(importBills).mock.calls[1][1].map(item => item.import_key);
    vi.mocked(importBills).mockClear();
    await saveImportRows(rows, 1);
    expect(vi.mocked(importBills).mock.calls[0][1].map(item => item.import_key)).toEqual(failedKeys);
    expect(rows.every(row => row.saved)).toBe(true);
  });
  it('暂停等待当前批保存完毕，再继续未完成部分', async () => {
    const rows = records(205); let paused = false;
    const result = await saveImportRows(rows, 1, { shouldStop: () => paused, onProgress: () => { paused = true; } });
    expect(result.paused).toBe(true);
    expect(rows.filter(row => row.saved)).toHaveLength(100);
    expect(importBills).toHaveBeenCalledTimes(1);
    await saveImportRows(rows, 1);
    expect(rows.every(row => row.saved)).toBe(true);
  });
  it('旧接口不存在才回退逐笔，单笔失败后保留已完成状态', async () => {
    const rows = records(3);
    vi.mocked(importBills).mockRejectedValue(new ApiError('Not Found', 404));
    vi.mocked(createBill).mockResolvedValueOnce({ id: 1 } as any).mockRejectedValueOnce(new Error('中断'));
    await expect(saveImportRows(rows, 1)).rejects.toThrow('中断');
    expect(rows.map(row => row.saved)).toEqual([true, false, false]);
    const failedKey = vi.mocked(createBill).mock.calls[1][0].import_key;
    vi.mocked(createBill).mockResolvedValue({ id: 2 } as any);
    await saveImportRows(rows, 1);
    expect(vi.mocked(createBill).mock.calls[2][0].import_key).toBe(failedKey);
    expect(rows.every(row => row.saved)).toBe(true);
  });
  it.each([undefined, null, {}, { id: 0 }, { id: -1 }, { id: '1' }, { id: 1.5 }])('旧接口返回无效成功响应 %j 时保留待保存状态和原编号', async response => {
    const rows = records(1);
    const originalKey = rows[0].importKey;
    vi.mocked(importBills).mockRejectedValue(new ApiError('Not Found', 404));
    vi.mocked(createBill).mockResolvedValueOnce(response as any).mockResolvedValueOnce({ id: 1 } as any);

    await expect(saveImportRows(rows, 1)).rejects.toThrow('确认');
    expect(rows[0]).toMatchObject({ saved: false, selected: true, importKey: originalKey });
    await saveImportRows(rows, 1);
    expect(vi.mocked(createBill).mock.calls.map(([payload]) => payload.import_key)).toEqual([originalKey, originalKey]);
    expect(rows[0].saved).toBe(true);
  });
  it.each([
    { ledger_id: 2 }, { type: 'income' }, { amount: 2 }, { amount: null },
    { category: '交通' }, { subcategory: '公交' }, { account: '银行卡' },
    { note: '旧账单' }, { bill_date: '2026-09-22' },
  ])('旧接口用相同编号返回不同账单字段 %j 时不冒充保存成功', async changes => {
    const rows = records(1);
    vi.mocked(importBills).mockRejectedValue(new ApiError('Not Found', 404));
    vi.mocked(createBill).mockResolvedValue({ id: 1, ledger_id: 1, ...rows[0].bill, ...changes } as any);

    await expect(saveImportRows(rows, 1)).rejects.toThrow('不一致');
    expect(rows[0]).toMatchObject({ saved: false, selected: true });
  });
  it('旧接口返回与提交相同的完整账单时接受服务端的空白标准化', async () => {
    const rows = records(1);
    rows[0].bill!.category = ' 餐饮 ';
    rows[0].bill!.note = '  ';
    vi.mocked(importBills).mockRejectedValue(new ApiError('Not Found', 404));
    vi.mocked(createBill).mockResolvedValue({ id: 1, ledger_id: 1, ...rows[0].bill, category: '餐饮', note: null } as any);

    await saveImportRows(rows, 1);
    expect(rows[0].saved).toBe(true);
  });
  it.each([401, 403, 409, 422, 500])('HTTP %i 不得回退或换编号重写', async status => {
    vi.mocked(importBills).mockRejectedValue(new ApiError('保存失败', status));
    await expect(saveImportRows(records(1), 1)).rejects.toThrow();
    expect(createBill).not.toHaveBeenCalled();
  });
  it('返回缺失或重复编号时不错误标记已保存', async () => {
    const rows = records(2);
    vi.mocked(importBills).mockResolvedValue({ items: [{ import_key: rows[0].importKey, bill_id: 1, created: true }] });
    await expect(saveImportRows(rows, 1)).rejects.toThrow('确认');
    expect(rows.some(row => row.saved)).toBe(false);
  });
});

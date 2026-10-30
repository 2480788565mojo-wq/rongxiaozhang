import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { mount, flushPromises, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import * as XLSX from 'xlsx';
import ImportPage from './index.vue';
import { createBill, importBills } from '@/api/bills';
import { ApiError } from '@/api/client';
import { useLedgerStore } from '@/stores/ledger';
import { useUserStore } from '@/stores/user';
vi.mock('@/api/bills');
const testUni = uni;
let wrapper: VueWrapper;
function setup(dataRows: unknown[][]) {
  const pinia = createPinia(); setActivePinia(pinia);
  useUserStore().token = 'token'; useLedgerStore().currentId = 1;
  const book = XLSX.utils.book_new(); XLSX.utils.book_append_sheet(book, XLSX.utils.aoa_to_sheet(dataRows), '账单');
  const data = XLSX.write(book, { type: 'array', bookType: 'xlsx' });
  vi.stubGlobal('wx', { chooseMessageFile: (args: any) => args.success({ tempFiles: [{ name: '账单.xlsx', size: data.byteLength, path: 'wxfile://bill.xlsx' }] }),
    getFileSystemManager: () => ({ readFile: (args: any) => args.success({ data }) }) });
  wrapper = mount(ImportPage, { global: { plugins: [pinia] } });
}
async function choose() {
  await wrapper.find('button.primary').trigger('click');
  await vi.waitUntil(() => wrapper.find('.preview-row').exists() || wrapper.find('.mapping-card').exists(), { timeout: 10000 });
  await flushPromises();
}
const standard = (count: number) => [['日期', '类型', '金额'], ...Array.from({ length: count }, (_, i) => ['2026-09-22', '支出', i + 1])];
describe('微信 Excel 导入流程', () => {
  beforeEach(() => { vi.resetAllMocks(); vi.stubGlobal('uni', testUni); });
  afterEach(() => { wrapper?.unmount(); vi.unstubAllGlobals(); });
  it('预览和取消不写入；旧后端部分失败在原页按原编号重试', async () => {
    setup(standard(2)); await choose();
    expect(importBills).not.toHaveBeenCalled(); expect(createBill).not.toHaveBeenCalled();
    vi.mocked(uni.showModal).mockResolvedValue({ confirm: false } as any);
    await wrapper.find('.confirm-import').trigger('click'); await flushPromises(); expect(importBills).not.toHaveBeenCalled();
    vi.mocked(uni.showModal).mockResolvedValue({ confirm: true } as any);
    vi.mocked(importBills).mockRejectedValue(new ApiError('旧版', 404));
    vi.mocked(createBill).mockResolvedValueOnce({ id: 1 } as any).mockRejectedValueOnce(new Error('网络中断'));
    await wrapper.find('.confirm-import').trigger('click'); await flushPromises();
    expect(wrapper.text()).toContain('已导入 1 笔'); const key = vi.mocked(createBill).mock.calls[1][0].import_key;
    vi.mocked(createBill).mockResolvedValueOnce({ id: 2 } as any);
    await wrapper.find('.confirm-import').trigger('click'); await flushPromises();
    expect(createBill).toHaveBeenCalledTimes(3); expect(vi.mocked(createBill).mock.calls[2][0].import_key).toBe(key);
    expect(wrapper.text()).toContain('已导入 2 笔');
  });
  it('5000条只显示50行，跨页勾选独立，50批保存', async () => {
    setup(standard(5000)); await choose();
    expect(wrapper.findAll('.preview-row')).toHaveLength(50); expect(wrapper.text()).toContain('共 5000 行');
    await wrapper.find('.next-page').trigger('click');
    await wrapper.find('checkbox-group').trigger('change', { detail: { value: Array.from({ length: 49 }, (_, i) => String(i + 53)) } });
    expect(wrapper.find('.confirm-import').text()).toContain('4999');
    vi.mocked(uni.showModal).mockResolvedValue({ confirm: true } as any);
    vi.mocked(importBills).mockImplementation(async (_, items) => ({ items: items.map((row, i) => ({ import_key: row.import_key, bill_id: i + 1, created: true })) }));
    await wrapper.find('.confirm-import').trigger('click'); await flushPromises();
    expect(importBills).toHaveBeenCalledTimes(50); expect(wrapper.text()).toContain('已导入 4999 笔');
    expect(vi.mocked(importBills).mock.calls.flatMap(([, items]) => items).some(row => row.amount === 51)).toBe(false);
    expect(wrapper.findAll('.preview-row')).toHaveLength(50);
  }, 15000);
  it('暂停等待当前批完成，继续时只提交剩余行', async () => {
    setup(standard(201)); await choose();
    vi.mocked(uni.showModal).mockResolvedValue({ confirm: true } as any);
    let resolveBatch: (value: any) => void;
    vi.mocked(importBills).mockImplementationOnce(() => new Promise(resolve => { resolveBatch = resolve; }));
    await wrapper.find('.confirm-import').trigger('click'); await flushPromises();
    await wrapper.find('.pause-import').trigger('click');
    const items = vi.mocked(importBills).mock.calls[0][1];
    resolveBatch!({ items: items.map((row, i) => ({ import_key: row.import_key, bill_id: i + 1, created: true })) }); await flushPromises();
    expect(importBills).toHaveBeenCalledTimes(1); expect(wrapper.text()).toContain('已暂停');
    vi.mocked(importBills).mockImplementation(async (_, remaining) => ({ items: remaining.map((row, i) => ({ import_key: row.import_key, bill_id: i + 1, created: true })) }));
    await wrapper.find('.confirm-import').trigger('click'); await flushPromises();
    expect(importBills).toHaveBeenCalledTimes(3); expect(wrapper.text()).toContain('已导入 201 笔');
  });
  it('无法判断收支时须用户明确选择后才生成预览', async () => {
    setup([['日期', '金额'], ['2026-09-22', 12]]); await choose();
    expect(wrapper.find('.mapping-card').exists()).toBe(true); expect(wrapper.find('.confirm-import').exists()).toBe(false);
    await wrapper.find('.amount-mode').trigger('change', { detail: { value: 3 } });
    await wrapper.find('.apply-mapping').trigger('click'); await flushPromises();
    await vi.waitUntil(() => wrapper.find('.confirm-import').exists());
    expect(wrapper.text()).toContain('支出 ¥12.00'); expect(importBills).not.toHaveBeenCalled();
  });
  it('身份变化停止后续批且拒绝在新身份下重试', async () => {
    setup(standard(201)); await choose();
    vi.mocked(uni.showModal).mockResolvedValue({ confirm: true } as any);
    vi.mocked(importBills).mockImplementation(async (_, items) => { useUserStore().token = 'another'; return { items: items.map((row, i) => ({ import_key: row.import_key, bill_id: i + 1, created: true })) }; });
    await wrapper.find('.confirm-import').trigger('click'); await flushPromises();
    expect(importBills).toHaveBeenCalledTimes(1);
    await wrapper.find('.confirm-import').trigger('click'); await flushPromises();
    expect(importBills).toHaveBeenCalledTimes(1); expect(wrapper.text()).toContain('登录状态已变化');
  });
});

import { beforeEach, describe, expect, it, vi } from 'vitest';
import { flushPromises, mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { useLedgerStore } from '@/stores/ledger';
import { useUserStore } from '@/stores/user';
import { useBillStore } from '@/stores/bill';
import * as api from '@/api/bills';
import AddPage from '@/pages/add/index.vue';
import BillPage from './index.vue';
vi.mock('@/api/bills');
vi.mock('@/api/accounts', () => ({ getAccounts: vi.fn().mockResolvedValue([]) }));
vi.mock('@/api/categories', () => ({ getCategories: vi.fn().mockResolvedValue([]) }));
const bill = { id: 42, ledger_id: 3, creator_id: 1, type: 'expense' as const, amount: 28,
  category: '餐饮美食', subcategory: '午餐', account: '微信钱包', note: '旧备注',
  bill_date: '2026-09-22', raw_input: null, ai_parsed: false, created_at: '2026-09-22', shares: [] };
const stubs = { 'u-button': { template: '<button><slot /></button>' }, 'u-picker': true, FabBtn: true };
let pinia: ReturnType<typeof createPinia>;
beforeEach(() => {
  vi.clearAllMocks();
  pinia = createPinia(); setActivePinia(pinia);
  useUserStore().token = 'test'; useLedgerStore().currentId = 3;
  vi.mocked(getCurrentPages).mockReturnValue([{ options: { id: '42' } }] as any);
  vi.mocked(api.getBill).mockResolvedValue({ ...bill });
  vi.mocked(api.getBills).mockResolvedValue({ items: [{ ...bill }], total: 1, page: 1, page_size: 20 });
});
describe('账单修改和删除', () => {
  it('云端账单回填并只提交修改字段，清空备注会保存为空', async () => {
    const wrapper = mount(AddPage, { global: { plugins: [pinia], stubs } }); await flushPromises();
    expect((wrapper.find('.amount-field').element as HTMLInputElement).value).toBe('28');
    expect(wrapper.text()).toContain('餐饮美食 › 午餐');
    await wrapper.find('.note-input').setValue('');
    vi.mocked(api.updateBill).mockResolvedValue({ ...bill, note: null });
    await wrapper.find('.save-button').trigger('click'); await flushPromises();
    expect(api.updateBill).toHaveBeenCalledWith(42, { note: null });
    expect(api.createBill).not.toHaveBeenCalled(); expect(useBillStore().bills[0].note).toBeNull(); wrapper.unmount();
  });
  it('加载编辑账单失败时不能误建新账单', async () => {
    vi.mocked(api.getBill).mockRejectedValue(new Error('无法读取账单'));
    const wrapper = mount(AddPage, { global: { plugins: [pinia], stubs } }); await flushPromises();
    await wrapper.find('.save-button').trigger('click'); await flushPromises();
    expect(api.createBill).not.toHaveBeenCalled(); expect(api.updateBill).not.toHaveBeenCalled();
    expect(wrapper.text()).toContain('无法读取账单'); wrapper.unmount();
  });
  it('导入超过一页时可以加载剩余账单并编辑', async () => {
    vi.mocked(api.getBills).mockResolvedValueOnce({ items: [{ ...bill }], total: 2, page: 1, page_size: 20 });
    const wrapper = mount(BillPage, { global: { plugins: [pinia], stubs } }); await flushPromises();
    expect(wrapper.text()).toContain('已显示 1 / 2 笔');
    await wrapper.find('.date-head').trigger('click');
    vi.mocked(api.getBills).mockResolvedValueOnce({ items: [{ ...bill, id: 43, note: '剩余账单' }], total: 2, page: 2, page_size: 20 });
    await wrapper.find('.load-more').trigger('click'); await flushPromises();
    expect(api.getBills).toHaveBeenLastCalledWith(expect.objectContaining({ page: 2 }));
    expect(wrapper.text()).toContain('剩余账单'); expect(wrapper.findAll('.edit-bill')).toHaveLength(2); wrapper.unmount();
  });
  it('分类名称包含分隔符时只改备注不会改写分类', async () => {
    vi.mocked(api.getBill).mockResolvedValue({ ...bill, category: '工作 › 差旅', subcategory: null });
    vi.mocked(api.updateBill).mockResolvedValue({ ...bill, category: '工作 › 差旅', subcategory: null, note: '新备注' });
    const wrapper = mount(AddPage, { global: { plugins: [pinia], stubs } }); await flushPromises();
    await wrapper.find('.note-input').setValue('新备注'); await wrapper.find('.save-button').trigger('click'); await flushPromises();
    expect(api.updateBill).toHaveBeenCalledWith(42, { note: '新备注' }); wrapper.unmount();
  });
  it('新账本没有账户也能保存未指定账户的账单', async () => {
    vi.mocked(getCurrentPages).mockReturnValue([{ options: {} }] as any);
    vi.mocked(api.createBill).mockResolvedValue({ ...bill, account: null });
    const wrapper = mount(AddPage, { global: { plugins: [pinia], stubs } }); await flushPromises();
    await wrapper.find('.amount-field').setValue('20'); await wrapper.find('.form-item').trigger('click');
    await wrapper.find('.cat-item').trigger('click'); await wrapper.find('.cat-item').trigger('click');
    await wrapper.find('.save-button').trigger('click'); await flushPromises();
    expect(api.createBill).toHaveBeenCalledWith(expect.objectContaining({ amount:20, account:null })); wrapper.unmount();
  });
  it('列表编辑按钮只打开编辑页，取消删除后记录保留', async () => {
    const wrapper = mount(BillPage, { global: { plugins: [pinia], stubs } }); await flushPromises();
    await wrapper.find('.date-head').trigger('click');
    await wrapper.find('.edit-bill').trigger('click');
    expect(uni.navigateTo).toHaveBeenCalledExactlyOnceWith({ url: '/pages/add/index?id=42' });
    vi.mocked(uni.showModal).mockResolvedValue({ confirm: false, cancel: true } as any);
    await wrapper.find('.delete-bill').trigger('click'); await flushPromises();
    expect(api.deleteBill).not.toHaveBeenCalled(); expect(wrapper.text()).toContain('28.00');
    vi.mocked(uni.showModal).mockResolvedValue({ confirm: true, cancel: false } as any);
    await wrapper.find('.delete-bill').trigger('click'); await flushPromises();
    expect(api.deleteBill).toHaveBeenCalledWith(42); expect(wrapper.text()).not.toContain('28.00'); wrapper.unmount();
  });
});

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import Categories from './index.vue';
import Modal from 'uview-plus/components/u-modal/u-modal.vue';
import { useLedgerStore } from '@/stores/ledger';
import * as categoryApi from '@/api/categories';
import * as ledgerApi from '@/api/ledgers';
import type { CustomCategory, Ledger } from '@/types';

vi.hoisted(() => Object.assign(uni, { getLocale: () => 'zh-Hans', onLocaleChange: () => {} }));
vi.mock('@/api/categories');
vi.mock('@/api/ledgers');

const confirmSelector = '.u-modal__button-group__wrapper--confirm';
const parent: CustomCategory = { id: 11, user_id: 1, ledger_id: 1, type: 'expense', parent_name: '', name: '宠物护理', icon: null, sort: 0, created_at: '2026-09-23' };
const ledger: Ledger = { id: 1, name: '我的账本', type: 'personal', owner_id: 1, invite_code: null, settle_strategy: 'equal', member_count: 1, created_at: '2026-09-23', members: [] };
const wrappers: VueWrapper[] = [];

async function mountPage(ledgerId = 1) {
  const pinia = createPinia();
  setActivePinia(pinia);
  useLedgerStore().switchLedger(ledgerId);
  const wrapper = mount(Categories, {
    global: {
      plugins: [pinia],
      components: { 'u-modal': Modal },
      // 保留真实 u-modal 的按钮和事件，仅替换与提交逻辑无关的弹层动画。
      stubs: { 'u-popup': { template: '<div><slot /></div>' }, 'u-line': true, 'u-loading-icon': true },
    },
  });
  wrappers.push(wrapper);
  await flushPromises();
  return wrapper;
}

async function confirm(wrapper: VueWrapper) {
  await wrapper.find(confirmSelector).trigger('tap');
  await flushPromises();
}

beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(categoryApi.getCategories).mockResolvedValue([]);
  vi.mocked(categoryApi.createCategory).mockResolvedValue(parent);
  vi.mocked(ledgerApi.getLedgers).mockResolvedValue([]);
});
afterEach(() => { wrappers.splice(0).forEach((wrapper) => wrapper.unmount()); });

describe('分类确认按钮', () => {
  it('空名称会提示而不是静默返回', async () => {
    const wrapper = await mountPage();
    await wrapper.find('.add-parent').trigger('click');
    await wrapper.find('input').setValue('   ');
    await confirm(wrapper);
    expect(uni.showToast).toHaveBeenCalledWith({ title: '请输入分类名称', icon: 'none' });
    expect(categoryApi.createCategory).not.toHaveBeenCalled();
    expect(wrapper.findComponent(Modal).props('show')).toBe(true);
  });

  it('从真实确定按钮提交大类并立即显示新分类', async () => {
    const wrapper = await mountPage();
    await wrapper.find('.add-parent').trigger('click');
    await wrapper.find('input').setValue(' 宠物护理 ');
    await confirm(wrapper);
    expect(categoryApi.createCategory).toHaveBeenCalledWith({ ledger_id: 1, type: 'expense', parent_name: '', name: '宠物护理' });
    expect(wrapper.findAll('.parent-name').some((node) => node.text() === '宠物护理')).toBe(true);
    expect(wrapper.findComponent(Modal).props('show')).toBe(false);
    expect(uni.showToast).toHaveBeenCalledWith({ title: '分类已添加', icon: 'success' });
  });

  it('将子类挂到所选大类下', async () => {
    vi.mocked(categoryApi.getCategories).mockResolvedValue([parent]);
    vi.mocked(categoryApi.createCategory).mockResolvedValue({ ...parent, id: 12, parent_name: '宠物护理', name: '猫粮' });
    const wrapper = await mountPage();
    const group = wrapper.findAll('.group').find((node) => node.find('.parent-name').text() === '宠物护理')!;
    await group.find('.parent-row button').trigger('click');
    await wrapper.find('input').setValue('猫粮');
    await confirm(wrapper);
    expect(categoryApi.createCategory).toHaveBeenCalledWith({ ledger_id: 1, type: 'expense', parent_name: '宠物护理', name: '猫粮' });
    expect(group.find('.child-row').text()).toContain('猫粮');
    expect(wrapper.findComponent(Modal).props('show')).toBe(false);
  });

  it('没有账本时显示可操作的提示并保留名称', async () => {
    const wrapper = await mountPage(0);
    await wrapper.find('.add-parent').trigger('click');
    await wrapper.find('input').setValue('宠物护理');
    await confirm(wrapper);
    expect(wrapper.text()).toContain('请先创建或加入账本');
    expect((wrapper.find('input').element as HTMLInputElement).value).toBe('宠物护理');
    expect(categoryApi.createCategory).not.toHaveBeenCalled();
  });

  it('账本尚未加载时重新读取账本再保存', async () => {
    const wrapper = await mountPage(0);
    vi.mocked(ledgerApi.getLedgers).mockResolvedValue([ledger]);
    await wrapper.find('.add-parent').trigger('click');
    await wrapper.find('input').setValue('宠物护理');
    await confirm(wrapper);
    expect(categoryApi.createCategory).toHaveBeenCalledWith({ ledger_id: 1, type: 'expense', parent_name: '', name: '宠物护理' });
    expect(wrapper.findComponent(Modal).props('show')).toBe(false);
  });

  it('请求失败后显示原因、保留输入并允许再次提交', async () => {
    vi.mocked(categoryApi.createCategory).mockRejectedValueOnce(new Error('网络连接失败，请稍后重试'));
    const wrapper = await mountPage();
    await wrapper.find('.add-parent').trigger('click');
    await wrapper.find('input').setValue('宠物护理');
    await confirm(wrapper);
    expect(wrapper.text()).toContain('网络连接失败，请稍后重试');
    expect(wrapper.findComponent(Modal).props('show')).toBe(true);
    expect((wrapper.find('input').element as HTMLInputElement).value).toBe('宠物护理');
    await confirm(wrapper);
    expect(wrapper.findComponent(Modal).props('show')).toBe(false);
    expect(categoryApi.createCategory).toHaveBeenCalledTimes(2);
  });

  it('保存中显示状态并阻止连续点击重复创建', async () => {
    let resolveRequest!: (category: CustomCategory) => void;
    vi.mocked(categoryApi.createCategory).mockReturnValue(new Promise((resolve) => { resolveRequest = resolve; }));
    const wrapper = await mountPage();
    await wrapper.find('.add-parent').trigger('click');
    await wrapper.find('input').setValue('宠物护理');
    await wrapper.find(confirmSelector).trigger('tap');
    await wrapper.find(confirmSelector).trigger('tap');
    expect(wrapper.find(confirmSelector).text()).toContain('保存中');
    expect(categoryApi.createCategory).toHaveBeenCalledTimes(1);
    resolveRequest(parent);
    await flushPromises();
    expect(wrapper.findComponent(Modal).props('show')).toBe(false);
  });

  it('删除分类失败会提示并保留原行', async () => {
    vi.mocked(categoryApi.getCategories).mockResolvedValue([parent]);
    vi.mocked(categoryApi.deleteCategory).mockRejectedValueOnce(
      new Error('分类删除失败，请稍后重试'),
    );
    vi.mocked(uni.showModal).mockImplementationOnce((options: any) => {
      options.success?.({ confirm: true });
    });
    const wrapper = await mountPage();

    await wrapper.find('.remove-parent').trigger('click');
    await flushPromises();

    expect(uni.showToast).toHaveBeenCalledWith({
      title: '分类删除失败，请稍后重试',
      icon: 'none',
    });
    expect(wrapper.text()).toContain('宠物护理');
  });

  it('页面加载失败会显示重试入口，重试成功后显示分类', async () => {
    vi.mocked(categoryApi.getCategories).mockRejectedValueOnce(new Error('分类服务暂不可用')).mockResolvedValue([parent]);
    const wrapper = await mountPage();
    expect(wrapper.text()).toContain('分类服务暂不可用');
    await wrapper.find('.retry-load').trigger('click');
    await flushPromises();
    expect(wrapper.findAll('.parent-name').some((node) => node.text() === '宠物护理')).toBe(true);
    expect(wrapper.find('.retry-load').exists()).toBe(false);
  });
});
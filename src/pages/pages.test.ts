import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import * as billApi from '@/api/bills'
import * as statsApi from '@/api/stats'
import * as budgetApi from '@/api/budgets'
import * as accountApi from '@/api/accounts'
import * as categoryApi from '@/api/categories'

vi.mock('@/api/bills')
vi.mock('@/api/stats')
vi.mock('@/api/budgets')
vi.mock('@/api/accounts')
vi.mock('@/api/categories')
vi.mock('echarts', () => ({
  init: vi.fn(),
  graphic: { LinearGradient: class {} },
}))
vi.mock('@/api/ledgers', () => ({
  getLedgers: vi.fn().mockResolvedValue([]),
  createLedger: vi.fn(),
  joinLedger: vi.fn(),
}))

const stubs = {
  'u-modal': { template: '<div><slot /></div>' },
  'u-line-progress': { template: '<div />' },
  'picker': { template: '<div><slot /></div>' },
  'BudgetGauge': { template: '<div class="gauge-stub" />' },
  'TrendLine': { template: '<div class="trend-stub" />' },
  'CategoryPie': { template: '<div class="pie-stub" />' },
  'FabBtn': { template: '<div />' },
}

const ledger = {
  id: 1,
  name: '我的账本',
  type: 'personal' as const,
  owner_id: 1,
  invite_code: null,
  settle_strategy: 'equal',
  member_count: 1,
  created_at: '2026-07-15T00:00:00',
  members: [],
}

function activatePinia() {
  const pinia = createPinia()
  setActivePinia(pinia)
  return pinia
}

async function mountPage(path: string, pinia = activatePinia()) {
  const component = (await import(/* @vite-ignore */ path)).default
  const wrapper = mount(component, { global: { plugins: [pinia], stubs } })
  await flushPromises()
  return wrapper
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(billApi.getBills).mockResolvedValue({ items: [], total: 0, page: 1, page_size: 20 })
  vi.mocked(statsApi.getOverview).mockResolvedValue({ ledger_id: 1, year: 2026, month: 7, expense: 0, income: 0, balance: 0, budget_used_percentage: null })
  vi.mocked(statsApi.getTrend).mockResolvedValue({ ledger_id: 1, items: [] })
  vi.mocked(statsApi.getCategoryStats).mockResolvedValue({ ledger_id: 1, year: 2026, month: 7, total: 0, items: [] })
  vi.mocked(budgetApi.getBudget).mockResolvedValue(null)
  vi.mocked(budgetApi.getBudgetStatus).mockResolvedValue({ ledger_id: 1, year: 2026, month: 7, statuses: [] })
  vi.mocked(accountApi.getAccounts).mockResolvedValue([])
  vi.mocked(categoryApi.getCategories).mockResolvedValue([])
})

describe('手动记账兼容页', () => {
  it('仍可渲染收支切换按钮', async () => {
    const wrapper = await mountPage('./add/index.vue')
    expect(wrapper.text()).toContain('支出')
    expect(wrapper.text()).toContain('收入')
  })
})

describe('云端账单列表', () => {
  it('无账单时显示空状态', async () => {
    const { useLedgerStore } = await import('@/stores/ledger')
    const pinia = activatePinia()
    const ledgerStore = useLedgerStore()
    ledgerStore.ledgers = [ledger]
    ledgerStore.switchLedger(1)
    const wrapper = await mountPage('./bills/index.vue', pinia)
    expect(wrapper.text()).toContain('该月份暂无账单')
  })

  it('渲染后端返回的日期分组', async () => {
    vi.mocked(billApi.getBills).mockResolvedValue({
      items: [{ id: 1, ledger_id: 1, creator_id: 1, type: 'expense', amount: 50, category: '餐饮美食', subcategory: '午餐', account: '微信钱包', note: null, bill_date: '2026-07-15', raw_input: '午饭50', ai_parsed: true, created_at: '2026-07-15T12:00:00', shares: [] }],
      total: 1, page: 1, page_size: 20,
    })
    const { useLedgerStore } = await import('@/stores/ledger')
    const pinia = activatePinia()
    const ledgerStore = useLedgerStore()
    ledgerStore.ledgers = [ledger]
    ledgerStore.switchLedger(1)
    const wrapper = await mountPage('./bills/index.vue', pinia)
    expect(wrapper.text()).toContain('2026-07-15')
    expect(wrapper.text()).toContain('餐饮美食')
  })
})

describe('云端首页', () => {
  it('渲染云端收支摘要', async () => {
    vi.mocked(statsApi.getOverview).mockResolvedValue({ ledger_id: 1, year: 2026, month: 7, expense: 100, income: 5000, balance: 4900, budget_used_percentage: 10 })
    const { useUserStore } = await import('@/stores/user')
    const { useLedgerStore } = await import('@/stores/ledger')
    const pinia = activatePinia()
    useUserStore().token = 'token'
    useLedgerStore().ledgers = [ledger]
    useLedgerStore().switchLedger(1)
    const wrapper = await mountPage('./index/index.vue', pinia)
    expect(wrapper.text()).toContain('¥100.00')
    expect(wrapper.text()).toContain('¥5000.00')
  })

  it('无预算时显示云端空状态', async () => {
    const { useUserStore } = await import('@/stores/user')
    const { useLedgerStore } = await import('@/stores/ledger')
    const pinia = activatePinia()
    useUserStore().token = 'token'
    useLedgerStore().ledgers = [ledger]
    useLedgerStore().switchLedger(1)
    const wrapper = await mountPage('./index/index.vue', pinia)
    expect(wrapper.text()).toContain('尚未设置分类预算')
  })

  it('跨月后首页重新请求新月份数据', async () => {
    vi.useFakeTimers()
    try {
      vi.setSystemTime(new Date(2026, 11, 31, 23, 59))
      const { useUserStore } = await import('@/stores/user')
      const { useLedgerStore } = await import('@/stores/ledger')
      const pinia = activatePinia()
      useUserStore().token = 'token'
      useLedgerStore().ledgers = [ledger]
      useLedgerStore().switchLedger(1)
      const wrapper = await mountPage('./index/index.vue', pinia)
      vi.setSystemTime(new Date(2027, 0, 1, 0, 1))
      const load = (wrapper.vm as any).$?.setupState?.load
      await load()
      expect(statsApi.getOverview).toHaveBeenLastCalledWith(1, 2027, 1)
      expect(budgetApi.getBudgetStatus).toHaveBeenLastCalledWith(1, 2027, 1)
      wrapper.unmount()
    } finally {
      vi.useRealTimers()
    }
  })

  it('账单接口失败时仍更新首页收支数据', async () => {
    vi.mocked(statsApi.getOverview).mockResolvedValue({ ledger_id: 1, year: 2026, month: 7, expense: 123, income: 456, balance: 333, budget_used_percentage: null })
    vi.mocked(billApi.getBills).mockRejectedValue(new Error('账单服务暂不可用'))
    const { useUserStore } = await import('@/stores/user')
    const { useLedgerStore } = await import('@/stores/ledger')
    const pinia = activatePinia()
    useUserStore().token = 'token'
    useLedgerStore().ledgers = [ledger]
    useLedgerStore().switchLedger(1)
    const wrapper = await mountPage('./index/index.vue', pinia)
    expect(wrapper.text()).toContain('¥123.00')
    expect(wrapper.text()).toContain('¥456.00')
    expect(uni.showToast).toHaveBeenCalledWith({ title: '部分首页数据加载失败，请稍后重试', icon: 'none' })
  })
})

describe('语音记账页面', () => {
  it('表单重置后忽略迟到的微信语音停止回调', async () => {
    const manager: any = {
      start: vi.fn(),
      stop: vi.fn(),
    }
    vi.stubGlobal('requirePlugin', vi.fn(() => ({ getRecordRecognitionManager: () => manager })))
    vi.mocked(uni.authorize).mockImplementation((options: any) => options.success?.())
    const { useUserStore } = await import('@/stores/user')
    const { useLedgerStore } = await import('@/stores/ledger')
    const pinia = activatePinia()
    useUserStore().token = 'token'
    useLedgerStore().ledgers = [ledger]
    useLedgerStore().switchLedger(1)
    const wrapper = await mountPage('./transcribe/index.vue', pinia)
    await wrapper.find('.speech-input').setValue('原文')
    await wrapper.find('.voice-button').trigger('click')
    expect(manager.start).toHaveBeenCalled()
    manager.onStart?.()
    manager.onRecognize?.({ result: '午饭28元' })
    await flushPromises()
    expect((wrapper.find('.speech-input').element as HTMLTextAreaElement).value).toContain('午饭28元')
    const resetForm = (wrapper.vm as any).$?.setupState?.resetForm
    expect(resetForm).toBeTypeOf('function')
    resetForm()
    await flushPromises()
    manager.onStop?.({ result: '迟到的识别结果' })
    await flushPromises()
    expect((wrapper.find('.speech-input').element as HTMLTextAreaElement).value).toBe('')
    expect(wrapper.find('.voice-status').exists()).toBe(false)
    wrapper.unmount()
    delete (globalThis as any).requirePlugin
  })
})

describe('云端管理页面', () => {
  it('账户页显示后端账户余额', async () => {
    vi.mocked(accountApi.getAccounts).mockResolvedValue([{ id: 1, user_id: 1, ledger_id: 1, name: '微信钱包', type: '电子钱包', icon: null, balance: 88.5, created_at: '2026-07-15' }])
    const { useLedgerStore } = await import('@/stores/ledger')
    const pinia = activatePinia()
    useLedgerStore().ledgers = [ledger]
    useLedgerStore().switchLedger(1)
    const wrapper = await mountPage('./accounts/index.vue', pinia)
    expect(wrapper.text()).toContain('微信钱包')
    expect(wrapper.text()).toContain('¥88.50')
  })

  it('预算页显示后端预算', async () => {
    vi.mocked(budgetApi.getBudget).mockResolvedValue({ ledger_id: 1, year: new Date().getFullYear(), month: new Date().getMonth() + 1, total_budget: 5000, category_budgets: { 餐饮美食: 1000 } })
    const { useLedgerStore } = await import('@/stores/ledger')
    const pinia = activatePinia()
    useLedgerStore().ledgers = [ledger]
    useLedgerStore().switchLedger(1)
    const wrapper = await mountPage('./budget/index.vue', pinia)
    expect((wrapper.find('.total-row input').element as HTMLInputElement).value).toBe('5000')
  })

  it('清空预算输入后提交 null 并删除空分类预算', async () => {
    vi.mocked(budgetApi.getBudget).mockResolvedValue({ ledger_id: 1, year: new Date().getFullYear(), month: new Date().getMonth() + 1, total_budget: 5000, category_budgets: { 餐饮美食: 1000 } })
    vi.mocked(budgetApi.setBudget).mockResolvedValue({ ledger_id: 1, year: new Date().getFullYear(), month: new Date().getMonth() + 1, total_budget: null, category_budgets: {} })
    const { useLedgerStore } = await import('@/stores/ledger')
    const pinia = activatePinia()
    useLedgerStore().ledgers = [ledger]
    useLedgerStore().switchLedger(1)
    const wrapper = await mountPage('./budget/index.vue', pinia)
    await wrapper.find('.total-row input').setValue('')
    await wrapper.find('.category-row input').setValue('')
    await wrapper.find('.save').trigger('click')
    await flushPromises()
    expect(budgetApi.setBudget).toHaveBeenCalledWith(expect.objectContaining({ total_budget: null, category_budgets: {} }))
  })

  it('分类页阻止创建与预置大类同名的分类', async () => {
    const { useLedgerStore } = await import('@/stores/ledger')
    const pinia = activatePinia()
    useLedgerStore().ledgers = [ledger]
    useLedgerStore().switchLedger(1)
    const wrapper = await mountPage('./categories/index.vue', pinia)
    await wrapper.find('.add-parent').trigger('click')
    await wrapper.find('.form input').setValue('餐饮美食')
    wrapper.findComponent(stubs['u-modal']).vm.$emit('confirm')
    await flushPromises()
    expect(categoryApi.createCategory).not.toHaveBeenCalled()
    expect(uni.showToast).toHaveBeenCalledWith({ title: '同名大类已存在', icon: 'none' })
  })

  it('统计页显示后端摘要', async () => {
    vi.mocked(statsApi.getOverview).mockResolvedValue({ ledger_id: 1, year: 2026, month: 7, expense: 200, income: 0, balance: -200, budget_used_percentage: null })
    const { useLedgerStore } = await import('@/stores/ledger')
    const pinia = activatePinia()
    useLedgerStore().ledgers = [ledger]
    useLedgerStore().switchLedger(1)
    const wrapper = await mountPage('./stats/index.vue', pinia)
    expect(wrapper.text()).toContain('¥200.00')
  })

  it('跨月后统计页重新请求新月份数据', async () => {
    vi.useFakeTimers()
    try {
      vi.setSystemTime(new Date(2026, 11, 31, 23, 59))
      const { useLedgerStore } = await import('@/stores/ledger')
      const pinia = activatePinia()
      useLedgerStore().ledgers = [ledger]
      useLedgerStore().switchLedger(1)
      const wrapper = await mountPage('./stats/index.vue', pinia)
      vi.setSystemTime(new Date(2027, 0, 1, 0, 1))
      const load = (wrapper.vm as any).$?.setupState?.load
      await load()
      expect(statsApi.getOverview).toHaveBeenLastCalledWith(1, 2027, 1)
      expect(statsApi.getCategoryStats).toHaveBeenLastCalledWith(1, 2027, 1)
      expect(wrapper.text()).toContain('2027年1月')
      wrapper.unmount()
    } finally {
      vi.useRealTimers()
    }
  })
})

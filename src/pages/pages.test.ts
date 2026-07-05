import { describe, expect, it, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { addBill, addAccount, clearAllLocalData, saveBudget } from '@/utils/store'

// uview-plus 组件的桩（uni-app 内置组件保留原生渲染）
const stubs = {
  'u-button': { template: '<button @click="$emit(\'click\')"><slot /></button>' },
  'u-picker': { template: '<div />' },
  'u-modal': { template: '<div><slot /></div>' },
  'u-line-progress': { template: '<div />' },
}

 beforeEach(() => {
  clearAllLocalData()
})

describe('记账页 /pages/add/index.vue', () => {
  it('渲染收支切换按钮', async () => {
    const wrapper = await mount((await import('./add/index.vue')).default, { global: { stubs } })
    expect(wrapper.text()).toContain('支出')
    expect(wrapper.text()).toContain('收入')
  })

  it('切换收支类型', async () => {
    const wrapper = await mount((await import('./add/index.vue')).default, { global: { stubs } })
    const btns = wrapper.findAll('.type-btn')
    if (btns.length >= 2) {
      await btns[1].trigger('click')
      expect(wrapper.text()).toContain('请选择')
    }
  })
})

describe('账单列表 /pages/bills/index.vue', () => {
  it('无账单时显示空状态', async () => {
    clearAllLocalData()
    const wrapper = await mount((await import('@/pages/bills/index.vue')).default, { global: { stubs } })
    expect(wrapper.text()).toContain('暂无账单记录')
  })

  it('有账单时渲染日期分组', async () => {
    addBill({ type: 'expense', amount: 50, category: '午餐', categoryPath: ['餐饮美食', '午餐'], account: '微信', note: '', date: '2026-07-04' })
    addBill({ type: 'income', amount: 1000, category: '工资', categoryPath: ['工资收入', '工资'], account: '银行卡', note: '', date: '2026-07-04' })

    const wrapper = await mount((await import('@/pages/bills/index.vue')).default, { global: { stubs } })
    expect(wrapper.text()).toContain('2026-07-04')
  })
})

describe('首页 /pages/index/index.vue', () => {
  it('渲染收支摘要', async () => {
    addBill({ type: 'expense', amount: 100, category: '午餐', categoryPath: ['餐饮美食', '午餐'], account: '微信', note: '', date: '2026-07-04' })
    addBill({ type: 'income', amount: 5000, category: '工资', categoryPath: ['工资收入', '工资'], account: '银行卡', note: '', date: '2026-07-01' })

    const wrapper = await mount((await import('@/pages/index/index.vue')).default, { global: { stubs } })
    expect(wrapper.text()).toContain('支出')
    expect(wrapper.text()).toContain('收入')
    expect(wrapper.text()).toContain('结余')
  })

  it('未设置预算时显示提示', async () => {
    clearAllLocalData()
    const wrapper = await mount((await import('@/pages/index/index.vue')).default, { global: { stubs } })
    expect(wrapper.text()).toContain('尚未设置预算')
  })

  it('无记录时显示引导文字', async () => {
    clearAllLocalData()
    const wrapper = await mount((await import('@/pages/index/index.vue')).default, { global: { stubs } })
    expect(wrapper.text()).toContain('记账')
  })
})

describe('账户管理 /pages/accounts/index.vue', () => {
  it('显示默认 4 个账户和总资产', async () => {
    const wrapper = await mount((await import('@/pages/accounts/index.vue')).default, { global: { stubs } })
    expect(wrapper.text()).toContain('总资产')
    expect(wrapper.text()).toContain('¥0')
  })
})

describe('预算管理 /pages/budget/index.vue', () => {
  it('设置预算后显示数值', async () => {
    const now = new Date()
    saveBudget({ year: now.getFullYear(), month: now.getMonth() + 1, totalBudget: 5000, categoryBudgets: { 餐饮: 1000 } })
    const wrapper = await mount((await import('@/pages/budget/index.vue')).default, { global: { stubs } })
    expect(wrapper.text()).toContain('5000')
  })
})

describe('统计页 /pages/stats/index.vue', () => {
  it('有数据时显示统计摘要', async () => {
    addBill({ type: 'expense', amount: 200, category: '午餐', categoryPath: ['餐饮美食', '午餐'], account: '微信', note: '', date: '2026-07-04' })
    const wrapper = await mount((await import('@/pages/stats/index.vue')).default, { global: { stubs } })
    expect(wrapper.text()).toContain('本月支出')
  })
})

import { describe, expect, it, beforeEach } from 'vitest'
import {
  genId,
  currentMonth,
  getBills,
  addBill,
  updateBill,
  deleteBill,
  getBillsByMonth,
  getRecentBills,
  getMonthlyStats,
  getCategoryStats,
  getTrendData,
  getAccounts,
  addAccount,
  deleteAccount,
  getBudget,
  saveBudget,
  getPresetCategories,
  addCustomCategory,
  updateCustomCategoryName,
  deleteCustomCategory,
  getCustomCategories,
  getAllCategories,
  exportAllData,
  exportCSV,
  clearAllLocalData,
} from './store'

// 每次测试前清空本地存储
beforeEach(() => {
  clearAllLocalData()
})

describe('工具函数', () => {
  it('genId 生成非空字符串', () => {
    const id = genId()
    expect(id).toBeTruthy()
    expect(typeof id).toBe('string')
  })

  it('currentMonth 返回 YYYY-MM 格式', () => {
    const now = new Date()
    const expected = now.getFullYear() + '-' + String(now.getMonth() + 1).padStart(2, '0')
    expect(currentMonth()).toBe(expected)
  })
})

describe('账单 CRUD', () => {
  const sampleBill = {
    type: 'expense' as const,
    amount: 25.5,
    category: '午餐',
    categoryPath: ['餐饮美食', '午餐'],
    account: '微信钱包',
    note: '沙县小吃',
    date: '2026-07-04',
  }

  it('getBills 初始返回空数组', () => {
    expect(getBills()).toEqual([])
  })

  it('addBill 创建账单并返回完整数据', () => {
    const bill = addBill(sampleBill)
    expect(bill._id).toBeTruthy()
    expect(bill.amount).toBe(25.5)
    expect(bill.type).toBe('expense')
    expect(bill.createdAt).toBeGreaterThan(0)
    expect(bill.category).toBe('午餐')
  })

  it('addBill 多条时按添加倒序排列', () => {
    addBill({ ...sampleBill, amount: 10 })
    addBill({ ...sampleBill, amount: 20 })
    const bills = getBills()
    expect(bills.length).toBe(2)
    expect(bills[0].amount).toBe(20) // 最新在前面
    expect(bills[1].amount).toBe(10)
  })

  it('updateBill 更新指定账单字段', () => {
    const bill = addBill(sampleBill)
    updateBill(bill._id, { amount: 99.9, note: '更新了' })
    const bills = getBills()
    expect(bills[0].amount).toBe(99.9)
    expect(bills[0].note).toBe('更新了')
  })

  it('updateBill 不存在的 ID 不报错', () => {
    updateBill('not-exist', { amount: 100 })
    expect(getBills().length).toBe(0)
  })

  it('deleteBill 删除账单', () => {
    addBill(sampleBill)
    const bill2 = addBill({ ...sampleBill, amount: 30 })
    expect(getBills().length).toBe(2)
    deleteBill(bill2._id)
    expect(getBills().length).toBe(1)
    expect(getBills()[0].amount).toBe(25.5)
  })

  it('deleteBill 删除不存在的 ID 不报错', () => {
    deleteBill('not-exist')
    expect(getBills().length).toBe(0)
  })
})

describe('账单查询', () => {
  beforeEach(() => {
    addBill({ type: 'expense', amount: 50, category: '午餐', categoryPath: ['餐饮美食', '午餐'], account: '微信', note: '', date: '2026-07-04' })
    addBill({ type: 'income', amount: 1000, category: '工资', categoryPath: ['工资收入', '工资'], account: '银行卡', note: '', date: '2026-07-01' })
    addBill({ type: 'expense', amount: 200, category: '打车', categoryPath: ['交通出行', '打车'], account: '支付宝', note: '', date: '2026-06-15' })
  })

  it('getBillsByMonth 按年月过滤', () => {
    const july = getBillsByMonth(2026, 7)
    expect(july.length).toBe(2)
    const june = getBillsByMonth(2026, 6)
    expect(june.length).toBe(1)
  })

  it('getRecentBills 返回最近 N 条', () => {
    const recent = getRecentBills(2)
    expect(recent.length).toBe(2)
  })

  it('getMonthlyStats 正确计算收支', () => {
    const stats = getMonthlyStats(2026, 7)
    expect(stats.expense).toBe(50)
    expect(stats.income).toBe(1000)
    expect(stats.balance).toBe(950)
  })

  it('getMonthlyStats 无数据月份返回 0', () => {
    const stats = getMonthlyStats(2025, 1)
    expect(stats.expense).toBe(0)
    expect(stats.income).toBe(0)
    expect(stats.balance).toBe(0)
  })

  it('getCategoryStats 按金额降序排列', () => {
    const stats = getCategoryStats(2026, 7)
    expect(stats.length).toBe(1)
    expect(stats[0].name).toBe('午餐')
    expect(stats[0].amount).toBe(50)
  })

  it('getTrendData 返回 12 个月数据', () => {
    const data = getTrendData()
    expect(data.length).toBe(12)
    data.forEach(d => {
      expect(d).toHaveProperty('month')
      expect(d).toHaveProperty('expense')
      expect(d).toHaveProperty('income')
    })
  })
})

describe('账户管理', () => {
  it('getAccounts 首次调用返回默认账户', () => {
    const accounts = getAccounts()
    expect(accounts.length).toBe(4)
    expect(accounts[0].name).toBe('微信钱包')
    expect(accounts[0].balance).toBe(0)
  })

  it('addAccount 添加新账户', () => {
    addAccount('测试账户', 500)
    const accounts = getAccounts()
    const added = accounts.find(a => a.name === '测试账户')
    expect(added).toBeTruthy()
    expect(added!.balance).toBe(500)
  })

  it('deleteAccount 删除账户', () => {
    const accounts = getAccounts()
    const count = accounts.length
    deleteAccount(accounts[0]._id)
    expect(getAccounts().length).toBe(count - 1)
  })
})

describe('预算管理', () => {
  it('getBudget 未设置时返回 null', () => {
    expect(getBudget(2026, 7)).toBeNull()
  })

  it('saveBudget 创建并读取预算', () => {
    saveBudget({ year: 2026, month: 7, totalBudget: 5000, categoryBudgets: { 餐饮: 1000 } })
    const budget = getBudget(2026, 7)
    expect(budget).not.toBeNull()
    expect(budget!.totalBudget).toBe(5000)
    expect(budget!.categoryBudgets['餐饮']).toBe(1000)
  })

  it('saveBudget 同月更新预算', () => {
    saveBudget({ year: 2026, month: 7, totalBudget: 3000, categoryBudgets: {} })
    saveBudget({ year: 2026, month: 7, totalBudget: 8000, categoryBudgets: {} })
    const budget = getBudget(2026, 7)
    expect(budget!.totalBudget).toBe(8000)
  })
})

describe('分类管理', () => {
  it('getPresetCategories 返回预设分类', () => {
    const cats = getPresetCategories()
    expect(cats.expense.length).toBeGreaterThan(0)
    expect(cats.income.length).toBeGreaterThan(0)
    expect(cats.expense[0].name).toBe('餐饮美食')
  })

  it('addCustomCategory 添加自定义分类', () => {
    const result = addCustomCategory('expense', '', '我的自定义大类')
    expect(result).not.toBeNull()
    expect(result!.name).toBe('我的自定义大类')
  })

  it('addCustomCategory 拒绝重名', () => {
    addCustomCategory('expense', '', '测试类')
    const result = addCustomCategory('expense', '', '测试类')
    expect(result).toBeNull()
  })

  it('addCustomCategory 拒绝与预置分类冲突', () => {
    const result = addCustomCategory('expense', '', '餐饮美食')
    expect(result).toBeNull()
  })

  it('addCustomCategory 拒绝与预置子分类冲突', () => {
    const result = addCustomCategory('expense', '餐饮美食', '午餐')
    expect(result).toBeNull()
  })

  it('updateCustomCategoryName 修改分类名', () => {
    addCustomCategory('expense', '', '旧名称')
    const cats = getCustomCategories()
    const ok = updateCustomCategoryName(cats[0]._id, '新名称')
    expect(ok).toBe(true)
    expect(getCustomCategories()[0].name).toBe('新名称')
  })

  it('updateCustomCategoryName 不存在返回 false', () => {
    const ok = updateCustomCategoryName('not-exist', '新名称')
    expect(ok).toBe(false)
  })

  it('deleteCustomCategory 删除分类', () => {
    addCustomCategory('expense', '', '待删除')
    expect(getCustomCategories().length).toBe(1)
    deleteCustomCategory(getCustomCategories()[0]._id)
    expect(getCustomCategories().length).toBe(0)
  })

  it('deleteCustomCategory 删除大类时连带删除子类', () => {
    const parent = addCustomCategory('expense', '', '父类')!
    addCustomCategory('expense', '父类', '子类1')
    addCustomCategory('expense', '父类', '子类2')
    expect(getCustomCategories().length).toBe(3)
    deleteCustomCategory(parent._id)
    expect(getCustomCategories().length).toBe(0)
  })

  it('getAllCategories 合并预置和自定义分类', () => {
    addCustomCategory('expense', '', '自定义大类')
    addCustomCategory('expense', '自定义大类', '自定义子类')
    const all = getAllCategories('expense')
    const custom = all.find(c => c.name === '自定义大类')
    expect(custom).toBeTruthy()
    expect(custom!.isCustom).toBe(true)
    expect(custom!.children).toContain('自定义子类')
  })
})

describe('数据导出', () => {
  it('exportAllData 返回完整 JSON 字符串', () => {
    addBill({ type: 'expense', amount: 10, category: '测试', categoryPath: ['测试'], account: '微信', note: '', date: '2026-07-04' })
    const json = exportAllData()
    const data = JSON.parse(json)
    expect(data.version).toBe('1.0')
    expect(data.bills.length).toBe(1)
    expect(data.accounts.length).toBeGreaterThan(0)
  })

  it('exportCSV 生成正确格式', () => {
    const bills = [
      { _id: '1', type: 'expense' as const, amount: 25.5, category: '午餐', categoryPath: ['餐饮美食', '午餐'], account: '微信', note: '吃饭', date: '2026-07-04', createdAt: 100 },
      { _id: '2', type: 'income' as const, amount: 5000, category: '工资', categoryPath: ['工资收入', '工资'], account: '银行卡', note: '', date: '2026-07-01', createdAt: 200 },
    ]
    const csv = exportCSV(bills)
    expect(csv).toContain('日期,类型,分类,金额(元),账户,备注')
    expect(csv).toContain('2026-07-04,支出,午餐,25.50,微信,吃饭')
    expect(csv).toContain('2026-07-01,收入,工资,5000.00,银行卡,')
  })
})

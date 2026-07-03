// 本地数据存储工具
// 在连接微信云开发之前，所有数据都存在本地

const KEYS = {
	bills: 'rzz_bills',
	accounts: 'rzz_accounts',
	budgets: 'rzz_budgets',
	categories: 'rzz_categories',
};

// 生成短ID
function genId(): string {
	return Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
}

// 获取当前月份 YYYY-MM
function currentMonth(): string {
	const d = new Date();
	return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0');
}

// ============ 账单操作 ============

export interface Bill {
	_id: string;
	type: 'expense' | 'income';
	amount: number;
	category: string;
	categoryPath: string[];
	account: string;
	note: string;
	date: string; // YYYY-MM-DD
	createdAt: number;
}

export function getBills(): Bill[] {
	try {
		const data = uni.getStorageSync(KEYS.bills);
		return data ? JSON.parse(data) : [];
	} catch {
		return [];
	}
}

export function saveBills(bills: Bill[]) {
	uni.setStorageSync(KEYS.bills, JSON.stringify(bills));
}

export function addBill(bill: Omit<Bill, '_id' | 'createdAt'>): Bill {
	const bills = getBills();
	const newBill: Bill = {
		_id: genId(),
		...bill,
		createdAt: Date.now(),
	};
	bills.unshift(newBill);
	saveBills(bills);
	return newBill;
}

export function updateBill(id: string, data: Partial<Bill>) {
	const bills = getBills();
	const idx = bills.findIndex(b => b._id === id);
	if (idx > -1) {
		bills[idx] = { ...bills[idx], ...data };
		saveBills(bills);
	}
}

export function deleteBill(id: string) {
	const bills = getBills().filter(b => b._id !== id);
	saveBills(bills);
}

// 按月获取账单
export function getBillsByMonth(year: number, month: number): Bill[] {
	const prefix = year + '-' + String(month).padStart(2, '0');
	return getBills().filter(b => b.date.startsWith(prefix));
}

// 获取最近N条
export function getRecentBills(n: number = 5): Bill[] {
	return getBills().slice(0, n);
}

// 按月统计
export function getMonthlyStats(year: number, month: number) {
	const bills = getBillsByMonth(year, month);
	let expense = 0, income = 0;
	bills.forEach(b => {
		if (b.type === 'expense') expense += b.amount;
		else income += b.amount;
	});
	return { expense, income, balance: income - expense };
}

// 按分类统计
export function getCategoryStats(year: number, month: number) {
	const bills = getBillsByMonth(year, month);
	const map: Record<string, number> = {};
	bills.forEach(b => {
		if (b.type === 'expense') {
			const cat = b.category;
			map[cat] = (map[cat] || 0) + b.amount;
		}
	});
	return Object.entries(map)
		.map(([name, amount]) => ({ name, amount }))
		.sort((a, b) => b.amount - a.amount);
}

// 获取月度趋势（近12个月）
export function getTrendData() {
	const data: { month: string; expense: number; income: number }[] = [];
	const now = new Date();
	for (let i = 11; i >= 0; i--) {
		const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
		const stats = getMonthlyStats(d.getFullYear(), d.getMonth() + 1);
		data.push({
			month: (d.getMonth() + 1) + '月',
			expense: stats.expense,
			income: stats.income,
		});
	}
	return data;
}

// ============ 账户操作 ============

export interface Account {
	_id: string;
	name: string;
	type: string;
	icon: string;
	balance: number;
}

export function getAccounts(): Account[] {
	try {
		const data = uni.getStorageSync(KEYS.accounts);
		if (data) return JSON.parse(data);
	} catch {}
	// 默认账户
	const defaults: Account[] = [
		{ _id: genId(), name: '微信钱包', type: '电子钱包', icon: '', balance: 0 },
		{ _id: genId(), name: '支付宝', type: '电子钱包', icon: '', balance: 0 },
		{ _id: genId(), name: '银行卡', type: '银行卡', icon: '', balance: 0 },
		{ _id: genId(), name: '现金', type: '现金', icon: '', balance: 0 },
	];
	saveAccounts(defaults);
	return defaults;
}

export function saveAccounts(accounts: Account[]) {
	uni.setStorageSync(KEYS.accounts, JSON.stringify(accounts));
}

export function addAccount(name: string, balance: number = 0): Account {
	const accounts = getAccounts();
	const acct: Account = { _id: genId(), name, type: '其他', icon: '', balance };
	accounts.push(acct);
	saveAccounts(accounts);
	return acct;
}

export function deleteAccount(id: string) {
	const accounts = getAccounts().filter(a => a._id !== id);
	saveAccounts(accounts);
}

// ============ 预算操作 ============

export interface Budget {
	_id: string;
	year: number;
	month: number;
	totalBudget: number;
	categoryBudgets: Record<string, number>;
}

export function getBudget(year: number, month: number): Budget | null {
	try {
		const data = uni.getStorageSync(KEYS.budgets);
		if (data) {
			const list: Budget[] = JSON.parse(data);
			return list.find(b => b.year === year && b.month === month) || null;
		}
	} catch {}
	return null;
}

export function saveBudget(budget: Omit<Budget, '_id'>) {
	const data = uni.getStorageSync(KEYS.budgets);
	const list: Budget[] = data ? JSON.parse(data) : [];
	const idx = list.findIndex(b => b.year === budget.year && b.month === budget.month);
	const item: Budget = { _id: genId(), ...budget };
	if (idx > -1) {
		list[idx] = item;
	} else {
		list.push(item);
	}
	uni.setStorageSync(KEYS.budgets, JSON.stringify(list));
}

// ============ 数据导出 ============

export function exportAllData(): string {
	const data = {
		version: '1.0',
		exportTime: new Date().toISOString(),
		bills: getBills(),
		accounts: getAccounts(),
		budgets: (() => {
			try {
				const d = uni.getStorageSync(KEYS.budgets);
				return d ? JSON.parse(d) : [];
			} catch { return []; }
		})(),
	};
	return JSON.stringify(data, null, 2);
}

export function exportCSV(bills: Bill[]): string {
	const header = '日期,类型,分类,金额(元),账户,备注';
	const rows = bills.map(b => {
		const type = b.type === 'expense' ? '支出' : '收入';
		return `${b.date},${type},${b.category},${b.amount.toFixed(2)},${b.account},${b.note || ''}`;
	});
	return header + '\n' + rows.join('\n');
}

export function clearAllLocalData() {
	try {
		uni.removeStorageSync(KEYS.bills);
		uni.removeStorageSync(KEYS.accounts);
		uni.removeStorageSync(KEYS.budgets);
	} catch {}
}

// ============ 分类管理 ============

export interface UserCategory {
	_id: string;
	type: 'expense' | 'income';
	parentName: string; // '' 表示是大类，非空表示属于哪个大类
	name: string;
}

// 预置分类（硬编码）
export function getPresetCategories() {
	return {
		expense: [
			{ name: '餐饮美食', children: ['早餐','午餐','晚餐','外卖','水果零食','奶茶饮品','聚餐宴请'] },
			{ name: '交通出行', children: ['公交地铁','打车','加油','停车费','过路费','火车/飞机','共享单车'] },
			{ name: '购物消费', children: ['服装鞋包','美妆护肤','家居日用','数码电器','文具书籍','宠物用品'] },
			{ name: '居住物业', children: ['房租/房贷','水费','电费','燃气费','物业费','维修','网络宽带'] },
			{ name: '休闲娱乐', children: ['电影演出','运动健身','游戏充值','旅游度假','KTV/酒吧'] },
			{ name: '人情社交', children: ['红包礼金','孝敬父母','送礼','聚会请客'] },
			{ name: '医疗健康', children: ['看病挂号','药品','体检','牙科/眼科','保健'] },
			{ name: '教育学习', children: ['课程培训','考证报名','书籍','文具'] },
			{ name: '通讯', children: ['话费','流量套餐'] },
		],
		income: [
			{ name: '工资收入', children: ['工资','奖金','补贴'] },
			{ name: '副业收入', children: ['兼职','投资理财','红包收入'] },
			{ name: '其他收入', children: ['退款','闲置出售','其他'] },
		],
	};
}

export function getCustomCategories(): UserCategory[] {
	try {
		const data = uni.getStorageSync(KEYS.categories);
		return data ? JSON.parse(data) : [];
	} catch {
		return [];
	}
}

export function saveCustomCategories(cats: UserCategory[]) {
	uni.setStorageSync(KEYS.categories, JSON.stringify(cats));
}

/** 检查名称是否与预置分类冲突 */
function isNameConflict(type: 'expense' | 'income', parentName: string, name: string): boolean {
	const presets = getPresetCategories();
	for (const p of presets[type]) {
		if (parentName) {
			if (p.name === parentName && p.children.includes(name)) return true;
		} else {
			if (p.name === name) return true;
		}
	}
	return false;
}

/** 新增自定义分类 */
export function addCustomCategory(type: 'expense' | 'income', parentName: string, name: string): UserCategory | null {
	const cats = getCustomCategories();
	// 检查自定义分类中是否已同名
	if (cats.some(c => c.type === type && c.parentName === parentName && c.name === name)) return null;
	if (isNameConflict(type, parentName, name)) return null;

	const cat: UserCategory = { _id: genId(), type, parentName, name };
	cats.push(cat);
	saveCustomCategories(cats);
	return cat;
}

/** 修改自定义分类名称 */
export function updateCustomCategoryName(id: string, newName: string): boolean {
	const cats = getCustomCategories();
	const idx = cats.findIndex(c => c._id === id);
	if (idx === -1) return false;
	const oldName = cats[idx].name;
	if (isNameConflict(cats[idx].type, cats[idx].parentName, newName)) return false;
	if (cats.some((c, i) => i !== idx && c.type === cats[idx].type && c.parentName === cats[idx].parentName && c.name === newName)) return false;

	cats[idx].name = newName;

	// 如果改的是大类名称，同步更新所有子类的 parentName
	if (cats[idx].parentName === '') {
		cats.forEach(c => {
			if (c.parentName === oldName && c.type === cats[idx].type) {
				c.parentName = newName;
			}
		});
	}

	saveCustomCategories(cats);
	return true;
}

/** 删除自定义分类（同时删除其子类） */
export function deleteCustomCategory(id: string) {
	const cats = getCustomCategories();
	const target = cats.find(c => c._id === id);
	if (!target) return;
	const filtered = cats.filter(c => {
		if (c._id === id) return false;
		// 如果删除的是大类，连带删除它的子类
		if (target.parentName === '' && c.parentName === target.name && c.type === target.type) return false;
		return true;
	});
	saveCustomCategories(filtered);
}

/** 获取合并后的分类列表（预置 + 自定义），供记账页使用 */
export function getAllCategories(type: 'expense' | 'income') {
	const presets = getPresetCategories()[type];
	const customs = getCustomCategories().filter(c => c.type === type);

	const result: { name: string; children: string[]; isCustom: boolean }[] = [];

	// 预置大类
	presets.forEach(p => {
		result.push({ name: p.name, children: [...p.children], isCustom: false });
	});

	// 自定义大类
	const customParents = customs.filter(c => c.parentName === '');
	customParents.forEach(cp => {
		const children = customs.filter(c => c.parentName === cp.name).map(c => c.name);
		result.push({ name: cp.name, children, isCustom: true });
	});

	// 自定义子类补充到对应的大类下
	customs.filter(c => c.parentName !== '').forEach(cc => {
		const parent = result.find(r => r.name === cc.parentName);
		if (parent && !parent.children.includes(cc.name)) {
			parent.children.push(cc.name);
		}
	});

	return result;
}

export { currentMonth, genId };

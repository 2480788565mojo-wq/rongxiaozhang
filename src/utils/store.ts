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

export { currentMonth, genId };

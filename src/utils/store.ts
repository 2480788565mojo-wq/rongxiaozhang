// 本地数据存储工具
// 在连接微信云开发之前，所有数据都存在手机本地（微信小程序缓存）
// 每条数据都有唯一ID、时间戳，方便后续迁移到云端

// 本地存储的键名，统一管理防止冲突
const KEYS = {
	bills: 'rzz_bills',         // 账单数据
	accounts: 'rzz_accounts',   // 账户数据
	budgets: 'rzz_budgets',     // 预算数据
	categories: 'rzz_categories', // 自定义分类数据
};

// 生成短ID：使用当前时间戳（36进制）+ 随机数，确保唯一性
function genId(): string {
	return Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
}

// 获取当前月份，格式为 YYYY-MM，用于按月筛选账单
function currentMonth(): string {
	const d = new Date();
	return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0');
}

// ============ 账单操作（增删改查）============

// 账单的数据结构定义
export interface Bill {
	_id: string;             // 唯一ID，自动生成
	type: 'expense' | 'income'; // 类型：支出 或 收入
	amount: number;          // 金额（单位：元）
	category: string;        // 分类名称，如"午餐"
	categoryPath: string[];  // 分类路径，如["餐饮美食","午餐"]
	account: string;         // 使用的账户，如"微信钱包"
	note: string;            // 备注，可选
	date: string;            // 日期，格式 YYYY-MM-DD
	createdAt: number;       // 创建时间戳
}

// 获取所有账单列表，从本地存储读取
export function getBills(): Bill[] {
	try {
		const data = uni.getStorageSync(KEYS.bills);
		return data ? JSON.parse(data) : [];
	} catch {
		return []; // 异常时返回空数组，避免页面崩溃
	}
}

// 将账单列表保存到本地存储
export function saveBills(bills: Bill[]) {
	uni.setStorageSync(KEYS.bills, JSON.stringify(bills));
}

// 添加一条新账单，自动生成ID和时间戳，新账单放在列表最前面
export function addBill(bill: Omit<Bill, '_id' | 'createdAt'>): Bill {
	const bills = getBills();
	const newBill: Bill = {
		_id: genId(),
		...bill,
		createdAt: Date.now(),
	};
	bills.unshift(newBill); // 最新的放最前面
	saveBills(bills);
	return newBill;
}

// 更新指定ID的账单信息（只修改传入的字段）
export function updateBill(id: string, data: Partial<Bill>) {
	const bills = getBills();
	const idx = bills.findIndex(b => b._id === id);
	if (idx > -1) {
		bills[idx] = { ...bills[idx], ...data };
		saveBills(bills);
	}
}

// 删除指定ID的账单
export function deleteBill(id: string) {
	const bills = getBills().filter(b => b._id !== id);
	saveBills(bills);
}

// 按月获取账单：根据年份和月份筛选出当月的所有账单
export function getBillsByMonth(year: number, month: number): Bill[] {
	const prefix = year + '-' + String(month).padStart(2, '0');
	return getBills().filter(b => b.date.startsWith(prefix));
}

// 获取最近 N 条账单记录，首页预览用
export function getRecentBills(n: number = 5): Bill[] {
	return getBills().slice(0, n);
}

// 按月统计：计算某个月的总支出、总收入、结余（收入-支出）
export function getMonthlyStats(year: number, month: number) {
	const bills = getBillsByMonth(year, month);
	let expense = 0, income = 0;
	bills.forEach(b => {
		if (b.type === 'expense') expense += b.amount;
		else income += b.amount;
	});
	return { expense, income, balance: income - expense };
}

// 按分类统计：计算某个月中每个支出分类的花费金额，按金额降序排列
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
		.sort((a, b) => b.amount - a.amount); // 花钱最多的排最前面
}

// 获取近12个月的收支趋势数据，用于统计页面的折线图
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

// ============ 账户操作（增删改查） ============

// 账户的数据结构定义
export interface Account {
	_id: string;    // 唯一ID
	name: string;   // 账户名称，如"微信钱包"
	type: string;   // 账户类型，如"电子钱包""银行卡""现金"
	icon: string;   // 图标（预留）
	balance: number; // 账户余额
}

// 获取所有账户，首次使用时自动创建4个默认账户
export function getAccounts(): Account[] {
	try {
		const data = uni.getStorageSync(KEYS.accounts);
		if (data) return JSON.parse(data);
	} catch {}
	// 首次使用：初始化默认账户
	const defaults: Account[] = [
		{ _id: genId(), name: '微信钱包', type: '电子钱包', icon: '', balance: 0 },
		{ _id: genId(), name: '支付宝', type: '电子钱包', icon: '', balance: 0 },
		{ _id: genId(), name: '银行卡', type: '银行卡', icon: '', balance: 0 },
		{ _id: genId(), name: '现金', type: '现金', icon: '', balance: 0 },
	];
	saveAccounts(defaults);
	return defaults;
}

// 保存账户列表到本地存储
export function saveAccounts(accounts: Account[]) {
	uni.setStorageSync(KEYS.accounts, JSON.stringify(accounts));
}

// 添加新账户，可指定名称和初始余额
export function addAccount(name: string, balance: number = 0): Account {
	const accounts = getAccounts();
	const acct: Account = { _id: genId(), name, type: '其他', icon: '', balance };
	accounts.push(acct);
	saveAccounts(accounts);
	return acct;
}

// 删除指定ID的账户
export function deleteAccount(id: string) {
	const accounts = getAccounts().filter(a => a._id !== id);
	saveAccounts(accounts);
}

// ============ 预算操作（按月设置预算） ============

// 预算的数据结构：按月设置，支持总预算和各分类预算
export interface Budget {
	_id: string;                          // 唯一ID
	year: number;                         // 年份
	month: number;                        // 月份
	totalBudget: number;                  // 月总预算金额
	categoryBudgets: Record<string, number>; // 各分类预算，如 {"餐饮": 1000}
}

// 查询指定月份的预算，没有设置过则返回 null
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

// 保存预算设置。如果同一月份已有预算则覆盖更新，否则新增
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

// ============ 数据导出（备份和CSV） ============

// 导出全部数据为 JSON 格式，用于完整备份和恢复
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

// 将账单导出为 CSV 格式（可用 Excel 打开），包含日期、类型、分类、金额等列
export function exportCSV(bills: Bill[]): string {
	const header = '日期,类型,分类,金额(元),账户,备注';
	const rows = bills.map(b => {
		const type = b.type === 'expense' ? '支出' : '收入';
		return `${b.date},${type},${b.category},${b.amount.toFixed(2)},${b.account},${b.note || ''}`;
	});
	return header + '\n' + rows.join('\n');
}

// 清除本地所有数据（危险操作：不可恢复）
export function clearAllLocalData() {
	try {
		uni.removeStorageSync(KEYS.bills);
		uni.removeStorageSync(KEYS.accounts);
		uni.removeStorageSync(KEYS.budgets);
		uni.removeStorageSync(KEYS.categories);
	} catch {}
}

// ============ 分类管理（预置分类 + 自定义分类） ============

// 自定义分类的数据结构
// - parentName 为空（''）表示是"大类"，如"餐饮美食"
// - parentName 有值表示是"子类"，如"午餐"属于"餐饮美食"
export interface UserCategory {
	_id: string;
	type: 'expense' | 'income'; // 支出还是收入
	parentName: string;          // '' 表示是大类，非空表示属于哪个大类
	name: string;                // 分类名称
}

// 预置分类（硬编码）：应用自带的基础分类，不可修改
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

// 获取用户自定义的分类列表
export function getCustomCategories(): UserCategory[] {
	try {
		const data = uni.getStorageSync(KEYS.categories);
		return data ? JSON.parse(data) : [];
	} catch {
		return [];
	}
}

// 保存自定义分类列表到本地存储
export function saveCustomCategories(cats: UserCategory[]) {
	uni.setStorageSync(KEYS.categories, JSON.stringify(cats));
}

// 检查新分类名称是否和预置分类冲突
// 比如用户不能添加一个叫"餐饮美食"的自定义大类，也不能在"餐饮美食"下加一个叫"午餐"的子类
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

// 新增自定义分类，如果名称已存在或冲突则返回 null
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

// 修改自定义分类名称，如果新名称冲突则返回 false
// 注意：修改大类名称时，会自动同步更新其所有子类的 parentName
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

// 删除自定义分类，如果删除的是大类则同时删除其所有子类
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

// 获取合并后的分类列表（预置 + 自定义），供记账页选择分类时使用
export function getAllCategories(type: 'expense' | 'income') {
	const presets = getPresetCategories()[type];
	const customs = getCustomCategories().filter(c => c.type === type);

	const result: { name: string; children: string[]; isCustom: boolean }[] = [];

	// 先加预置的大类
	presets.forEach(p => {
		result.push({ name: p.name, children: [...p.children], isCustom: false });
	});

	// 再加自定义的大类
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

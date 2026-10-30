import { describe, expect, it } from 'vitest';
import * as XLSX from 'xlsx';
import { convertExcelSheet, inspectExcelSheet, MAX_FILE_BYTES, MAX_IMPORT_ROWS, parseExcelBills, readExcelWorkbook } from './excel-import';
function file(rows: unknown[][], bookType: XLSX.BookType = 'xlsx', date1904 = false) {
  const book = XLSX.utils.book_new(); book.Workbook = { WBProps: { date1904 } };
  XLSX.utils.book_append_sheet(book, XLSX.utils.aoa_to_sheet(rows), '账单');
  return XLSX.write(book, { type: 'array', bookType });
}
describe('Excel 账单解析', () => {
  it('读取 UTF-16LE 制表符 CSV（薄荷记账导出格式）', () => {
    const csv = '类型\t金额\t分类\t账户\t日期\t备注\r\n支出\t-12.50\t餐饮\t微信\t2026-09-08 10:00\t早餐\r\n收入\t100\t工资\t银行卡\t2026-09-07\t工资';
    const bytes = new Uint8Array(2 + csv.length * 2); bytes[0] = 0xff; bytes[1] = 0xfe;
    for (let i = 0; i < csv.length; i++) { bytes[2 + i * 2] = csv.charCodeAt(i) & 0xff; bytes[3 + i * 2] = csv.charCodeAt(i) >> 8; }
    const result = parseExcelBills(bytes.buffer);
    expect(result.rows.map(row => row.bill?.type)).toEqual(['expense', 'income']);
    expect(result.rows[0].bill).toMatchObject({ amount: 12.5, category: '餐饮', account: '微信' });
  });
  it.each(['xlsx', 'xls'] as const)('读取 %s 和说明行后的常见列名', format => {
    const result = parseExcelBills(file([['账单明细'], ['交易时间', '收/支', '金额(元)', '分类', '支付方式', '备注'],
      ['2026/09/22 12:30:00', '支出', '¥1,234.50', '购物', '微信钱包', '日用品']], format));
    expect(result.rows[0].bill).toEqual({ bill_date: '2026-09-22', type: 'expense', amount: 1234.5, category: '购物', subcategory: null, account: '微信钱包', note: '日用品' });
    expect(result.rows[0].rowNumber).toBe(3);
  });
  it('读取 Excel 日期序号并遵循 1904 日期系统', () => {
    const result = parseExcelBills(file([['日期','类型','金额'],[1,'收入',20]], 'xlsx', true));
    expect(result.rows[0].bill?.bill_date).toBe('1904-01-02');
  });
  it('错误行保留原因，重复行标记供用户核对', () => {
    const result = parseExcelBills(file([['日期','类型','金额'], ['2026-02-30','支出',20], ['2026-09-22','支出','1,2'],
      ['2026-09-22','不计收支',20], ['2026-09-22','收入',20], ['2026-09-22','收入',20]]));
    expect(result.rows.slice(0,3).every(row => row.error && !row.bill)).toBe(true);
    expect(result.rows[3].bill?.category).toBe('其他收入'); expect(result.rows[4].duplicate).toBe(true);
  });
  it('不执行或导入公式金额，要求固定数值', () => {
    const book = XLSX.utils.book_new(); const sheet = XLSX.utils.aoa_to_sheet([['日期','类型','金额'],['2026-09-22','支出',20]]);
    sheet.C2 = { t: 'n', f: '10+10', v: 20 }; XLSX.utils.book_append_sheet(book,sheet,'账单');
    expect(parseExcelBills(XLSX.write(book,{ type:'array',bookType:'xlsx' })).rows[0].error).toContain('公式');
  });
  it('拒绝无法确定的列、超过容量及空文件，不静默截断', () => {
    expect(() => parseExcelBills(file([['名称','价格'],['午餐',20]]))).toThrow('对应');
    expect(() => parseExcelBills(file([['日期','类型','金额'], ...Array.from({ length: MAX_IMPORT_ROWS + 1 }, () => ['2026-09-22','支出',20])]))).toThrow('10000');
    expect(() => parseExcelBills(new ArrayBuffer(0))).toThrow();
    expect(() => readExcelWorkbook(new ArrayBuffer(MAX_FILE_BYTES + 1))).toThrow('20MB');
  });
  it('完整转换 5000 条，异步转换时让出界面事件循环', async () => {
    const book = readExcelWorkbook(file([['日期','类型','金额'], ...Array.from({ length: 5000 }, (_, i) => ['2026-09-22','支出',i + 1])]));
    const inspection = inspectExcelSheet(book);
    let yielded = false;
    const timer = setTimeout(() => { yielded = true; }, 0);
    const result = await convertExcelSheet(book, inspection.sheetName, inspection.mapping);
    clearTimeout(timer);
    expect(result.rows).toHaveLength(5000);
    expect(result.rows.at(-1)?.bill?.amount).toBe(5000);
    expect(yielded).toBe(true);
  });
  it('在一万多行说明之后找到表头并保留原始行号', () => {
    const result = parseExcelBills(file([...Array.from({ length: 10010 }, () => ['说明：以下为流水']),['入账日期','收支方向','交易金额（元）'],['20260922','支出',30]]));
    expect(result.rows).toHaveLength(1);
    expect(result.rows[0].rowNumber).toBe(10012);
  });
  it('支持选择工作表，不强制读取第一张空白说明页', async () => {
    const book = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(book, XLSX.utils.aoa_to_sheet([['使用说明']]), '说明');
    XLSX.utils.book_append_sheet(book, XLSX.utils.aoa_to_sheet([['日期','类型','金额'],['2026-09-22','收入',80]]), '明细');
    const workbook = readExcelWorkbook(XLSX.write(book,{ type:'array',bookType:'xlsx' }));
    const inspection = inspectExcelSheet(workbook,'明细');
    expect(inspection.sheetNames).toEqual(['说明','明细']);
    expect((await convertExcelSheet(workbook,'明细',inspection.mapping)).rows[0].bill?.amount).toBe(80);
  });
  it('识别银行收入支出分列并拒绝同一行两边都有金额', () => {
    const rows = parseExcelBills(file([['交易日期','贷方发生额','借方发生额','摘要'],
      ['2026.09.22','1,200.10','','工资'],['2026-09-23',0,30,'餐费'],['2026-09-23',20,30,'歧义']])).rows;
    expect(rows[0].bill).toMatchObject({type:'income',amount:1200.1,note:'工资'});
    expect(rows[1].bill).toMatchObject({type:'expense',amount:30});
    expect(rows[2].error).toContain('同时');
  });
  it('识别正负金额，但只有正数且没有方向时要求用户确认', () => {
    const rows = parseExcelBills(file([['日期','金额'],['2026-09-22',-15],['2026-09-23',20]])).rows;
    expect(rows.map(row => row.bill?.type)).toEqual(['expense','income']);
    const inspection = inspectExcelSheet(readExcelWorkbook(file([['日期','金额'],['2026-09-22',20]])));
    expect(inspection.needsMapping).toBe(true);
    expect(inspection.mapping.amountMode).toBe('unknown');
  });
  it('没有表头时根据内容识别日期、收支与金额', () => {
    const book = readExcelWorkbook(file([['2026-09-22','支出',32],['2026-09-23','收入',200]]));
    const result = inspectExcelSheet(book);
    expect(result.mapping.headerRow).toBe(-1);
    expect(result.mapping.startRow).toBe(1);
    expect(result.needsMapping).toBe(false);
    expect(parseExcelBills(file([['2026-09-22','支出',32],['2026-09-23','收入',200]])).rows).toHaveLength(2);
  });
  it('未知表头和金额方向可通过手动对应转换', async () => {
    const book = readExcelWorkbook(file([['什么时候','多少','用途'],['2026-09-22',32,'早餐']]));
    const result = await convertExcelSheet(book,'账单',{headerRow:0,startRow:2,columns:{bill_date:0,amount:1,note:2},amountMode:'expense'});
    expect(result.rows[0].bill).toMatchObject({type:'expense',amount:32,note:'早餐'});
  });
  it('两个数字列不能可靠区分金额时不替用户猜测', () => {
    const result = inspectExcelSheet(readExcelWorkbook(file([['2026-09-22','支出',32,100],['2026-09-23','收入',50,150]])));
    expect(result.needsMapping).toBe(true);
    expect(result.mapping.columns.amount).toBeUndefined();
  });
  it('跳过空行、重复表头、合计和失败交易；明确收入的退款可保留', () => {
    const result = parseExcelBills(file([['日期','收支','金额','交易状态','备注'],
      ['2026-09-22','支出',10,'支付成功','午餐'],[],['日期','收支','金额','交易状态','备注'],['合计','',10],
      ['2026-09-22','支出',20,'交易关闭',''],['2026-09-22','支出',20,'已全额退款',''],
      ['2026-09-22','不计收支',20,'成功',''],['2026-09-22','收入',20,'退款成功','退款到账']]));
    expect(result.rows.filter(row => row.bill)).toHaveLength(2);
    expect(result.rows.filter(row => row.skipped).every(row => Boolean(row.error))).toBe(true);
    expect(result.rows.at(-1)?.bill).toMatchObject({type:'income',amount:20});
  });
  it.each(['2026-09-22','2026/9/22','2026.9.22','2026年9月22日','20260922',20260922,'09/22/2026','22/09/2026','2026-09-22T12:30:00+08:00'])('支持严格校验的日期 %s', date => {
    expect(parseExcelBills(file([['日期','类型','金额'],[date,'支出',20]])).rows[0].bill?.bill_date).toBe('2026-09-22');
  });
  it.each(['2026-02-30','03/04/2026','2026-09-22 25:00:00'])('不猜测或修正错误日期 %s', date => {
    expect(parseExcelBills(file([['日期','类型','金额'],[date,'支出',20]])).rows[0].bill).toBeNull();
  });
  it('保留金额分的精度并拒绝三位小数与方向冲突', () => {
    const rows = parseExcelBills(file([['日期','类型','金额'],['2026-09-22','支出','￥1,234.50元'],['2026-09-22','支出',1.234],['2026-09-22','收入',-20]])).rows;
    expect(rows[0].bill?.amount).toBe(1234.5);
    expect(rows[1].error).toContain('两位');
    expect(rows[2].error).toContain('冲突');
  });
  it('公式即使位于未选中的列也不导入该行', () => {
    const book = XLSX.utils.book_new(); const sheet = XLSX.utils.aoa_to_sheet([['日期','类型','金额','辅助'],['2026-09-22','支出',20,1]]);
    sheet.D2 = { t:'n', f:'1+1', v:2 }; XLSX.utils.book_append_sheet(book,sheet,'账单');
    expect(parseExcelBills(XLSX.write(book,{type:'array',bookType:'xlsx'})).rows[0].error).toContain('公式');
  });
  it('后面的重复表头即使列更全也不会覆盖开头表头而丢掉账单', () => {
    const result = parseExcelBills(file([['日期','类型','金额'],['2026-09-22','支出',20],['日期','类型','金额','分类','备注'],['2026-09-23','收入',30]]));
    expect(result.rows.filter(row => row.bill).map(row => row.rowNumber)).toEqual([2,4]);
  });
  it('账单的备注与分类恰好等于表头词时仍按账单解析', () => {
    const result = parseExcelBills(file([['2026-09-22','收入',20,'日期','金额'],['2026-09-23','收入',30,'日期','金额']]));
    expect(result.rows.filter(row => row.bill)).toHaveLength(2);
  });
  it('显式指定无表头时不能擅自改成首行表头', () => {
    const book = readExcelWorkbook(file([['什么时候','多少','用途'],['2026-09-22',32,'早餐']]));
    const result = inspectExcelSheet(book,'账单',-1);
    expect(result.mapping.headerRow).toBe(-1);
    expect(result.mapping.startRow).toBe(1);
  });
  it('只含收入/支出列也能确定方向，不会把金额列当成日期', () => {
    expect(parseExcelBills(file([['日期','收入金额'],['2026-09-22',50000]])).rows[0].bill).toMatchObject({type:'income',amount:50000});
    expect(parseExcelBills(file([['日期','支出金额'],['2026-09-22',100]])).rows[0].bill).toMatchObject({type:'expense',amount:100});
  });
  it('拒绝重复映射列和数据起始行早于表头', async () => {
    const book = readExcelWorkbook(file([['日期','金额'],['2026-09-22',32]]));
    await expect(convertExcelSheet(book,'账单',{headerRow:0,startRow:2,columns:{bill_date:0,amount:0},amountMode:'expense'})).rejects.toThrow('多个字段');
    await expect(convertExcelSheet(book,'账单',{headerRow:1,startRow:2,columns:{bill_date:0,amount:1},amountMode:'expense'})).rejects.toThrow('之前');
  });
  it('读取支付宝交易创建时间并优先选择明确的收支列而不是业务类型', () => {
    const rows = parseExcelBills(file([['交易创建时间','类型','收/支','交易金额(元)','收/付款方式','交易状态','商品名称'],
      ['2026-09-22 10:30:00','即时到账交易','支出',32,'余额宝','交易成功','早饭']])).rows;
    expect(rows[0].bill).toMatchObject({type:'expense',amount:32,bill_date:'2026-09-22',account:'余额宝',note:'早饭'});
  });
  it('完整保留一万条有效账单，不把原始行号一万以上误认为超量', async () => {
    const workbook = readExcelWorkbook(file([['导出账单说明'],['日期','类型','金额'],...Array.from({length:10000},(_,i)=>['2026-09-22','支出',i+1])]));
    const inspection = inspectExcelSheet(workbook);
    const result = await convertExcelSheet(workbook,inspection.sheetName,inspection.mapping);
    expect(result.rows).toHaveLength(10000);
    expect(result.rows.at(-1)?.rowNumber).toBe(10002);
    expect(result.rows.at(-1)?.bill?.amount).toBe(10000);
  });
  it('同一页后半段换了列顺序时明确拒绝，防止用旧列对应导入错误金额', () => {
    expect(() => parseExcelBills(file([['日期','类型','金额','备注'],['2026-09-22','支出',20,'费用'],
      ['日期','类型','备注','金额'],['2026-09-23','支出',12345,30]]))).toThrow('列顺序');
  });
  it('银行分列中明确为收入的退款到账仍保留，原支出退款跳过', () => {
    const result = parseExcelBills(file([['日期','收入金额','支出金额','状态'],['2026-09-22',30,0,'退款成功'],['2026-09-22',0,40,'已全额退款']]));
    expect(result.rows[0].bill).toMatchObject({type:'income',amount:30});
    expect(result.rows[1].skipped).toBe(true);
  });
});

import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

function pageSource(page: string) {
  return readFileSync(resolve(process.cwd(), "src", "pages", page, "index.vue"), "utf8");
}

describe("Apple HIG 页面视觉回归", () => {
  it("首页保留 Bento 资产总览和三项月度摘要", () => {
    const source = pageSource("index");
    expect(source).toContain('class="asset-card card"');
    expect(source).toContain('class="summary-grid"');
    expect(source).toContain("总资产");
    expect(source).toContain("本月支出");
    expect(source).toContain("本月收入");
    expect(source).toContain("本月结余");
  });

  it("首页采用 B 的浅色卡片资产区和预算胶囊", () => {
    const source = pageSource("index");
    expect(source).toContain('class="asset-foot"');
    expect(source).toContain('class="asset-pill"');
    expect(source).toContain("linear-gradient(135deg");
    expect(source).toContain("var(--shadow-card)");
  });

  it("核心页面不再出现赛博终端文案和样式名", () => {
    const source = ["index", "transcribe", "stats"].map(pageSource).join("\n");
    expect(source).not.toMatch(/cyber|terminal|neon|scanline|glass-panel/i);
    expect(source).not.toContain("指令控制台");
    expect(source).not.toContain("全息");
  });

  it("AI 记账页保留消息气泡和固定底部输入栏", () => {
    const source = pageSource("transcribe");
    expect(source).toContain('class="message-bubble assistant-bubble"');
    expect(source).toContain('class="message-bubble user-bubble"');
    expect(source).toContain('class="composer-shell"');
    expect(source).toMatch(/\.composer-shell\s*\{\s*position:\s*fixed;/);
  });

  it("AI 解析中显示三个加载点并隐藏输入栏", () => {
    const source = pageSource("transcribe");
    expect(source).toContain('v-if="parsing" class="message-row assistant"');
    expect(source).toContain('<view class="typing-dots"><text /><text /><text /></view>');
    expect(source).toContain('v-if="!parsing" class="composer-shell"');
  });

  it("追问未完成时禁止确认，避免过滤后的下标错位", () => {
    const source = pageSource("transcribe");
    expect(source).toMatch(/if \(clarificationQuestion\.value\) return false/);
    // 单笔与多笔两个确认按钮都必须依赖 canConfirm，而非只看 parsedItems
    expect(source.split(':disabled="!canConfirm || saving"').length - 1).toBe(2);
    // saveBills 自身也复用 canConfirm，防止绕过按钮直接调用时提前入账
    expect(source).toMatch(/if \(!parsedItems\.value\.length \|\| !canConfirm\.value\) return;/);
    // 未完成项在 normalize 阶段被丢弃，正是确认键会错位的来源
    expect(source).toMatch(/\.filter\(\(item\): item is ParsedBill => Boolean\(item\)\)/);
  });

  it("共享账本成员不足两人时禁用 AA 并给出提示", () => {
    const source = pageSource("transcribe");
    expect(source).toContain("aaAvailable");
    expect(source).toContain(':disabled="!aaAvailable"');
    expect(source).toContain("至少需要两名成员才能 AA");
  });

  it("记账页保留多笔确认列表和逐笔编辑", () => {
    const source = pageSource("transcribe");
    expect(source).toContain("parsedItems");
    expect(source).toContain("识别到 {{ parsedItems.length }} 笔");
    expect(source).toContain("确认全部 {{ parsedItems.length }} 笔");
    expect(source).toContain("batch-item");
  });

  it("统计页保留趋势、分类和排行空状态", () => {
    const source = pageSource("stats");
    expect(source).toContain("暂无趋势数据");
    expect(source).toContain("本月暂无支出");
    expect(source).toContain("暂无分类排行");
  });

  it("统计页仍可进入原有 AI 消费洞察", () => {
    const source = pageSource("stats");
    expect(source).toContain('url="/pages/insights/index"');
    expect(source).toContain("AI 消费分析");
  });

  it("设置页和账本页保留关键业务入口", () => {
    const settings = pageSource("settings");
    const ledgers = pageSource("ledgers");
    expect(settings).toContain("账本管理");
    expect(settings).toContain("导出 CSV");
    expect(settings).toContain("导出 JSON 备份");
    expect(settings).toContain("退出登录");
    expect(ledgers).toContain("创建账本");
    expect(ledgers).toContain("加入共享账本");
    expect(ledgers).toContain("成员");
    expect(ledgers).toContain("结算");
  });
});

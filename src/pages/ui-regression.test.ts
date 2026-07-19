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
    expect(source).toContain('v-if="!parsing && !parsed" class="composer-shell"');
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

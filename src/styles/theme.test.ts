import { existsSync, readFileSync, readdirSync } from "node:fs";
import { extname, join, resolve } from "node:path";
import { describe, expect, it } from "vitest";

const sourceRoot = resolve(process.cwd(), "src");

function read(relativePath: string) {
  return readFileSync(resolve(sourceRoot, relativePath), "utf8");
}

function collectPageStyles(directory: string): string[] {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = join(directory, entry.name);
    if (entry.isDirectory()) return collectPageStyles(path);
    return [".vue", ".css", ".scss"].includes(extname(entry.name)) ? [path] : [];
  });
}

describe("Apple HIG 全局主题", () => {
  it("定义任务书要求的核心颜色 Token", () => {
    const tokens = read("styles/tokens.css").toLowerCase();
    expect(tokens).toContain("--color-bg: #f7f8fa");
    expect(tokens).toContain("--color-surface: #ffffff");
    expect(tokens).toContain("--color-primary: #4a90e2");
    expect(tokens).toContain("--color-success: #34c759");
    expect(tokens).toContain("--color-warning: #ff9f0a");
    expect(tokens).toContain("--color-danger: #ff3b30");
    expect(tokens).toContain("--color-text: #1d1d1f");
    expect(tokens).toContain("--color-text-secondary: #86868b");
    expect(tokens).toContain("--color-border: #e5e5ea");
  });

  it("页面源码不包含霓虹、玻璃拟态或扫描线样式", () => {
    const pageSource = collectPageStyles(resolve(sourceRoot, "pages"))
      .map((path) => readFileSync(path, "utf8"))
      .join("\n");
    expect(pageSource).not.toMatch(/cyber|neon|glow|glass(?:morphism|-panel)?|scanline|backdrop-filter/i);
  });

  it("旧 CyberBackground 组件保持删除状态", () => {
    expect(existsSync(resolve(sourceRoot, "components/CyberBackground.vue"))).toBe(false);
  });
});

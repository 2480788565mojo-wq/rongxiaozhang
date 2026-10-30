import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { CATEGORY_PRESETS, buildCategoryOptions } from "@/constants/categories";
import type { BillType, CustomCategory } from "@/types";

let nextId = 1;

/** 构造云端自定义分类；parent_name 为空串表示大类（后端默认值就是 ""）。 */
function customCategory(
  name: string,
  options: { type?: BillType; parentName?: string; id?: number } = {},
): CustomCategory {
  return {
    id: options.id ?? nextId++,
    user_id: 1,
    ledger_id: 1,
    type: options.type ?? "expense",
    parent_name: options.parentName ?? "",
    name,
    icon: null,
    sort: 0,
    created_at: "2026-10-01T00:00:00",
  };
}

function pageSource(page: string) {
  return readFileSync(resolve(process.cwd(), "src", "pages", page, "index.vue"), "utf8");
}

describe("buildCategoryOptions 合并预置分类", () => {
  it("没有自定义分类时，预置大类及其子类完整保留", () => {
    const expense = buildCategoryOptions("expense", []);
    expect(expense.map((item) => item.name)).toEqual(Object.keys(CATEGORY_PRESETS.expense));
    for (const [name, children] of Object.entries(CATEGORY_PRESETS.expense)) {
      const parent = expense.find((item) => item.name === name);
      expect(parent, `缺少预置大类 ${name}`).toBeDefined();
      expect(parent?.children).toEqual(children);
    }
    // 返回的是副本，手动记账页后续操作不会污染全局预置。
    expect(expense[0].children).not.toBe(CATEGORY_PRESETS.expense[expense[0].name]);

    const income = buildCategoryOptions("income");
    expect(income.map((item) => item.name)).toEqual(Object.keys(CATEGORY_PRESETS.income));
    for (const [name, children] of Object.entries(CATEGORY_PRESETS.income)) {
      expect(income.find((item) => item.name === name)?.children).toEqual(children);
    }
  });

  it("没有 parent_name 的自定义大类只出现一次", () => {
    // 第二条模拟云端重复数据；第三条与预置大类同名，不能产生第二个同名大类。
    const options = buildCategoryOptions("expense", [
      customCategory("宠物护理"),
      customCategory("宠物护理"),
      customCategory("餐饮美食"),
    ]);

    const pet = options.filter((item) => item.name === "宠物护理");
    expect(pet).toHaveLength(1);
    expect(pet[0].children).toEqual([]);

    const food = options.filter((item) => item.name === "餐饮美食");
    expect(food).toHaveLength(1);
    expect(food[0].children).toEqual(CATEGORY_PRESETS.expense["餐饮美食"]);
  });

  it("自定义子类挂到已存在的预置大类下，不会变成新大类", () => {
    const options = buildCategoryOptions("expense", [
      customCategory("下午茶", { parentName: "餐饮美食" }),
      customCategory("下午茶", { parentName: "餐饮美食" }),
    ]);

    const food = options.find((item) => item.name === "餐饮美食");
    expect(food?.children).toEqual([...CATEGORY_PRESETS.expense["餐饮美食"], "下午茶"]);
    expect(food?.children.filter((child) => child === "下午茶")).toHaveLength(1);
    expect(options.some((item) => item.name === "下午茶")).toBe(false);
    expect(options).toHaveLength(Object.keys(CATEGORY_PRESETS.expense).length);
  });

  it("自定义子类的父类也是自定义时，创建并合并到同一个自定义父类", () => {
    // 子类排在大类前面，验证声明顺序不影响合并结果。
    const options = buildCategoryOptions("expense", [
      customCategory("猫粮", { parentName: "宠物护理" }),
      customCategory("宠物护理"),
    ]);

    const pet = options.filter((item) => item.name === "宠物护理");
    expect(pet).toHaveLength(1);
    expect(pet[0].children).toEqual(["猫粮"]);
    expect(options.some((item) => item.name === "猫粮")).toBe(false);
  });

  it("自定义子类的父类未声明时自动补建父类", () => {
    const options = buildCategoryOptions("expense", [
      customCategory("洗澡", { parentName: "宠物服务" }),
      customCategory("剪毛", { parentName: "宠物服务" }),
    ]);

    const pet = options.filter((item) => item.name === "宠物服务");
    expect(pet).toHaveLength(1);
    expect(pet[0].children).toEqual(["洗澡", "剪毛"]);
  });

  it("只合并当前收支类型的自定义分类", () => {
    const options = buildCategoryOptions("income", [
      customCategory("宠物护理"),
      customCategory("猫粮", { parentName: "宠物护理" }),
    ]);

    expect(options.map((item) => item.name)).toEqual(Object.keys(CATEGORY_PRESETS.income));
    expect(options.some((item) => item.name === "宠物护理")).toBe(false);
  });
});

describe("手动记账页接入统一分类源", () => {
  it("不再从旧本地 store 读分类，改用 buildCategoryOptions + useCategoryStore", () => {
    const source = pageSource("add");

    expect(source).not.toContain("getAllCategories");
    expect(source).not.toMatch(/from\s+["']@\/utils\/store["']/);
    expect(source).not.toContain("getPresetCategories");
    expect(source).not.toContain("getCustomCategories");

    expect(source).toMatch(/import\s*\{\s*buildCategoryOptions\s*\}\s*from\s*["']@\/constants\/categories["']/);
    expect(source).toMatch(/import\s*\{\s*useCategoryStore\s*\}\s*from\s*["']@\/stores\/category["']/);
    expect(source).toMatch(/buildCategoryOptions\(\s*formData\.type,\s*categoryStore\.categories\s*\)/);
  });
});

describe("分类管理与预算页复用同一份预置分类", () => {
  it("分类管理页引用 CATEGORY_PRESETS 而不是旧本地 store", () => {
    const source = pageSource("categories");

    expect(source).toMatch(/import\s*\{\s*CATEGORY_PRESETS\s*\}\s*from\s*["']@\/constants\/categories["']/);
    expect(source).toContain("CATEGORY_PRESETS");
    expect(source).not.toContain("getAllCategories");
    expect(source).not.toMatch(/@\/utils\/store/);
  });

  it("预算页引用 CATEGORY_PRESETS 而不是旧本地 store", () => {
    const source = pageSource("budget");

    expect(source).toMatch(/import\s*\{\s*CATEGORY_PRESETS\s*\}\s*from\s*["']@\/constants\/categories["']/);
    expect(source).toContain("CATEGORY_PRESETS");
    expect(source).not.toContain("getAllCategories");
    expect(source).not.toMatch(/@\/utils\/store/);
  });
});

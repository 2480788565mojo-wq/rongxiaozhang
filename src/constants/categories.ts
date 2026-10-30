import type { BillType, CustomCategory } from "@/types";

/** 预置分类只保留一份；分类管理、手动记账、预算页都从这里读。 */
export const CATEGORY_PRESETS: Record<BillType, Record<string, string[]>> = {
  expense: {
    餐饮美食: ["早餐", "午餐", "晚餐", "外卖", "水果零食", "奶茶饮品", "聚餐宴请"],
    交通出行: ["公交地铁", "打车", "加油"],
    购物消费: ["服装鞋包", "家居日用", "数码电器"],
    居住物业: ["房租/房贷", "水费", "电费"],
    休闲娱乐: ["电影演出", "运动健身", "旅游度假"],
    人情社交: ["红包礼金", "送礼"],
    医疗健康: ["看病挂号", "药品"],
    教育学习: ["课程培训", "书籍"],
    通讯: ["话费", "流量套餐"],
  },
  income: {
    工资收入: ["工资", "奖金", "补贴"],
    副业收入: ["兼职", "红包收入"],
    其他收入: ["退款", "闲置出售", "其他"],
  },
};

export interface CategoryOption {
  name: string;
  children: string[];
}

/** 把预置分类和云端自定义分类合并成同一棵树。 */
export function buildCategoryOptions(
  type: BillType,
  custom: CustomCategory[] = [],
): CategoryOption[] {
  const tree = new Map<string, string[]>(
    Object.entries(CATEGORY_PRESETS[type]).map(([name, children]) => [
      name,
      [...children],
    ]),
  );

  custom
    .filter((item) => item.type === type && !item.parent_name)
    .forEach((item) => {
      if (!tree.has(item.name)) tree.set(item.name, []);
    });

  custom
    .filter((item) => item.type === type && item.parent_name)
    .forEach((item) => {
      const children = tree.get(item.parent_name) ?? [];
      if (!children.includes(item.name)) children.push(item.name);
      tree.set(item.parent_name, children);
    });

  return Array.from(tree, ([name, children]) => ({ name, children }));
}

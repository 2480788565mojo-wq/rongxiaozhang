import { ref } from "vue";
import { defineStore } from "pinia";
import * as categoryApi from "@/api/categories";
import type { BillType, CustomCategory } from "@/types";

export const useCategoryStore = defineStore("category", () => {
  const categories = ref<CustomCategory[]>([]);
  const loading = ref(false);

  async function fetchCategories(ledgerId: number) {
    loading.value = true;
    try {
      categories.value = await categoryApi.getCategories(ledgerId);
      return categories.value;
    } finally { loading.value = false; }
  }

  async function create(
    ledgerId: number,
    type: BillType,
    parentName: string,
    name: string,
  ) {
    const category = await categoryApi.createCategory({
      ledger_id: ledgerId,
      type,
      parent_name: parentName,
      name,
    });
    categories.value.push(category);
    return category;
  }

  async function rename(id: number, name: string) {
    const category = await categoryApi.updateCategory(id, { name });
    const index = categories.value.findIndex((item) => item.id === id);
    if (index >= 0) categories.value[index] = category;
    await fetchCategories(category.ledger_id);
    return category;
  }

  async function remove(id: number) {
    const target = categories.value.find((item) => item.id === id);
    await categoryApi.deleteCategory(id);
    categories.value = categories.value.filter(
      (item) => item.id !== id && item.parent_name !== target?.name,
    );
  }

  function clear() {
    categories.value = [];
    loading.value = false;
  }

  return { categories, loading, fetchCategories, create, rename, remove, clear };
});

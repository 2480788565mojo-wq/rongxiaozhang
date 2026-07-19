import { describe, expect, it } from "vitest";

import { escapeCsvCell } from "./csv";

describe("CSV 导出安全处理", () => {
  it.each(["=HYPERLINK(\"https://evil.example\")", "+cmd", "-1+1", "@SUM(A1)"])(
    "为公式前缀 %s 添加安全前缀",
    (value) => {
      expect(escapeCsvCell(value)).toBe(`"'${value.replace(/"/g, '""')}"`);
    },
  );

  it("清理单元格换行并保留普通引号转义", () => {
    expect(escapeCsvCell('备注\n"正常"')).toBe('"备注 ""正常"""');
  });
});

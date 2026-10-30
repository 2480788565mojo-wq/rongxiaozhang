import { describe, expect, it } from "vitest";
import { buildBatchConfirmKey } from "./bill-batch";

describe("批量确认幂等键", () => {
  it("单笔沿用原始 session，且不标记批量", () => {
    expect(buildBatchConfirmKey("abc123", 0, 1)).toEqual({
      session_id: "abc123",
      is_batch_item: false,
    });
  });

  it("多笔逐项追加索引，并显式标记批量", () => {
    expect(buildBatchConfirmKey("abc123", 0, 2)).toEqual({
      session_id: "abc123:0",
      is_batch_item: true,
    });
    expect(buildBatchConfirmKey("abc123", 1, 2)).toEqual({
      session_id: "abc123:1",
      is_batch_item: true,
    });
  });

  it("空列表按单笔兜底，不会生成带冒号的空 key", () => {
    expect(buildBatchConfirmKey("abc123", 0, 0)).toEqual({
      session_id: "abc123",
      is_batch_item: false,
    });
  });
});

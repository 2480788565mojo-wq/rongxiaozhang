import { beforeEach, describe, expect, it, vi } from "vitest";

import { createSSEConnection } from "./sse";

describe("SSE HTTP 错误处理", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("将 429 后端提示传给页面并停止等待", () => {
    let requestOptions: any;
    const task = { onChunkReceived: vi.fn(), abort: vi.fn() };
    vi.mocked(uni.request).mockImplementation((options: any) => {
      requestOptions = options;
      return task as any;
    });
    const onError = vi.fn();

    createSSEConnection("/api/v1/bills/transcribe", {
      onEvent: vi.fn(),
      onError,
    });
    requestOptions.success({
      statusCode: 429,
      data: { detail: "操作过于频繁，请稍后再试" },
    });

    expect(onError).toHaveBeenCalledOnce();
    expect(onError.mock.calls[0][0]).toBeInstanceOf(Error);
    expect(onError.mock.calls[0][0].message).toBe("操作过于频繁，请稍后再试");
  });

  it("连接关闭后忽略迟到的 HTTP 错误", () => {
    let requestOptions: any;
    const task = { onChunkReceived: vi.fn(), abort: vi.fn() };
    vi.mocked(uni.request).mockImplementation((options: any) => {
      requestOptions = options;
      return task as any;
    });
    const onError = vi.fn();
    const connection = createSSEConnection("/api/v1/bills/transcribe", {
      onEvent: vi.fn(),
      onError,
    });

    connection.close();
    requestOptions.success({ statusCode: 503, data: { detail: "服务暂不可用" } });

    expect(task.abort).toHaveBeenCalledOnce();
    expect(onError).not.toHaveBeenCalled();
  });
});

import type { SSEEvent } from "@/types";

export interface SSERequestOptions {
  method?: "GET" | "POST";
  data?: unknown;
  token?: string;
  onEvent: (event: SSEEvent) => void;
  onError?: (error: unknown) => void;
}

export interface SSEConnection {
  close: () => void;
}

function responseError(response: any): Error {
  let data = response?.data;
  if (typeof data === "string") {
    try { data = JSON.parse(data); } catch { /* Keep the original response text. */ }
  }
  const message = data?.detail || data?.message || (typeof data === "string" ? data : "请求失败，请稍后重试");
  return new Error(message);
}

function decodeChunk(chunk: ArrayBuffer, decoder?: TextDecoder): string {
  if (decoder) return decoder.decode(chunk, { stream: true });
  const bytes = new Uint8Array(chunk);
  const encoded = Array.from(bytes, (byte) => `%${byte.toString(16).padStart(2, "0")}`).join("");
  try {
    return decodeURIComponent(encoded);
  } catch {
    return String.fromCharCode(...bytes);
  }
}

function parseEventBlock(block: string): SSEEvent | null {
  let eventName = "message";
  const dataLines: string[] = [];
  block.split(/\r?\n/).forEach((line) => {
    if (line.startsWith("event:")) eventName = line.slice(6).trim();
    if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
  });
  if (!dataLines.length) return null;
  const rawData = dataLines.join("\n");
  try {
    const parsed = JSON.parse(rawData);
    if (eventName === "message" && parsed?.event) {
      return { event: parsed.event, data: parsed.data || {} };
    }
    return { event: eventName, data: parsed };
  } catch {
    return { event: eventName, data: { message: rawData } };
  }
}

export function createSSEConnection(
  url: string,
  options: SSERequestOptions,
): SSEConnection {
  let buffer = "";
  let closed = false;
  const decoder = typeof TextDecoder !== "undefined" ? new TextDecoder("utf-8") : undefined;
  const task = uni.request({
    url,
    method: options.method || "GET",
    data: options.data,
    enableChunked: true,
    header: {
      Accept: "text/event-stream",
      "Content-Type": "application/json",
      ...(options.token ? { Authorization: `Bearer ${options.token}` } : {}),
    },
    success(response: any) {
      if (!closed && response?.statusCode >= 400) {
        options.onError?.(responseError(response));
      }
    },
    fail(error: any) {
      if (!closed) options.onError?.(error);
    },
  } as any) as any;

  task.onChunkReceived?.((response: { data: ArrayBuffer }) => {
    buffer += decodeChunk(response.data, decoder);
    const blocks = buffer.split(/\r?\n\r?\n/);
    buffer = blocks.pop() || "";
    blocks.forEach((block) => {
      const event = parseEventBlock(block);
      if (event) options.onEvent(event);
    });
  });

  return {
    close() {
      closed = true;
      task.abort?.();
    },
  };
}

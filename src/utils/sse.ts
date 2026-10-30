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

export interface Utf8Chunk {
  text: string;
  rest: number[];
}

/**
 * 小程序不一定有 TextDecoder；必须跨 chunk 保留不完整的多字节序列，
 * 否则一个汉字的 3 个字节被拆到两个 chunk 时会变成乱码。
 */
export function decodeUtf8Bytes(bytes: number[]): Utf8Chunk {
  let index = 0;
  let text = "";
  while (index < bytes.length) {
    const first = bytes[index];
    let needed = 0;
    let codePoint = 0;
    if (first < 0x80) {
      text += String.fromCharCode(first);
      index += 1;
      continue;
    }
    if ((first & 0xe0) === 0xc0) {
      needed = 1;
      codePoint = first & 0x1f;
    } else if ((first & 0xf0) === 0xe0) {
      needed = 2;
      codePoint = first & 0x0f;
    } else if ((first & 0xf8) === 0xf0) {
      needed = 3;
      codePoint = first & 0x07;
    } else {
      // 非法起始字节：用替换符消费掉，避免死循环。
      text += "\uFFFD";
      index += 1;
      continue;
    }
    if (index + needed >= bytes.length) break;
    let valid = true;
    for (let offset = 1; offset <= needed; offset += 1) {
      const next = bytes[index + offset];
      if ((next & 0xc0) !== 0x80) {
        valid = false;
        break;
      }
      codePoint = (codePoint << 6) | (next & 0x3f);
    }
    if (!valid) {
      text += "\uFFFD";
      index += 1;
      continue;
    }
    text += String.fromCodePoint(codePoint);
    index += needed + 1;
  }
  return { text, rest: bytes.slice(index) };
}

function decodeChunk(chunk: ArrayBuffer, decoder: TextDecoder): string {
  return decoder.decode(chunk, { stream: true });
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
  let pendingBytes: number[] = [];
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
    if (decoder) {
      buffer += decodeChunk(response.data, decoder);
    } else {
      const decoded = decodeUtf8Bytes([
        ...pendingBytes,
        ...Array.from(new Uint8Array(response.data)),
      ]);
      pendingBytes = decoded.rest;
      buffer += decoded.text;
    }
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

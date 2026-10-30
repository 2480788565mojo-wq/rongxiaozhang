export interface BatchConfirmKey {
  session_id: string;
  is_batch_item: boolean;
}

/**
 * 单笔沿用原 session；多笔逐项使用 `{session_id}:{index}`，
 * 并在请求里显式标记批量，避免后端靠冒号猜测。
 */
export function buildBatchConfirmKey(
  sessionId: string,
  index: number,
  itemCount: number,
): BatchConfirmKey {
  if (itemCount <= 1) {
    return { session_id: sessionId, is_batch_item: false };
  }
  return {
    session_id: `${sessionId}:${index}`,
    is_batch_item: true,
  };
}

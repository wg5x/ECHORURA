export const MEMORY_SESSION_IDS_KEY = "voice-engine:memory-session-ids";

export function loadMemorySessionIds(storage: Storage, limit = 8): string[] {
  try {
    const parsed = JSON.parse(storage.getItem(MEMORY_SESSION_IDS_KEY) || "[]");
    if (!Array.isArray(parsed)) return [];
    return normalizeSessionIds(parsed).slice(0, limit);
  } catch {
    return [];
  }
}

export function rememberMemorySessionId(storage: Storage, sessionId: string, limit = 8): string[] {
  const cleanId = sessionId.trim();
  if (!cleanId) return loadMemorySessionIds(storage, limit);

  const ids = [cleanId, ...loadMemorySessionIds(storage, limit)].filter(
    (id, index, values) => values.indexOf(id) === index
  );
  const limitedIds = ids.slice(0, limit);
  storage.setItem(MEMORY_SESSION_IDS_KEY, JSON.stringify(limitedIds));
  return limitedIds;
}

export function extractSessionId(message: unknown): string {
  if (!message || typeof message !== "object" || !("session_id" in message)) return "";
  const sessionId = (message as { session_id?: unknown }).session_id;
  return typeof sessionId === "string" ? sessionId.trim() : "";
}

function normalizeSessionIds(values: unknown[]): string[] {
  const ids = values
    .map((value) => (typeof value === "string" ? value.trim() : ""))
    .filter(Boolean);
  return ids.filter((id, index) => ids.indexOf(id) === index);
}

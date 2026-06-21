import {
  MEMORY_SESSION_IDS_KEY,
  extractSessionId,
  loadMemorySessionIds,
  rememberMemorySessionId
} from "./memorySessions.js";

declare const process: {
  exitCode?: number;
};

function assertDeepEqual(actual: unknown, expected: unknown, message: string) {
  if (JSON.stringify(actual) !== JSON.stringify(expected)) {
    throw new Error(`${message}: expected ${JSON.stringify(expected)}, got ${JSON.stringify(actual)}`);
  }
}

function assertEqual(actual: unknown, expected: unknown, message: string) {
  if (actual !== expected) {
    throw new Error(`${message}: expected ${String(expected)}, got ${String(actual)}`);
  }
}

function test(name: string, run: () => void) {
  try {
    run();
    console.log(`ok - ${name}`);
  } catch (error) {
    process.exitCode = 1;
    console.error(`not ok - ${name}`);
    console.error(error instanceof Error ? error.message : error);
  }
}

class MemoryStorage implements Storage {
  private items = new Map<string, string>();

  get length() {
    return this.items.size;
  }

  clear(): void {
    this.items.clear();
  }

  getItem(key: string): string | null {
    return this.items.get(key) ?? null;
  }

  key(index: number): string | null {
    return [...this.items.keys()][index] ?? null;
  }

  removeItem(key: string): void {
    this.items.delete(key);
  }

  setItem(key: string, value: string): void {
    this.items.set(key, value);
  }
}

test("loads valid session ids from storage", () => {
  const storage = new MemoryStorage();
  storage.setItem(MEMORY_SESSION_IDS_KEY, JSON.stringify(["session-b", "session-a"]));

  assertDeepEqual(loadMemorySessionIds(storage), ["session-b", "session-a"], "stored ids should load");
});

test("remembers newest session first and deduplicates", () => {
  const storage = new MemoryStorage();
  storage.setItem(MEMORY_SESSION_IDS_KEY, JSON.stringify(["session-a", "session-b"]));

  const ids = rememberMemorySessionId(storage, "session-b");

  assertDeepEqual(ids, ["session-b", "session-a"], "existing id should move to front");
});

test("limits remembered sessions", () => {
  const storage = new MemoryStorage();
  storage.setItem(MEMORY_SESSION_IDS_KEY, JSON.stringify(["session-1", "session-2", "session-3"]));

  const ids = rememberMemorySessionId(storage, "session-4", 3);

  assertDeepEqual(ids, ["session-4", "session-1", "session-2"], "old sessions should be trimmed");
});

test("extracts session id from realtime messages", () => {
  assertEqual(
    extractSessionId({ type: "route_decision", session_id: "session-1" }),
    "session-1",
    "route decision should expose session id"
  );
  assertEqual(extractSessionId({ type: "status", status: "idle" }), "", "status has no session id");
});

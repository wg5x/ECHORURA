import { attachRouteDecision, type LogItem, type RouteDecision } from "./logItems.js";

declare const process: {
  exitCode?: number;
};

function assertEqual(actual: unknown, expected: unknown, message: string) {
  if (actual !== expected) {
    throw new Error(`${message}: expected ${String(expected)}, got ${String(actual)}`);
  }
}

function assertDeepEqual(actual: unknown, expected: unknown, message: string) {
  if (JSON.stringify(actual) !== JSON.stringify(expected)) {
    throw new Error(`${message}: values differ`);
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

test("attaches route decision to matching user text without replacing the original message", () => {
  const items: LogItem[] = [
    { id: "assistant-1", role: "assistant", text: "你好", at: "10:00:02" },
    { id: "user-1", role: "user", text: "打开淘宝", at: "10:00:01", turnId: "turn-1" }
  ];
  const decision: RouteDecision = {
    type: "route_decision",
    session_id: "session-1",
    turn_id: "turn-1",
    agent_profile_id: "phone-assistant",
    mode: "native_action",
    intent: "app.open",
    confidence: 0.92
  };

  const updated = attachRouteDecision(items, decision);

  assertEqual(updated[1].text, "打开淘宝", "user text should remain original");
  assertEqual(updated[1].routeDecision?.intent, "app.open", "route decision should attach to user item");
});

test("ignores route decision when no matching user turn exists", () => {
  const items: LogItem[] = [{ id: "user-1", role: "user", text: "打开淘宝", at: "10:00:01", turnId: "turn-1" }];
  const decision: RouteDecision = {
    type: "route_decision",
    session_id: "session-1",
    turn_id: "turn-2",
    mode: "native_action",
    intent: "app.open",
    confidence: 0.92
  };

  assertDeepEqual(attachRouteDecision(items, decision), items, "unmatched decision should not change logs");
});

test("does not attach ordinary chat route decisions to user messages", () => {
  const items: LogItem[] = [{ id: "user-1", role: "user", text: "今天天气怎么样", at: "10:00:01", turnId: "turn-1" }];
  const decision: RouteDecision = {
    type: "route_decision",
    session_id: "session-1",
    turn_id: "turn-1",
    mode: "chat",
    intent: "general",
    confidence: 0.45
  };

  assertDeepEqual(attachRouteDecision(items, decision), items, "ordinary chat should not show intent hint");
});

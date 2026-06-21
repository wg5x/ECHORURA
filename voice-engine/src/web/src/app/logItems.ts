export type RouteDecision = {
  type: "route_decision";
  session_id: string;
  turn_id: string;
  agent_profile_id?: string;
  mode: string;
  intent?: string;
  scenario_id?: string;
  scenario_intent?: string;
  confidence: number;
  need_clarification?: boolean;
  requires_confirmation?: boolean;
  arguments?: Record<string, unknown>;
};

export type LogItem = {
  id: string;
  role: string;
  text: string;
  at: string;
  outputId?: string;
  turnId?: string;
  routeDecision?: RouteDecision;
};

export function attachRouteDecision(items: LogItem[], decision: RouteDecision): LogItem[] {
  if (decision.mode === "chat" || decision.intent === "general") return items;

  const targetIndex = items.findIndex((item) => item.role === "user" && item.turnId === decision.turn_id);
  if (targetIndex < 0) return items;

  return items.map((item, index) => (index === targetIndex ? { ...item, routeDecision: decision } : item));
}

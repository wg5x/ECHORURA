from __future__ import annotations

from .models import RouteDecision, RouteInput
from .registry import default_capabilities
from .strategies import RuleBasedStrategy


class SemanticRouter:
    def __init__(self) -> None:
        self.capabilities = default_capabilities()
        self.strategy = RuleBasedStrategy()

    def route_text(self, session_id: str, turn_id: str, text: str, source: str = "manual_text") -> RouteDecision:
        route_input = RouteInput(session_id=session_id, turn_id=turn_id, text=text, source=source)
        return self.strategy.decide(route_input, self.capabilities)

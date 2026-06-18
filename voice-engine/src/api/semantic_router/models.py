from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


RouteMode = Literal["chat", "scenario", "native_action", "server_action", "clarify", "reject"]
RouteDecision = dict[str, Any]


@dataclass(frozen=True)
class RouteInput:
    session_id: str
    turn_id: str
    text: str
    source: str = "manual_text"
    agent_profile_id: str = "default"


@dataclass(frozen=True)
class Capability:
    id: str
    mode: RouteMode
    intent: str
    keywords: tuple[str, ...]
    confidence: float
    scenario_id: str = ""
    scenario_intent: str = ""
    requires_confirmation: bool = False
    arguments: dict[str, Any] = field(default_factory=dict)

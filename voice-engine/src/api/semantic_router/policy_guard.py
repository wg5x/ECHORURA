from __future__ import annotations

from ..configs.capability_config import CapabilityConfig
from ..configs.agent_profile_config import default_agent_profile_configs
from ..configs.capability_config import default_capability_configs


def enforce_route_policy(decision: dict, text: str, agent_profile_id: str) -> dict:
    normalized_text = _normalize_text(text)
    corrected = dict(decision)

    if corrected.get("mode") == "native_action" and corrected.get("intent") == "app.search":
        if "搜索" not in normalized_text and normalized_text.startswith("打开"):
            corrected["intent"] = "app.open"

    capability = _capability_config_for_decision(corrected)
    if capability and capability.mode == "scenario":
        corrected.setdefault("scenario_id", capability.scenario_id)
        corrected.setdefault("scenario_intent", capability.scenario_intent)

    if not capability or capability.id not in _allowed_capability_ids(agent_profile_id):
        return _fallback_chat(decision, agent_profile_id)

    return corrected


def _allowed_capability_ids(agent_profile_id: str) -> set[str]:
    profiles = {profile.id: profile for profile in default_agent_profile_configs()}
    profile = profiles.get(agent_profile_id) or profiles["default"]
    return set(profile.enabled_capability_ids)


def _capability_config_for_decision(decision: dict) -> CapabilityConfig | None:
    mode = str(decision.get("mode") or "")
    intent = str(decision.get("intent") or "")
    scenario_intent = str(decision.get("scenario_intent") or "")
    scenario_id = str(decision.get("scenario_id") or "")
    for config in default_capability_configs():
        if config.mode != mode:
            continue
        if mode == "scenario":
            if scenario_id and config.scenario_id != scenario_id:
                continue
            if scenario_intent and config.scenario_intent != scenario_intent:
                continue
            if config.intent == intent:
                return config
            continue
        if config.intent == intent:
            return config
    return None


def _fallback_chat(decision: dict, agent_profile_id: str) -> dict:
    return {
        "type": "route_decision",
        "session_id": decision.get("session_id", ""),
        "turn_id": decision.get("turn_id", ""),
        "agent_profile_id": agent_profile_id,
        "mode": "chat",
        "intent": "general",
        "confidence": 0.0,
        "need_clarification": False,
        "requires_confirmation": False,
        "arguments": {},
    }


def _normalize_text(text: str) -> str:
    return "".join(str(text or "").lower().split())

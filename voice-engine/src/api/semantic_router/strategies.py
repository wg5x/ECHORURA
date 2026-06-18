from __future__ import annotations

from .models import Capability, RouteDecision, RouteInput


class RuleBasedStrategy:
    def decide(self, route_input: RouteInput, capabilities: list[Capability]) -> RouteDecision:
        text = _normalize_text(route_input.text)
        capability = _match_capability(text, capabilities)
        arguments = dict(capability.arguments)
        arguments.update(_extract_arguments(capability, route_input.text, text))

        decision: RouteDecision = {
            "type": "route_decision",
            "session_id": route_input.session_id,
            "turn_id": route_input.turn_id,
            "mode": capability.mode,
            "intent": capability.intent,
            "confidence": capability.confidence,
            "need_clarification": False,
            "requires_confirmation": capability.requires_confirmation,
            "arguments": arguments,
        }

        if capability.mode == "scenario":
            decision["scenario_id"] = capability.scenario_id
            decision["scenario_intent"] = capability.scenario_intent

        return decision


def _match_capability(text: str, capabilities: list[Capability]) -> Capability:
    fallback = capabilities[-1]
    for capability in capabilities:
        if not capability.keywords:
            fallback = capability
            continue
        if any(keyword.lower() in text for keyword in capability.keywords):
            return capability
    return fallback


def _extract_arguments(capability: Capability, raw_text: str, normalized_text: str) -> dict[str, str]:
    if capability.id == "music_creation.create_song":
        return _extract_create_song_arguments(raw_text, normalized_text)
    if capability.id == "music_creation.revise_song":
        return {"revision_prompt": raw_text.strip()}
    return {}


def _extract_create_song_arguments(raw_text: str, normalized_text: str) -> dict[str, str]:
    arguments = {
        "theme": raw_text.strip(),
        "language": "zh",
    }
    genre = _extract_genre(normalized_text)
    if genre:
        arguments["genre"] = genre
    vocal = _extract_vocal(normalized_text)
    if vocal:
        arguments["vocal"] = vocal
    return arguments


def _extract_genre(text: str) -> str:
    genres = {
        "lofi": ("lofi", "lo-fi"),
        "rap": ("说唱", "rap"),
        "folk": ("民谣",),
        "electronic": ("电子",),
        "rock": ("摇滚",),
    }
    for genre, markers in genres.items():
        if any(marker in text for marker in markers):
            return genre
    return ""


def _extract_vocal(text: str) -> str:
    if "女声" in text:
        return "female"
    if "男声" in text:
        return "male"
    if "童声" in text:
        return "child"
    return ""


def _normalize_text(text: str) -> str:
    return "".join(str(text or "").strip().lower().split())

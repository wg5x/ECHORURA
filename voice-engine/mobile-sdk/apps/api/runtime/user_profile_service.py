from __future__ import annotations

from typing import Any

from ..memory.card_service import list_memory_cards, to_memory_id


USER_PROFILE_VERSION = "local-user-profile-v1"


def build_user_profile(user_id: Any, scene_id: Any | None = None) -> dict[str, Any]:
    normalized_user_id = to_memory_id(user_id)
    normalized_scene_id = to_memory_id(scene_id) if scene_id else None
    cards = list_memory_cards(normalized_user_id, normalized_scene_id)
    warnings = [] if cards else ["当前用户还没有可聚合的本地记忆卡。"]

    return {
        "version": USER_PROFILE_VERSION,
        "userId": normalized_user_id,
        "sceneId": normalized_scene_id,
        "updatedAt": _latest_updated_at(cards),
        "stableFacts": _merge_items(cards, "facts"),
        "profile": _merge_items(cards, "profile"),
        "preferences": _merge_items(cards, "preferences"),
        "conversationStyle": _merge_items(cards, "conversationStyle"),
        "openThreads": _merge_items(cards, "openThreads"),
        "boundaries": _merge_items(cards, "doNotAssume"),
        "evidence": [
            {"sceneId": card.get("sceneId"), "updatedAt": card.get("updatedAt")}
            for card in cards
        ],
        "warnings": warnings,
    }


def _merge_items(cards: list[dict[str, Any]], field: str, limit: int = 12) -> list[str]:
    result: list[str] = []
    for card in cards:
        values = card.get(field)
        if not isinstance(values, list):
            continue
        for item in values:
            if isinstance(item, str) and item and item not in result:
                result.append(item)
            if len(result) >= limit:
                return result
    return result


def _latest_updated_at(cards: list[dict[str, Any]]) -> str | None:
    values = [item.get("updatedAt") for item in cards if isinstance(item.get("updatedAt"), str)]
    return max(values) if values else None

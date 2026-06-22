from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..config import LOCAL_RUNTIME_DIR
from ..shared.value_utils import to_int_in_range, to_string_value


MEMORY_CARD_VERSION = "local-memory-card-v1"
MEMORY_CARD_DIR = LOCAL_RUNTIME_DIR / "memory-cards"
DEFAULT_MEMORY_MAX_CHARS = 1200
MIN_MEMORY_MAX_CHARS = 400
MAX_MEMORY_MAX_CHARS = 3000


def to_memory_id(value: Any) -> str:
    text = to_string_value(value)
    if not text:
        raise ValueError("userId 和 sceneId 不能为空。")
    return text[:80]


async def read_memory_card(user_id: str, scene_id: str) -> dict[str, Any] | None:
    filepath = _get_memory_card_path(user_id, scene_id)
    if not filepath.exists():
        return None
    return normalize_memory_card(json.loads(filepath.read_text(encoding="utf-8")), user_id, scene_id)


async def write_memory_card(card: dict[str, Any]) -> None:
    MEMORY_CARD_DIR.mkdir(parents=True, exist_ok=True)
    filepath = _get_memory_card_path(card["userId"], card["sceneId"])
    tmp_path = filepath.with_suffix(".json.tmp")
    tmp_path.write_text(
        json.dumps(card, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    tmp_path.replace(filepath)


async def delete_memory_card(user_id: str, scene_id: str) -> None:
    filepath = _get_memory_card_path(user_id, scene_id)
    try:
        filepath.unlink()
    except FileNotFoundError:
        return


def list_memory_cards(user_id: str, scene_id: str | None = None) -> list[dict[str, Any]]:
    if scene_id:
        filepath = _get_memory_card_path(user_id, scene_id)
        paths = [filepath] if filepath.exists() else []
    else:
        paths = sorted(MEMORY_CARD_DIR.glob(f"{_to_safe_memory_key(user_id)}__*.json")) if MEMORY_CARD_DIR.exists() else []

    cards: list[dict[str, Any]] = []
    for path in paths:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(value, dict):
            cards.append(normalize_memory_card(value, to_string_value(value.get("userId")) or user_id, to_string_value(value.get("sceneId")) or "unknown"))

    cards.sort(key=lambda item: to_string_value(item.get("updatedAt")), reverse=True)
    return cards


def normalize_memory_card(
    value: Any,
    user_id: str,
    scene_id: str,
    max_chars: int = DEFAULT_MEMORY_MAX_CHARS,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        return _make_empty_memory_card(user_id, scene_id, max_chars)

    return {
        **_make_empty_memory_card(user_id, scene_id, max_chars),
        "updatedAt": value.get("updatedAt") if isinstance(value.get("updatedAt"), str) else None,
        "maxChars": to_int_in_range(value.get("maxChars"), max_chars, MIN_MEMORY_MAX_CHARS, MAX_MEMORY_MAX_CHARS),
        "facts": _normalize_string_list(value.get("facts"), 6, 110),
        "profile": _normalize_string_list(value.get("profile"), 5, 96),
        "preferences": _normalize_string_list(value.get("preferences"), 6, 96),
        "conversationStyle": _normalize_string_list(value.get("conversationStyle"), 5, 96),
        "openThreads": _normalize_string_list(value.get("openThreads"), 6, 110),
        "doNotAssume": _normalize_string_list(value.get("doNotAssume"), 5, 110),
        "lastSessionSummary": re.sub(r"\s+", " ", to_string_value(value.get("lastSessionSummary")))[:180],
    }


def render_memory_card_for_prompt(card: dict[str, Any]) -> str:
    return _render_memory_card_for_prompt(card)


def compress_memory_card(
    *,
    user_id: str,
    scene_id: str,
    max_chars: int,
    previous_card: Any,
    report: dict[str, Any],
) -> dict[str, Any]:
    warnings: list[str] = []
    base = normalize_memory_card(previous_card, user_id, scene_id, max_chars)
    transcript = report.get("transcript") if isinstance(report.get("transcript"), list) else []
    candidates = _extract_memory_candidates(transcript)

    if not transcript:
        warnings.append("本次报告没有可压缩的转写内容，仅保留原有记忆卡。")

    card = {
        **base,
        "updatedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "maxChars": max_chars,
        "facts": _merge_memory_list(base["facts"], candidates["facts"], 6, 110),
        "preferences": _merge_memory_list(base["preferences"], candidates["preferences"], 6, 96),
        "conversationStyle": _merge_memory_list(base["conversationStyle"], candidates["conversationStyle"], 5, 96),
        "openThreads": _merge_memory_list(base["openThreads"], candidates["openThreads"], 6, 110),
        "doNotAssume": _merge_memory_list(
            base["doNotAssume"],
            ["敏感身份、住址、健康、财务、未成年人信息默认不写入本地压缩记忆。"],
            5,
            110,
        ),
        "lastSessionSummary": _build_memory_session_summary(report, transcript),
    }

    return {"card": _fit_memory_card_budget(card, max_chars), "warnings": warnings}


def _make_empty_memory_card(user_id: str, scene_id: str, max_chars: int = DEFAULT_MEMORY_MAX_CHARS) -> dict[str, Any]:
    return {
        "version": MEMORY_CARD_VERSION,
        "userId": user_id,
        "sceneId": scene_id,
        "updatedAt": None,
        "maxChars": to_int_in_range(max_chars, DEFAULT_MEMORY_MAX_CHARS, MIN_MEMORY_MAX_CHARS, MAX_MEMORY_MAX_CHARS),
        "facts": [],
        "profile": [],
        "preferences": [],
        "conversationStyle": [],
        "openThreads": [],
        "doNotAssume": ["不要把压缩记忆当成确定事实；仅在用户主动提及时轻量承接。"],
        "lastSessionSummary": "",
    }


def _get_memory_card_path(user_id: str, scene_id: str) -> Path:
    return MEMORY_CARD_DIR / f"{_to_safe_memory_key(user_id)}__{_to_safe_memory_key(scene_id)}.json"


def _to_safe_memory_key(value: Any) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]", "_", to_memory_id(value))[:80]


def _normalize_string_list(value: Any, limit: int = 6, item_limit: int = 96) -> list[str]:
    if not isinstance(value, list):
        return []

    result: list[str] = []
    for item in value:
        text = re.sub(r"\s+", " ", to_string_value(item))
        if not text:
            continue
        text = text[:item_limit]
        if text not in result:
            result.append(text)
        if len(result) >= limit:
            break
    return result


def _should_skip_memory_text(text: str) -> bool:
    return bool(re.search(r"身份证|银行卡|密码|住址|详细地址|手机号|电话号码|诊断|处方|药量|自杀|自伤|他伤|未成年人", text))


def _compact_memory_text(text: Any, max_length: int = 96) -> str:
    return re.sub(r"\s+", " ", to_string_value(text)).replace("“", "").replace("”", "")[:max_length]


def _merge_memory_list(previous: list[str], additions: list[str], limit: int, item_limit: int = 96) -> list[str]:
    return _normalize_string_list([*previous, *additions], limit, item_limit)


def _extract_memory_candidates(transcript: list[Any]) -> dict[str, list[str]]:
    user_turns = [
        text
        for item in transcript
        if isinstance(item, dict) and item.get("role") == "user"
        for text in [_compact_memory_text(item.get("text"), 120)]
        if text and not _should_skip_memory_text(text)
    ]
    preference_pattern = re.compile(r"喜欢|不喜欢|偏好|希望|想要|下次|以后|记得|习惯|不要")
    style_pattern = re.compile(r"慢一点|快一点|声音|语速|简短|直接|温柔|别打断|多问|少问")
    fact_pattern = re.compile(r"我叫|我是|我在做|我主要|我的工作|我的职业|我的目标|我负责|我正在")

    return {
        "facts": [text for text in user_turns if fact_pattern.search(text)][-3:],
        "openThreads": [f"最近提到：{text}" for text in user_turns[-3:]],
        "preferences": [text for text in user_turns if preference_pattern.search(text)][-3:],
        "conversationStyle": [text for text in user_turns if style_pattern.search(text)][-2:],
    }


def _build_memory_session_summary(report: dict[str, Any], transcript: list[Any]) -> str:
    explicit_summary = _compact_memory_text(report.get("summary"), 180)
    if explicit_summary and not _should_skip_memory_text(explicit_summary):
        return explicit_summary

    recent_user_turns = [
        text
        for item in transcript
        if isinstance(item, dict) and item.get("role") == "user"
        for text in [_compact_memory_text(item.get("text"), 72)]
        if text and not _should_skip_memory_text(text)
    ][-2:]

    if not recent_user_turns:
        return "本次会话未形成可保存的非敏感用户记忆。"
    return f"本次主要围绕：{'；'.join(recent_user_turns)}。"


def _render_memory_card_for_prompt(card: dict[str, Any]) -> str:
    lines = [
        f"记忆版本：{card['version']}",
        f"最近摘要：{card['lastSessionSummary']}" if card.get("lastSessionSummary") else "",
        *[f"稳定事实：{item}" for item in card.get("facts", [])],
        *[f"用户画像：{item}" for item in card.get("profile", [])],
        *[f"偏好：{item}" for item in card.get("preferences", [])],
        *[f"互动方式：{item}" for item in card.get("conversationStyle", [])],
        *[f"待承接话题：{item}" for item in card.get("openThreads", [])],
        *[f"边界：{item}" for item in card.get("doNotAssume", [])],
    ]
    return "\n".join([line for line in lines if line])


def _fit_memory_card_budget(card: dict[str, Any], max_chars: int) -> dict[str, Any]:
    next_card = {
        **card,
        "facts": [*card["facts"]],
        "profile": [*card["profile"]],
        "preferences": [*card["preferences"]],
        "conversationStyle": [*card["conversationStyle"]],
        "openThreads": [*card["openThreads"]],
        "doNotAssume": [*card["doNotAssume"]],
    }
    removable_fields = ["openThreads", "preferences", "profile", "facts", "conversationStyle", "doNotAssume"]

    while len(_render_memory_card_for_prompt(next_card)) > max_chars:
        field = next((key for key in removable_fields if len(next_card[key]) > 1), None)
        if not field:
            break
        next_card[field].pop(0)

    if len(_render_memory_card_for_prompt(next_card)) > max_chars and len(next_card["lastSessionSummary"]) > 80:
        next_card["lastSessionSummary"] = f"{next_card['lastSessionSummary'][:77]}..."

    while len(_render_memory_card_for_prompt(next_card)) > max_chars:
        field = next((key for key in removable_fields if next_card[key]), None)
        if not field:
            break
        next_card[field].pop(0)

    return next_card

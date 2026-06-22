from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..config import LOCAL_RUNTIME_DIR
from ..shared.value_utils import to_int_in_range, to_string_value


CALL_LOG_DIR = LOCAL_RUNTIME_DIR / "call-logs"
MAX_CALL_LOGS = 50


def save_call_log(raw_log: Any) -> dict[str, Any]:
    if not isinstance(raw_log, dict):
        raise ValueError("访谈日志不能为空。")

    user_id = _normalize_id(raw_log.get("userId"), "userId")
    scene_id = _normalize_id(raw_log.get("sceneId"), "sceneId")
    report = raw_log.get("report")
    if not isinstance(report, dict):
        raise ValueError("访谈报告不能为空。")

    now = _now_iso()
    log_id = _normalize_id(raw_log.get("id") or report.get("id") or f"log_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}", "logId")
    log = {
        "id": log_id,
        "sessionId": _normalize_optional_id(raw_log.get("sessionId"), "sessionId"),
        "requestId": _normalize_optional_id(raw_log.get("requestId"), "requestId"),
        "userId": user_id,
        "sceneId": scene_id,
        "savedAt": now,
        "report": report,
    }

    directory = CALL_LOG_DIR / user_id / scene_id
    directory.mkdir(parents=True, exist_ok=True)
    filepath = directory / f"{log_id}.json"
    tmp_path = filepath.with_suffix(".json.tmp")
    tmp_path.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_path.replace(filepath)
    return log


def list_call_logs(user_id: Any | None = None, scene_id: Any | None = None, limit: Any = 10) -> list[dict[str, Any]]:
    normalized_user_id = _normalize_id(user_id, "userId") if user_id else None
    normalized_scene_id = _normalize_id(scene_id, "sceneId") if scene_id else None
    count = to_int_in_range(limit, 10, 1, MAX_CALL_LOGS)
    roots: list[Path]

    if normalized_user_id and normalized_scene_id:
        roots = [CALL_LOG_DIR / normalized_user_id / normalized_scene_id]
    elif normalized_user_id:
        roots = [CALL_LOG_DIR / normalized_user_id]
    else:
        roots = [CALL_LOG_DIR]

    logs: list[dict[str, Any]] = []
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*.json"):
            try:
                value = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if isinstance(value, dict):
                logs.append(value)

    logs.sort(key=lambda item: to_string_value(item.get("savedAt")), reverse=True)
    return logs[:count]


def _normalize_id(value: Any, label: str) -> str:
    text = to_string_value(value)
    if not text:
        raise ValueError(f"{label} 不能为空。")
    if not re.fullmatch(r"[a-zA-Z0-9_-]{1,100}", text):
        raise ValueError(f"{label} 格式无效。")
    return text


def _normalize_optional_id(value: Any, label: str) -> str | None:
    text = to_string_value(value)
    if not text:
        return None
    return _normalize_id(text, label)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

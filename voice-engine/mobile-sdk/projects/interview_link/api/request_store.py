from __future__ import annotations

import json
import re
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from projects.interview_link.app_config import APP_CONFIG


PROJECT_DIR = Path(__file__).resolve().parents[1]
STORE_PATH = PROJECT_DIR / ".local" / "requests.json"


def create_request(entry_params: Any) -> dict[str, Any]:
    params = _normalize_entry_params(entry_params)
    now = _now_iso()
    request = {
        "requestId": f"req_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}_{secrets.token_hex(3)}",
        "sceneKind": APP_CONFIG["sceneKind"],
        "sceneId": APP_CONFIG["sceneId"],
        "entryParams": params,
        "platformSessionId": None,
        "status": "created",
        "createdAt": now,
        "updatedAt": now,
    }
    requests = _read_requests()
    requests.append(request)
    _write_requests(requests)
    return request


def list_requests() -> list[dict[str, Any]]:
    return sorted(_read_requests(), key=lambda item: str(item.get("createdAt") or ""), reverse=True)


def update_request(request_id: Any, patch: Any) -> dict[str, Any]:
    request_id_text = _normalize_id(request_id, "requestId")
    if not isinstance(patch, dict):
        raise ValueError("更新内容不能为空。")

    requests = _read_requests()
    for index, request in enumerate(requests):
        if request.get("requestId") != request_id_text:
            continue

        status = str(patch.get("status") or request.get("status") or "created")
        if status not in {"created", "started", "finished", "failed"}:
            raise ValueError("status 格式无效。")

        session_id = patch.get("platformSessionId")
        updated = {
            **request,
            "status": status,
            "platformSessionId": _normalize_optional_id(session_id, "platformSessionId")
            if session_id is not None
            else request.get("platformSessionId"),
            "updatedAt": _now_iso(),
        }
        requests[index] = updated
        _write_requests(requests)
        return updated

    raise KeyError("request 不存在。")


def _read_requests() -> list[dict[str, Any]]:
    if not STORE_PATH.exists():
        return []
    try:
        value = json.loads(STORE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _write_requests(requests: list[dict[str, Any]]) -> None:
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = STORE_PATH.with_suffix(".json.tmp")
    tmp_path.write_text(json.dumps(requests, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_path.replace(STORE_PATH)


def _normalize_entry_params(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        raise ValueError("entryParams 不能为空。")
    params = {
        "name": _normalize_text(value.get("name"), "姓名"),
        "phone": _normalize_text(value.get("phone"), "电话"),
        "city": _normalize_text(value.get("city"), "城市"),
    }
    if not re.fullmatch(r"[\d+\-\s]{6,30}", params["phone"]):
        raise ValueError("电话格式无效。")
    return params


def _normalize_text(value: Any, label: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{label}不能为空。")
    return text[:100]


def _normalize_id(value: Any, label: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{label} 不能为空。")
    if not re.fullmatch(r"[a-zA-Z0-9_-]{1,120}", text):
        raise ValueError(f"{label} 格式无效。")
    return text


def _normalize_optional_id(value: Any, label: str) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    return _normalize_id(text, label)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

from __future__ import annotations

import os
from pathlib import Path


API_DIR = Path(__file__).resolve().parent
SRC_DIR = API_DIR.parent
VOICE_ENGINE_DIR = SRC_DIR.parent
REPO_ROOT = VOICE_ENGINE_DIR.parent

DEFAULT_PORT = 8787
DEFAULT_VOLC_WS_URL = "wss://openspeech.bytedance.com/api/v3/realtime/dialogue"
DEFAULT_VOLC_RESOURCE_ID = "volc.speech.dialog"
PUBLIC_APP_KEY = "PlgvMymc7f3tQnJ6"
DEFAULT_RECORDINGS_DIR = SRC_DIR / "data" / "recordings"
DEFAULT_DEBUG_EVENTS_DIR = SRC_DIR / "data" / "debug-events"
DEFAULT_CONVERSATIONS_DIR = SRC_DIR / "data" / "conversations"
DEFAULT_MEMORIES_DIR = SRC_DIR / "data" / "memories"
DEFAULT_AUDIT_REPORTS_DIR = SRC_DIR / "data" / "audit-reports"

ENV_FILES = (
    SRC_DIR / ".env.local",
    VOICE_ENGINE_DIR / ".env.local",
    REPO_ROOT / ".env.local",
    REPO_ROOT / ".env",
)


def load_local_env() -> None:
    for filepath in ENV_FILES:
        if not filepath.exists():
            continue

        for line in filepath.read_text(encoding="utf-8").splitlines():
            trimmed = line.strip()
            if not trimmed or trimmed.startswith("#") or "=" not in trimmed:
                continue

            key, raw_value = trimmed.split("=", 1)
            key = key.strip()
            if key and key not in os.environ:
                os.environ[key] = raw_value.strip().strip("'\"")


def get_port() -> int:
    return int(os.environ.get("PORT") or DEFAULT_PORT)


def has_volc_credentials() -> bool:
    return bool(os.environ.get("VOLC_API_APP_ID") and os.environ.get("VOLC_API_ACCESS_KEY"))


def get_volc_ws_url() -> str:
    return os.environ.get("VOLC_WS_URL") or DEFAULT_VOLC_WS_URL


def get_volc_headers(connect_id: str) -> dict[str, str]:
    return {
        "X-Api-App-ID": os.environ.get("VOLC_API_APP_ID", ""),
        "X-Api-Access-Key": os.environ.get("VOLC_API_ACCESS_KEY", ""),
        "X-Api-Resource-Id": os.environ.get("VOLC_API_RESOURCE_ID") or DEFAULT_VOLC_RESOURCE_ID,
        "X-Api-App-Key": os.environ.get("VOLC_API_APP_KEY") or PUBLIC_APP_KEY,
        "X-Api-Connect-Id": connect_id,
    }


def is_voice_recording_enabled() -> bool:
    return os.environ.get("VOICE_RECORDING_ENABLED", "").lower() == "true"


def get_recordings_dir() -> Path:
    configured_dir = Path(os.environ.get("VOICE_RECORDINGS_DIR") or DEFAULT_RECORDINGS_DIR)
    return configured_dir if configured_dir.is_absolute() else SRC_DIR / configured_dir


def is_realtime_debug_log_enabled() -> bool:
    return os.environ.get("VOICE_DEBUG_LOG_ENABLED", "").lower() == "true"


def get_debug_events_dir() -> Path:
    configured_dir = Path(os.environ.get("VOICE_DEBUG_LOG_DIR") or DEFAULT_DEBUG_EVENTS_DIR)
    return configured_dir if configured_dir.is_absolute() else SRC_DIR / configured_dir


def get_conversations_dir() -> Path:
    configured_dir = Path(os.environ.get("VOICE_CONVERSATIONS_DIR") or DEFAULT_CONVERSATIONS_DIR)
    return configured_dir if configured_dir.is_absolute() else SRC_DIR / configured_dir


def get_memories_dir() -> Path:
    configured_dir = Path(os.environ.get("VOICE_MEMORIES_DIR") or DEFAULT_MEMORIES_DIR)
    return configured_dir if configured_dir.is_absolute() else SRC_DIR / configured_dir


def get_audit_reports_dir() -> Path:
    configured_dir = Path(os.environ.get("VOICE_AUDIT_REPORTS_DIR") or DEFAULT_AUDIT_REPORTS_DIR)
    return configured_dir if configured_dir.is_absolute() else SRC_DIR / configured_dir

from __future__ import annotations

import os
from pathlib import Path


DEFAULT_PORT = 8787
DEFAULT_VOLC_WS_URL = "wss://openspeech.bytedance.com/api/v3/realtime/dialogue"
DEFAULT_VOLC_PODCAST_WS_URL = "wss://openspeech.bytedance.com/api/v3/sami/podcasttts"
DEFAULT_VOLC_PODCAST_RESOURCE_ID = "volc.service_type.10050"
PUBLIC_APP_KEY = "PlgvMymc7f3tQnJ6"
API_DIR = Path(__file__).resolve().parent
REPO_ROOT = API_DIR.parents[1]
API_LOCAL_DIR = API_DIR / ".local"
LOCAL_RUNTIME_DIR = API_LOCAL_DIR / "runtime"
LOCAL_ENV_FILE = API_LOCAL_DIR / "env" / ".env.local"
CONFIG_ENV_FILE = REPO_ROOT / "config" / "env" / ".env.local"
LEGACY_ENV_FILES = (REPO_ROOT / ".env.local", REPO_ROOT / ".env")


def load_local_env() -> None:
    for filepath in (LOCAL_ENV_FILE, CONFIG_ENV_FILE, *LEGACY_ENV_FILES):
        if not filepath.exists():
            continue

        for line in filepath.read_text(encoding="utf-8").splitlines():
            trimmed = line.strip()
            if not trimmed or trimmed.startswith("#") or "=" not in trimmed:
                continue

            key, raw_value = trimmed.split("=", 1)
            key = key.strip()
            if not key or key in os.environ:
                continue

            os.environ[key] = raw_value.strip().strip("'\"")


def has_volc_credentials() -> bool:
    return bool(os.environ.get("VOLC_API_APP_ID") and os.environ.get("VOLC_API_ACCESS_KEY"))


def has_volc_podcast_credentials() -> bool:
    return bool(
        (os.environ.get("VOLC_PODCAST_APP_ID") or os.environ.get("VOLC_API_APP_ID"))
        and (os.environ.get("VOLC_PODCAST_ACCESS_KEY") or os.environ.get("VOLC_API_ACCESS_KEY"))
    )


def get_volc_ws_url() -> str:
    return os.environ.get("VOLC_WS_URL") or DEFAULT_VOLC_WS_URL


def get_volc_podcast_ws_url() -> str:
    return os.environ.get("VOLC_PODCAST_WS_URL") or DEFAULT_VOLC_PODCAST_WS_URL


def get_volc_headers(connect_id: str) -> dict[str, str]:
    return {
        "X-Api-App-ID": os.environ.get("VOLC_API_APP_ID", ""),
        "X-Api-Access-Key": os.environ.get("VOLC_API_ACCESS_KEY", ""),
        "X-Api-Resource-Id": os.environ.get("VOLC_API_RESOURCE_ID") or "volc.speech.dialog",
        "X-Api-App-Key": os.environ.get("VOLC_API_APP_KEY") or PUBLIC_APP_KEY,
        "X-Api-Connect-Id": connect_id,
    }


def get_volc_podcast_headers(connect_id: str) -> dict[str, str]:
    return {
        "X-Api-App-ID": os.environ.get("VOLC_PODCAST_APP_ID") or os.environ.get("VOLC_API_APP_ID", ""),
        "X-Api-Access-Key": os.environ.get("VOLC_PODCAST_ACCESS_KEY") or os.environ.get("VOLC_API_ACCESS_KEY", ""),
        "X-Api-Resource-Id": os.environ.get("VOLC_PODCAST_RESOURCE_ID") or DEFAULT_VOLC_PODCAST_RESOURCE_ID,
        "X-Api-App-Key": os.environ.get("VOLC_PODCAST_APP_KEY") or os.environ.get("VOLC_API_APP_KEY") or PUBLIC_APP_KEY,
        "X-Api-Connect-Id": connect_id,
    }

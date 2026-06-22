from __future__ import annotations

import json
import re
import struct
from pathlib import Path
from typing import Any

from .call_log_service import CALL_LOG_DIR
from .voice_recording_service import VOICE_RECORDING_DIR
from ..shared.value_utils import to_string_value


def get_session_result(session_id: Any) -> dict[str, Any]:
    normalized_session_id = _normalize_session_id(session_id)
    log = _find_call_log(normalized_session_id)
    manifest = _find_recording_manifest(normalized_session_id)
    report = log.get("report") if isinstance(log.get("report"), dict) else {}
    transcript = report.get("transcript") if isinstance(report.get("transcript"), list) else []

    return {
        "sessionId": normalized_session_id,
        "requestId": log.get("requestId") or manifest.get("requestId"),
        "sceneId": log.get("sceneId") or manifest.get("sceneId"),
        "status": "finished" if log else manifest.get("status") or "unknown",
        "startedAt": report.get("startedAt") or manifest.get("startedAt"),
        "endedAt": report.get("endedAt") or manifest.get("endedAt"),
        "transcript": transcript,
        "audio": _audio_summary(normalized_session_id, manifest),
    }


def build_session_audio_wav(session_id: Any, *, source: Any = "client") -> bytes:
    normalized_session_id = _normalize_session_id(session_id)
    normalized_source = _normalize_audio_source(source)
    manifest = _find_recording_manifest(normalized_session_id)
    if not manifest:
        raise FileNotFoundError("录音不存在。")

    recording_dir = _recording_dir_for_manifest(manifest)
    audio_info = _audio_info(manifest, normalized_source)
    audio_path = recording_dir / to_string_value(audio_info.get("path"))
    if not audio_path.exists():
        raise FileNotFoundError("录音文件不存在。")

    sample_rate = _sample_rate_from_mime(audio_info.get("mime"), 16000)
    pcm = audio_path.read_bytes()
    return _pcm_s16le_to_wav(pcm, sample_rate)


def _find_call_log(session_id: str) -> dict[str, Any]:
    if not CALL_LOG_DIR.exists():
        return {}
    for path in CALL_LOG_DIR.rglob("*.json"):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(value, dict) and value.get("sessionId") == session_id:
            return value
    return {}


def _find_recording_manifest(session_id: str) -> dict[str, Any]:
    if not VOICE_RECORDING_DIR.exists():
        return {}
    for path in VOICE_RECORDING_DIR.rglob("manifest.json"):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(value, dict) and value.get("sessionId") == session_id:
            return {**value, "_manifestPath": str(path)}
    return {}


def _audio_summary(session_id: str, manifest: dict[str, Any]) -> dict[str, Any] | None:
    if not manifest:
        return None
    audio_info = _audio_info(manifest, "client")
    if not audio_info:
        return None
    return {
        "url": f"/runtime/sessions/{session_id}/audio",
        "mime": "audio/wav",
        "source": "client",
        "byteLength": manifest.get("clientAudioBytes"),
    }


def _audio_info(manifest: dict[str, Any], source: str) -> dict[str, Any]:
    audio_info = manifest.get("assistantAudio" if source == "assistant" else "clientAudio")
    return audio_info if isinstance(audio_info, dict) else {}


def _normalize_audio_source(value: Any) -> str:
    source = to_string_value(value).lower()
    if source in {"client", "assistant"}:
        return source
    raise ValueError("source 只能是 client 或 assistant。")


def _recording_dir_for_manifest(manifest: dict[str, Any]) -> Path:
    manifest_path = to_string_value(manifest.get("_manifestPath"))
    if not manifest_path:
        raise FileNotFoundError("录音索引不存在。")
    return Path(manifest_path).parent


def _sample_rate_from_mime(mime: Any, default: int) -> int:
    match = re.search(r"rate=(\d+)", to_string_value(mime))
    if not match:
        return default
    try:
        return int(match.group(1))
    except ValueError:
        return default


def _pcm_s16le_to_wav(pcm: bytes, sample_rate: int) -> bytes:
    channel_count = 1
    bits_per_sample = 16
    byte_rate = sample_rate * channel_count * bits_per_sample // 8
    block_align = channel_count * bits_per_sample // 8
    header = b"".join(
        [
            b"RIFF",
            struct.pack("<I", 36 + len(pcm)),
            b"WAVE",
            b"fmt ",
            struct.pack("<IHHIIHH", 16, 1, channel_count, sample_rate, byte_rate, block_align, bits_per_sample),
            b"data",
            struct.pack("<I", len(pcm)),
        ]
    )
    return header + pcm


def _normalize_session_id(value: Any) -> str:
    text = to_string_value(value)
    if not text:
        raise ValueError("sessionId 不能为空。")
    if not re.fullmatch(r"[a-zA-Z0-9_-]{1,100}", text):
        raise ValueError("sessionId 格式无效。")
    return text

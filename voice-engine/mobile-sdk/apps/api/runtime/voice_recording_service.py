from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from typing import Any, BinaryIO

from ..config import LOCAL_RUNTIME_DIR
from ..shared.value_utils import to_string_value


VOICE_RECORDING_DIR = LOCAL_RUNTIME_DIR / "voice-recordings"


def is_voice_recording_enabled() -> bool:
    value = str(os.environ.get("VOICE_RECORDING_ENABLED") or "").strip().lower()
    return value in {"1", "true", "yes", "on"}


def start_voice_recording(
    session_id: str,
    metadata: dict[str, Any] | None = None,
    *,
    enabled: bool | None = None,
) -> VoiceRecordingSession | None:
    should_record = is_voice_recording_enabled() if enabled is None else enabled
    if not should_record:
        return None
    return VoiceRecordingSession(session_id, metadata or {})


class VoiceRecordingSession:
    def __init__(self, session_id: str, metadata: dict[str, Any]) -> None:
        self.session_id = _safe_text(session_id) or "session"
        self.request_id = _safe_text(metadata.get("requestId"))
        self.user_id = _safe_text(metadata.get("userId"))
        self.scene_id = _safe_text(metadata.get("sceneId"))
        self.started_at = _now_iso()
        self.ended_at = ""
        self.client_audio_bytes = 0
        self.client_audio_frames = 0
        self.assistant_audio_bytes = 0
        self.assistant_audio_frames = 0
        self.closed = False

        directory_name = f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}_{self.session_id}"
        self.directory = VOICE_RECORDING_DIR / directory_name
        self.directory.mkdir(parents=True, exist_ok=True)
        self.client_audio_path = self.directory / "client_16000_s16le.pcm"
        self.assistant_audio_path = self.directory / "assistant_24000_s16le.pcm"
        self.manifest_path = self.directory / "manifest.json"
        self._client_audio_file = self.client_audio_path.open("wb")
        self._assistant_audio_file = self.assistant_audio_path.open("wb")
        self._write_manifest("recording")

    def write_client_audio(self, audio: bytes) -> None:
        self._write_audio(self._client_audio_file, audio, "client")

    def write_assistant_audio(self, audio: bytes) -> None:
        self._write_audio(self._assistant_audio_file, audio, "assistant")

    def close(self) -> None:
        if self.closed:
            return

        self.closed = True
        self.ended_at = _now_iso()
        try:
            self._client_audio_file.close()
        finally:
            self._assistant_audio_file.close()
        self._write_manifest("closed")

    def _write_audio(self, file: BinaryIO, audio: bytes, source: str) -> None:
        if self.closed or not audio:
            return

        file.write(audio)
        file.flush()
        if source == "client":
            self.client_audio_bytes += len(audio)
            self.client_audio_frames += 1
        else:
            self.assistant_audio_bytes += len(audio)
            self.assistant_audio_frames += 1

    def _write_manifest(self, status: str) -> None:
        manifest = {
            "sessionId": self.session_id,
            "requestId": self.request_id or None,
            "userId": self.user_id,
            "sceneId": self.scene_id,
            "status": status,
            "startedAt": self.started_at,
            "endedAt": self.ended_at or None,
            "clientAudio": {
                "path": self.client_audio_path.name,
                "mime": "audio/pcm; format=s16le; rate=16000",
            },
            "assistantAudio": {
                "path": self.assistant_audio_path.name,
                "mime": "audio/pcm; format=s16le; rate=24000",
            },
            "clientAudioBytes": self.client_audio_bytes,
            "clientAudioFrames": self.client_audio_frames,
            "assistantAudioBytes": self.assistant_audio_bytes,
            "assistantAudioFrames": self.assistant_audio_frames,
        }
        self.manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def _safe_text(value: Any) -> str:
    text = to_string_value(value)
    if not text:
        return ""
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", text)[:100].strip("_")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

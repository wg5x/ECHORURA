from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .realtime.recording import LocalSessionRecorder


class ConversationStore:
    def __init__(
        self,
        base_dir: Path,
        session_id: str,
        agent_profile_id: str,
        config: dict[str, Any],
        memory_context: dict[str, Any] | None = None,
    ) -> None:
        self.base_dir = base_dir
        self.session_id = session_id
        self.agent_profile_id = agent_profile_id
        self.config = dict(config)
        self.memory_context = memory_context or {"memories": [], "system_role_text": ""}
        self.session_dir = self.base_dir / self.session_id
        self.started_at = _now()
        self.finalized = False
        self.recorder = LocalSessionRecorder(True, self.base_dir, self.session_id)
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self._write_session(ended_at="")

    def write_input_audio(self, pcm: bytes) -> None:
        self.recorder.write_input(pcm)

    def write_output_audio(self, pcm: bytes) -> None:
        self.recorder.write_output(pcm)

    def record_transcript(self, event: dict[str, Any]) -> None:
        self._append_jsonl("transcript.jsonl", event)

    def record_route_decision(self, decision: dict[str, Any]) -> None:
        self._append_jsonl("route_decisions.jsonl", decision)

    def read_transcript(self) -> list[dict[str, Any]]:
        path = self.session_dir / "transcript.jsonl"
        if not path.exists():
            return []
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def finalize(self, memory_extraction: dict[str, Any] | None = None) -> None:
        if self.finalized:
            return
        self.recorder.close()
        if memory_extraction is not None:
            self._write_json("memory_extraction.json", memory_extraction)
        self._write_session(ended_at=_now())
        self.finalized = True

    def _write_session(self, ended_at: str) -> None:
        self._write_json(
            "session.json",
            {
                "session_id": self.session_id,
                "agent_profile_id": self.agent_profile_id,
                "started_at": self.started_at,
                "ended_at": ended_at,
                "config": self.config,
                "memory_context": self.memory_context,
            },
        )

    def _write_json(self, filename: str, payload: dict[str, Any]) -> None:
        self.session_dir.mkdir(parents=True, exist_ok=True)
        (self.session_dir / filename).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def _append_jsonl(self, filename: str, payload: dict[str, Any]) -> None:
        self.session_dir.mkdir(parents=True, exist_ok=True)
        with (self.session_dir / filename).open("a", encoding="utf-8") as file:
            file.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")

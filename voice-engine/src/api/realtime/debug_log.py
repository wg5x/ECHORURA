from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


class RealtimeDebugLogger:
    def __init__(self, enabled: bool, base_dir: Path, session_id: str) -> None:
        self.enabled = enabled
        self.base_dir = base_dir
        self.session_id = session_id

    def record(self, kind: str, payload: dict[str, Any]) -> None:
        if not self.enabled:
            return

        try:
            session_dir = self.base_dir / self.session_id
            session_dir.mkdir(parents=True, exist_ok=True)
            entry = {
                "at": datetime.now().strftime("%H:%M:%S"),
                "kind": kind,
                "source": "doubao_s2s",
                "payload": payload,
            }
            with (session_dir / "events.jsonl").open("a", encoding="utf-8") as file:
                file.write(json.dumps(entry, ensure_ascii=False, separators=(",", ":")) + "\n")
        except OSError:
            return

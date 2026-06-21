from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from api.rule_audit_runner import collect_recent_sessions, run_rule_audit


class RuleAuditRunnerTest(unittest.TestCase):
    def test_collect_recent_sessions_reads_conversation_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            conversations_dir = Path(temp_dir)
            _write_session(
                conversations_dir,
                "session-a",
                agent_profile_id="phone-assistant",
                transcript=[{"role": "user", "text": "打开淘宝"}],
                route_decisions=[{"type": "route_decision", "intent": "app.open"}],
                ended_at="2026-06-21T10:00:00",
            )

            sessions = collect_recent_sessions(conversations_dir, limit=5)

        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0]["session_id"], "session-a")
        self.assertEqual(sessions[0]["agent_profile_id"], "phone-assistant")
        self.assertEqual(sessions[0]["transcript"][0]["text"], "打开淘宝")
        self.assertEqual(sessions[0]["route_decisions"][0]["intent"], "app.open")

    def test_run_rule_audit_writes_report_with_eval_summaries_and_recent_sessions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir)
            conversations_dir = base_dir / "conversations"
            reports_dir = base_dir / "reports"
            _write_session(
                conversations_dir,
                "session-a",
                agent_profile_id="phone-assistant",
                transcript=[{"role": "user", "text": "记住我喜欢女声"}],
                route_decisions=[{"type": "route_decision", "intent": "memory.preference.update"}],
                ended_at="2026-06-21T10:00:00",
            )

            report = run_rule_audit(
                conversations_dir=conversations_dir,
                reports_dir=reports_dir,
                recent_sessions_limit=3,
            )

            report_path = Path(report["report_path"])
            persisted = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(report["router_eval"]["summary"]["case_count"], 400)
            self.assertEqual(report["memory_eval"]["summary"]["case_count"], 400)
            self.assertEqual(report["recent_sessions"]["count"], 1)
            self.assertEqual(persisted["recent_sessions"]["sessions"][0]["session_id"], "session-a")


def _write_session(
    conversations_dir: Path,
    session_id: str,
    agent_profile_id: str,
    transcript: list[dict],
    route_decisions: list[dict],
    ended_at: str,
) -> None:
    session_dir = conversations_dir / session_id
    session_dir.mkdir(parents=True)
    (session_dir / "session.json").write_text(
        json.dumps(
            {
                "session_id": session_id,
                "agent_profile_id": agent_profile_id,
                "started_at": "2026-06-21T09:59:00",
                "ended_at": ended_at,
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    _write_jsonl(session_dir / "transcript.jsonl", transcript)
    _write_jsonl(session_dir / "route_decisions.jsonl", route_decisions)


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n" for record in records),
        encoding="utf-8",
    )


if __name__ == "__main__":
    unittest.main()

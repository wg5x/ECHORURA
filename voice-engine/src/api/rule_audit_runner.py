from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import get_audit_reports_dir, get_conversations_dir
from .memory_eval_runner import default_eval_cases_path as default_memory_cases_path
from .memory_eval_runner import load_eval_cases as load_memory_eval_cases
from .memory_eval_runner import load_model_memories, run_memory_eval
from .semantic_router.eval_runner import default_eval_cases_path as default_router_cases_path
from .semantic_router.eval_runner import load_eval_cases as load_router_eval_cases
from .semantic_router.eval_runner import load_model_decisions, run_router_eval


def run_rule_audit(
    conversations_dir: Path | None = None,
    reports_dir: Path | None = None,
    recent_sessions_limit: int = 20,
    router_cases_path: Path | None = None,
    memory_cases_path: Path | None = None,
    router_model_decisions_path: Path | None = None,
    memory_model_memories_path: Path | None = None,
) -> dict[str, Any]:
    conversations_dir = conversations_dir or get_conversations_dir()
    reports_dir = reports_dir or get_audit_reports_dir()
    router_cases = load_router_eval_cases(router_cases_path or default_router_cases_path())
    memory_cases = load_memory_eval_cases(memory_cases_path or default_memory_cases_path())
    router_model_decisions = (
        load_model_decisions(router_model_decisions_path) if router_model_decisions_path else None
    )
    memory_model_memories = load_model_memories(memory_model_memories_path) if memory_model_memories_path else None

    report = {
        "type": "rule_audit_report",
        "generated_at": _now(),
        "production_policy": {
            "router": "rule",
            "memory_accepted_source": "rule",
            "model_usage": "offline_audit_only",
        },
        "router_eval": run_router_eval(router_cases, model_decisions=router_model_decisions),
        "memory_eval": run_memory_eval(memory_cases, model_memories=memory_model_memories),
        "recent_sessions": {
            "source_dir": str(conversations_dir),
            "limit": recent_sessions_limit,
            "sessions": collect_recent_sessions(conversations_dir, limit=recent_sessions_limit),
        },
    }
    report["recent_sessions"]["count"] = len(report["recent_sessions"]["sessions"])

    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / f"rule-audit-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    report["report_path"] = str(report_path)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def collect_recent_sessions(conversations_dir: Path, limit: int = 20) -> list[dict[str, Any]]:
    if not conversations_dir.exists():
        return []

    sessions: list[dict[str, Any]] = []
    for session_dir in conversations_dir.iterdir():
        if not session_dir.is_dir():
            continue
        session_path = session_dir / "session.json"
        if not session_path.exists():
            continue
        session = _read_json(session_path)
        sessions.append(
            {
                "session_id": str(session.get("session_id") or session_dir.name),
                "agent_profile_id": str(session.get("agent_profile_id") or "default"),
                "started_at": session.get("started_at") or "",
                "ended_at": session.get("ended_at") or "",
                "transcript": _read_jsonl(session_dir / "transcript.jsonl"),
                "route_decisions": _read_jsonl(session_dir / "route_decisions.jsonl"),
                "memory_extraction": _read_json(session_dir / "memory_extraction.json")
                if (session_dir / "memory_extraction.json").exists()
                else {},
            }
        )

    sessions.sort(key=lambda item: str(item.get("ended_at") or item.get("started_at") or ""), reverse=True)
    return sessions[: max(0, limit)]


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run offline rule audits for router and memory extraction.")
    parser.add_argument("--conversations-dir", type=Path, default=get_conversations_dir())
    parser.add_argument("--reports-dir", type=Path, default=get_audit_reports_dir())
    parser.add_argument("--recent-sessions-limit", type=int, default=20)
    parser.add_argument("--router-model-decisions", type=Path)
    parser.add_argument("--memory-model-memories", type=Path)
    args = parser.parse_args(argv)

    report = run_rule_audit(
        conversations_dir=args.conversations_dir,
        reports_dir=args.reports_dir,
        recent_sessions_limit=args.recent_sessions_limit,
        router_model_decisions_path=args.router_model_decisions,
        memory_model_memories_path=args.memory_model_memories,
    )
    print(
        json.dumps(
            {
                "report_path": report["report_path"],
                "router": report["router_eval"]["summary"],
                "memory": report["memory_eval"]["summary"],
                "recent_sessions": report["recent_sessions"]["count"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


if __name__ == "__main__":
    main()

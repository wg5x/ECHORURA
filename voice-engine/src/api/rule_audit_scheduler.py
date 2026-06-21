from __future__ import annotations

import argparse
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .config import get_audit_reports_dir, get_conversations_dir
from .rule_audit_runner import run_rule_audit


def run_scheduler(
    run_once: Callable[[], Any],
    interval_seconds: int,
    max_runs: int | None = None,
    sleep: Callable[[float], Any] = time.sleep,
) -> None:
    runs = 0
    while max_runs is None or runs < max_runs:
        run_once()
        runs += 1
        if max_runs is not None and runs >= max_runs:
            return
        sleep(interval_seconds)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run rule audits on a fixed interval.")
    parser.add_argument("--interval-seconds", type=int, default=24 * 60 * 60)
    parser.add_argument("--max-runs", type=int)
    parser.add_argument("--conversations-dir", type=Path, default=get_conversations_dir())
    parser.add_argument("--reports-dir", type=Path, default=get_audit_reports_dir())
    parser.add_argument("--recent-sessions-limit", type=int, default=20)
    args = parser.parse_args(argv)

    run_scheduler(
        run_once=lambda: run_rule_audit(
            conversations_dir=args.conversations_dir,
            reports_dir=args.reports_dir,
            recent_sessions_limit=args.recent_sessions_limit,
        ),
        interval_seconds=max(1, args.interval_seconds),
        max_runs=args.max_runs,
    )


if __name__ == "__main__":
    main()

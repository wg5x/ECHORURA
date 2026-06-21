from __future__ import annotations

import argparse
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from .config import get_audit_reports_dir, get_conversations_dir


def prune_old_paths(base_dir: Path, older_than_days: int, now: datetime | None = None, apply: bool = False) -> dict[str, Any]:
    now = now or datetime.now()
    cutoff = now - timedelta(days=max(0, older_than_days))
    matched: list[str] = []
    deleted: list[str] = []

    if not base_dir.exists():
        return {"base_dir": str(base_dir), "older_than_days": older_than_days, "matched": [], "deleted": [], "apply": apply}

    for path in sorted(base_dir.iterdir()):
        if _mtime(path) >= cutoff:
            continue
        matched.append(str(path))
        if apply:
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
            deleted.append(str(path))

    return {
        "base_dir": str(base_dir),
        "older_than_days": older_than_days,
        "matched": matched,
        "deleted": deleted,
        "apply": apply,
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Prune old local voice-engine data.")
    parser.add_argument("--conversations-days", type=int, default=30)
    parser.add_argument("--audit-reports-days", type=int, default=30)
    parser.add_argument("--apply", action="store_true", help="Delete matched paths. Without this flag, dry-run only.")
    args = parser.parse_args(argv)

    results = {
        "conversations": prune_old_paths(get_conversations_dir(), args.conversations_days, apply=args.apply),
        "audit_reports": prune_old_paths(get_audit_reports_dir(), args.audit_reports_days, apply=args.apply),
    }
    import json

    print(json.dumps(results, ensure_ascii=False, indent=2))


def _mtime(path: Path) -> datetime:
    return datetime.fromtimestamp(path.stat().st_mtime)


if __name__ == "__main__":
    main()

from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from api.data_retention_runner import prune_old_paths


class DataRetentionRunnerTest(unittest.TestCase):
    def test_prune_old_paths_dry_run_reports_without_deleting(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir)
            old_dir = base_dir / "old-session"
            old_dir.mkdir()
            (old_dir / "session.json").write_text("{}", encoding="utf-8")
            old_time = datetime(2026, 6, 1).timestamp()
            _set_mtime(old_dir, old_time)
            _set_mtime(old_dir / "session.json", old_time)

            result = prune_old_paths(
                base_dir=base_dir,
                older_than_days=7,
                now=datetime(2026, 6, 21),
                apply=False,
            )

            self.assertEqual(result["matched"], [str(old_dir)])
            self.assertTrue(old_dir.exists())

    def test_prune_old_paths_deletes_when_apply_is_true(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir)
            old_dir = base_dir / "old-session"
            old_dir.mkdir()
            old_time = datetime(2026, 6, 1).timestamp()
            (old_dir / "session.json").write_text("{}", encoding="utf-8")
            old_dir.touch()
            for path in (old_dir, old_dir / "session.json"):
                path.touch()
            _set_mtime(old_dir, old_time)
            _set_mtime(old_dir / "session.json", old_time)

            result = prune_old_paths(
                base_dir=base_dir,
                older_than_days=7,
                now=datetime(2026, 6, 21),
                apply=True,
            )

            self.assertEqual(result["deleted"], [str(old_dir)])
            self.assertFalse(old_dir.exists())

    def test_prune_old_paths_keeps_recent_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir)
            recent_dir = base_dir / "recent-session"
            recent_dir.mkdir()
            recent_time = (datetime(2026, 6, 21) - timedelta(days=1)).timestamp()
            _set_mtime(recent_dir, recent_time)

            result = prune_old_paths(
                base_dir=base_dir,
                older_than_days=7,
                now=datetime(2026, 6, 21),
                apply=True,
            )

            self.assertEqual(result["matched"], [])
            self.assertTrue(recent_dir.exists())


def _set_mtime(path: Path, timestamp: float) -> None:
    import os

    os.utime(path, (timestamp, timestamp))


if __name__ == "__main__":
    unittest.main()

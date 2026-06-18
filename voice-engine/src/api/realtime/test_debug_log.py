import json
import tempfile
import unittest
from pathlib import Path

from .debug_log import RealtimeDebugLogger


class RealtimeDebugLoggerTest(unittest.TestCase):
    def test_disabled_logger_does_not_write_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            logger = RealtimeDebugLogger(False, Path(temp_dir), "session-1")
            logger.record("status", {"status": "connected"})

            self.assertEqual(list(Path(temp_dir).iterdir()), [])

    def test_enabled_logger_writes_jsonl_events(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            logger = RealtimeDebugLogger(True, Path(temp_dir), "session-1")
            logger.record("status", {"status": "connected"})
            logger.record("voice_turn_text", {"role": "user", "text": "你好"})

            log_path = Path(temp_dir) / "session-1" / "events.jsonl"
            events = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]

        self.assertEqual(events[0]["kind"], "status")
        self.assertEqual(events[0]["payload"], {"status": "connected"})
        self.assertEqual(events[0]["source"], "doubao_s2s")
        self.assertRegex(events[0]["at"], r"^\d{2}:\d{2}:\d{2}$")
        self.assertEqual(events[1]["kind"], "voice_turn_text")
        self.assertEqual(events[1]["payload"], {"role": "user", "text": "你好"})

    def test_log_write_failure_does_not_raise(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            invalid_base_dir = Path(temp_dir) / "not-a-directory"
            invalid_base_dir.write_text("", encoding="utf-8")
            logger = RealtimeDebugLogger(True, invalid_base_dir, "session-1")

            logger.record("status", {"status": "connected"})


if __name__ == "__main__":
    unittest.main()

import os
import unittest
from pathlib import Path
from unittest.mock import patch

from .config import (
    SRC_DIR,
    get_audit_reports_dir,
    get_conversations_dir,
    get_debug_events_dir,
    get_memories_dir,
    get_recordings_dir,
    is_realtime_debug_log_enabled,
    is_voice_recording_enabled,
)


class RecordingConfigTest(unittest.TestCase):
    def test_recording_is_disabled_by_default(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(is_voice_recording_enabled())

    def test_recording_is_enabled_only_by_true_string(self) -> None:
        with patch.dict(os.environ, {"VOICE_RECORDING_ENABLED": "true"}, clear=True):
            self.assertTrue(is_voice_recording_enabled())

    def test_recordings_relative_dir_is_resolved_under_src_dir(self) -> None:
        with patch.dict(os.environ, {"VOICE_RECORDINGS_DIR": "data/recordings"}, clear=True):
            self.assertEqual(get_recordings_dir(), SRC_DIR / "data" / "recordings")

    def test_recordings_absolute_dir_is_preserved(self) -> None:
        with patch.dict(os.environ, {"VOICE_RECORDINGS_DIR": "/tmp/voice-engine-recordings"}, clear=True):
            self.assertEqual(get_recordings_dir(), Path("/tmp/voice-engine-recordings"))

    def test_realtime_debug_log_is_disabled_by_default(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(is_realtime_debug_log_enabled())

    def test_realtime_debug_log_is_enabled_only_by_true_string(self) -> None:
        with patch.dict(os.environ, {"VOICE_DEBUG_LOG_ENABLED": "true"}, clear=True):
            self.assertTrue(is_realtime_debug_log_enabled())

    def test_debug_events_relative_dir_is_resolved_under_src_dir(self) -> None:
        with patch.dict(os.environ, {"VOICE_DEBUG_LOG_DIR": "data/debug-events"}, clear=True):
            self.assertEqual(get_debug_events_dir(), SRC_DIR / "data" / "debug-events")

    def test_debug_events_absolute_dir_is_preserved(self) -> None:
        with patch.dict(os.environ, {"VOICE_DEBUG_LOG_DIR": "/tmp/voice-engine-debug-events"}, clear=True):
            self.assertEqual(get_debug_events_dir(), Path("/tmp/voice-engine-debug-events"))

    def test_conversations_relative_dir_is_resolved_under_src_dir(self) -> None:
        with patch.dict(os.environ, {"VOICE_CONVERSATIONS_DIR": "data/conversations"}, clear=True):
            self.assertEqual(get_conversations_dir(), SRC_DIR / "data" / "conversations")

    def test_conversations_absolute_dir_is_preserved(self) -> None:
        with patch.dict(os.environ, {"VOICE_CONVERSATIONS_DIR": "/tmp/voice-engine-conversations"}, clear=True):
            self.assertEqual(get_conversations_dir(), Path("/tmp/voice-engine-conversations"))

    def test_memories_relative_dir_is_resolved_under_src_dir(self) -> None:
        with patch.dict(os.environ, {"VOICE_MEMORIES_DIR": "data/memories"}, clear=True):
            self.assertEqual(get_memories_dir(), SRC_DIR / "data" / "memories")

    def test_memories_absolute_dir_is_preserved(self) -> None:
        with patch.dict(os.environ, {"VOICE_MEMORIES_DIR": "/tmp/voice-engine-memories"}, clear=True):
            self.assertEqual(get_memories_dir(), Path("/tmp/voice-engine-memories"))

    def test_audit_reports_relative_dir_is_resolved_under_src_dir(self) -> None:
        with patch.dict(os.environ, {"VOICE_AUDIT_REPORTS_DIR": "data/audit-reports"}, clear=True):
            self.assertEqual(get_audit_reports_dir(), SRC_DIR / "data" / "audit-reports")

    def test_audit_reports_absolute_dir_is_preserved(self) -> None:
        with patch.dict(os.environ, {"VOICE_AUDIT_REPORTS_DIR": "/tmp/voice-engine-audit-reports"}, clear=True):
            self.assertEqual(get_audit_reports_dir(), Path("/tmp/voice-engine-audit-reports"))


if __name__ == "__main__":
    unittest.main()

import os
import unittest
from pathlib import Path
from unittest.mock import patch

from .config import SRC_DIR, get_recordings_dir, is_voice_recording_enabled


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
        with patch.dict(os.environ, {"VOICE_RECORDINGS_DIR": "/tmp/echorura-recordings"}, clear=True):
            self.assertEqual(get_recordings_dir(), Path("/tmp/echorura-recordings"))


if __name__ == "__main__":
    unittest.main()

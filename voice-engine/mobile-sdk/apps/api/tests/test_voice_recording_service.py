import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from apps.api.runtime.voice_recording_service import is_voice_recording_enabled, start_voice_recording


class VoiceRecordingServiceTest(unittest.TestCase):
    def test_voice_recording_disabled_by_default(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with (
                patch("apps.api.runtime.voice_recording_service.VOICE_RECORDING_DIR", Path(temp_dir)),
                patch.dict("os.environ", {}, clear=True),
            ):
                session = start_voice_recording("session-1", {"userId": "user_1", "sceneId": "scene_1"})

                self.assertIsNone(session)
                self.assertEqual(list(Path(temp_dir).iterdir()), [])
                self.assertFalse(is_voice_recording_enabled())

    def test_voice_recording_false_values_stay_disabled(self):
        for value in ("false", "0", "no", "off"):
            with self.subTest(value=value):
                with patch.dict("os.environ", {"VOICE_RECORDING_ENABLED": value}, clear=True):
                    self.assertFalse(is_voice_recording_enabled())

    def test_voice_recording_enabled_writes_pcm_and_manifest(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with (
                patch("apps.api.runtime.voice_recording_service.VOICE_RECORDING_DIR", Path(temp_dir)),
                patch.dict("os.environ", {"VOICE_RECORDING_ENABLED": "true"}, clear=True),
            ):
                session = start_voice_recording("session-1", {"userId": "user_1", "sceneId": "scene_1", "requestId": "request_1"})
                self.assertIsNotNone(session)

                session.write_client_audio(b"\x01\x02")
                session.write_assistant_audio(b"\x03\x04\x05\x06")
                session.close()

                recording_dirs = list(Path(temp_dir).iterdir())
                self.assertEqual(len(recording_dirs), 1)
                recording_dir = recording_dirs[0]
                self.assertEqual((recording_dir / "client_16000_s16le.pcm").read_bytes(), b"\x01\x02")
                self.assertEqual((recording_dir / "assistant_24000_s16le.pcm").read_bytes(), b"\x03\x04\x05\x06")

                manifest = json.loads((recording_dir / "manifest.json").read_text(encoding="utf-8"))
                self.assertEqual(manifest["sessionId"], "session-1")
                self.assertEqual(manifest["requestId"], "request_1")
                self.assertEqual(manifest["userId"], "user_1")
                self.assertEqual(manifest["sceneId"], "scene_1")
                self.assertEqual(manifest["clientAudioBytes"], 2)
                self.assertEqual(manifest["assistantAudioBytes"], 4)


if __name__ == "__main__":
    unittest.main()

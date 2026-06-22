import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from apps.api.runtime.call_log_service import save_call_log
from apps.api.runtime.session_result_service import (
    build_session_audio_wav,
    get_session_result,
)


class SessionResultServiceTest(unittest.TestCase):
    def test_get_session_result_returns_transcript_by_session_id(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with (
                patch("apps.api.runtime.call_log_service.CALL_LOG_DIR", Path(temp_dir) / "call-logs"),
                patch("apps.api.runtime.session_result_service.CALL_LOG_DIR", Path(temp_dir) / "call-logs"),
                patch("apps.api.runtime.session_result_service.VOICE_RECORDING_DIR", Path(temp_dir) / "voice-recordings"),
            ):
                save_call_log(
                    {
                        "id": "log-1",
                        "sessionId": "session-1",
                        "requestId": "request-1",
                        "userId": "scene_route",
                        "sceneId": "hs6_user_interview",
                        "report": {
                            "id": "log-1",
                            "startedAt": "10:00:00",
                            "endedAt": "10:01:00",
                            "transcript": [
                                {"role": "assistant", "text": "您好", "at": "10:00:01"},
                                {"role": "user", "text": "我在杭州", "at": "10:00:03"},
                            ],
                        },
                    }
                )

                result = get_session_result("session-1")

                self.assertEqual(result["sessionId"], "session-1")
                self.assertEqual(result["requestId"], "request-1")
                self.assertEqual(result["sceneId"], "hs6_user_interview")
                self.assertEqual(result["status"], "finished")
                self.assertEqual(result["transcript"][1]["text"], "我在杭州")
                self.assertIsNone(result["audio"])

    def test_get_session_result_includes_audio_url_when_recording_exists(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            recording_dir = Path(temp_dir) / "voice-recordings" / "20260618_session-1"
            recording_dir.mkdir(parents=True)
            (recording_dir / "client_16000_s16le.pcm").write_bytes(b"\x00\x00\x01\x00")
            (recording_dir / "manifest.json").write_text(
                json.dumps(
                    {
                        "sessionId": "session-1",
                        "sceneId": "hs6_user_interview",
                        "status": "closed",
                        "clientAudio": {
                            "path": "client_16000_s16le.pcm",
                            "mime": "audio/pcm; format=s16le; rate=16000",
                        },
                        "clientAudioBytes": 4,
                    }
                ),
                encoding="utf-8",
            )
            with (
                patch("apps.api.runtime.session_result_service.CALL_LOG_DIR", Path(temp_dir) / "call-logs"),
                patch("apps.api.runtime.session_result_service.VOICE_RECORDING_DIR", Path(temp_dir) / "voice-recordings"),
            ):
                result = get_session_result("session-1")

                self.assertEqual(result["audio"]["url"], "/runtime/sessions/session-1/audio")
                self.assertEqual(result["audio"]["mime"], "audio/wav")
                self.assertEqual(result["audio"]["source"], "client")

    def test_build_session_audio_wav_wraps_pcm_for_browser_playback(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            recording_dir = Path(temp_dir) / "voice-recordings" / "20260618_session-1"
            recording_dir.mkdir(parents=True)
            (recording_dir / "client_16000_s16le.pcm").write_bytes(b"\x00\x00\x01\x00")
            (recording_dir / "manifest.json").write_text(
                json.dumps(
                    {
                        "sessionId": "session-1",
                        "clientAudio": {
                            "path": "client_16000_s16le.pcm",
                            "mime": "audio/pcm; format=s16le; rate=16000",
                        },
                    }
                ),
                encoding="utf-8",
            )
            with patch("apps.api.runtime.session_result_service.VOICE_RECORDING_DIR", Path(temp_dir) / "voice-recordings"):
                wav = build_session_audio_wav("session-1")

                self.assertEqual(wav[:4], b"RIFF")
                self.assertEqual(wav[8:12], b"WAVE")
                self.assertEqual(wav[-4:], b"\x00\x00\x01\x00")

    def test_build_session_audio_wav_can_return_assistant_audio(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            recording_dir = Path(temp_dir) / "voice-recordings" / "20260618_session-1"
            recording_dir.mkdir(parents=True)
            (recording_dir / "client_16000_s16le.pcm").write_bytes(b"\x00\x00")
            (recording_dir / "assistant_24000_s16le.pcm").write_bytes(b"\x03\x00\x04\x00")
            (recording_dir / "manifest.json").write_text(
                json.dumps(
                    {
                        "sessionId": "session-1",
                        "clientAudio": {
                            "path": "client_16000_s16le.pcm",
                            "mime": "audio/pcm; format=s16le; rate=16000",
                        },
                        "assistantAudio": {
                            "path": "assistant_24000_s16le.pcm",
                            "mime": "audio/pcm; format=s16le; rate=24000",
                        },
                    }
                ),
                encoding="utf-8",
            )
            with patch("apps.api.runtime.session_result_service.VOICE_RECORDING_DIR", Path(temp_dir) / "voice-recordings"):
                wav = build_session_audio_wav("session-1", source="assistant")

                self.assertEqual(wav[:4], b"RIFF")
                self.assertEqual(wav[-4:], b"\x03\x00\x04\x00")


if __name__ == "__main__":
    unittest.main()

import os
import unittest
from unittest.mock import patch

from .payload import DEFAULT_O2_SPEAKER, DEFAULT_SC2_SPEAKER, build_start_session_payload


class StartSessionPayloadTest(unittest.TestCase):
    def test_default_payload_uses_o2_speaker_and_dialog_settings(self) -> None:
        with patch.dict(os.environ, {"VOLC_WEBSEARCH_API_KEY": "test-key"}, clear=True):
            result = build_start_session_payload()

        self.assertEqual(result["config"]["mode"], "o2")
        self.assertEqual(result["payload"]["tts"]["speaker"], DEFAULT_O2_SPEAKER)
        self.assertEqual(result["payload"]["dialog"]["bot_name"], "ECHORURA")
        self.assertEqual(result["warnings"], [])

    def test_warns_when_websearch_is_enabled_without_key(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            result = build_start_session_payload({"enableWebSearch": True})

        self.assertEqual(
            result["warnings"],
            ["已开启联网能力，但后端未配置 VOLC_WEBSEARCH_API_KEY；真实联网请求会被火山 API 拒绝。"],
        )

    def test_warns_when_o2_speaker_is_not_in_allowlist(self) -> None:
        with patch.dict(os.environ, {"VOLC_WEBSEARCH_API_KEY": "test-key"}, clear=True):
            result = build_start_session_payload({"mode": "o2", "speaker": "unknown-speaker"})

        self.assertEqual(
            result["warnings"],
            ["当前音色不在端到端实时语音大模型 S2S-O 官方音色列表中，可能被火山 API 拒绝。"],
        )

    def test_warns_when_sc2_speaker_is_not_in_allowlist(self) -> None:
        with patch.dict(os.environ, {"VOLC_WEBSEARCH_API_KEY": "test-key"}, clear=True):
            result = build_start_session_payload({"mode": "sc2", "speaker": "unknown-speaker"})

        self.assertEqual(
            result["warnings"],
            ["当前音色不在端到端实时语音大模型 SC 2.0 官方音色列表中，可能被火山 API 拒绝。"],
        )

    def test_sc2_uses_character_manifest_and_disables_music(self) -> None:
        with patch.dict(os.environ, {"VOLC_WEBSEARCH_API_KEY": "test-key"}, clear=True):
            result = build_start_session_payload(
                {
                    "mode": "sc2",
                    "speaker": DEFAULT_SC2_SPEAKER,
                    "characterManifest": "你是一个简短回复的中文语音助手。",
                    "enableMusic": True,
                }
            )

        self.assertEqual(result["config"]["mode"], "sc2")
        self.assertFalse(result["config"]["enableMusic"])
        self.assertEqual(result["payload"]["tts"]["speaker"], DEFAULT_SC2_SPEAKER)
        self.assertEqual(result["payload"]["dialog"]["character_manifest"], "你是一个简短回复的中文语音助手。")
        self.assertNotIn("enable_music", result["payload"]["dialog"]["extra"])


if __name__ == "__main__":
    unittest.main()

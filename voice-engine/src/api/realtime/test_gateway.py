import asyncio
import json
import unittest

from ..integrations.volc.frames import ServerFrame
from .gateway import (
    RealtimeGateway,
    _clean_display_text,
    _make_audio_latency_debug_payload,
    _make_transcript_event,
    _make_upstream_debug_payload,
    _make_voice_turn_text_event,
    _merge_asr_text,
)


class AsrTextMergeTest(unittest.TestCase):
    def test_replaces_partial_with_punctuated_final_text(self) -> None:
        first = "哎你刚才说出门记得防晒这件事不是有点废话吗我问的你今天多少度"
        second = "哎，你刚才说出门记得防晒这件事不是有点废话吗？我问的你今天多少度？"

        self.assertEqual(_merge_asr_text(first, second), second)

    def test_keeps_single_line_when_final_text_repeats(self) -> None:
        text = "今天上海多少度？"

        self.assertEqual(_merge_asr_text(text, text), text)

    def test_replaces_short_partial_with_longer_revision(self) -> None:
        first = "今天上海多少度"
        second = "今天上海多少度，适合出门吗？"

        self.assertEqual(_merge_asr_text(first, second), second)

    def test_keeps_previous_text_when_asr_rolls_back_to_shorter_fragment(self) -> None:
        first = "今天上海多少度，适合出门吗？"
        second = "上海多少度"

        self.assertEqual(_merge_asr_text(first, second), first)

    def test_merges_real_tail_content_by_overlap(self) -> None:
        first = "麻烦帮我播放周杰伦的歌"
        second = "周杰伦的歌曲晴天"

        self.assertEqual(_merge_asr_text(first, second), "麻烦帮我播放周杰伦的歌曲晴天")


class DisplayTextCleanTest(unittest.TestCase):
    def test_removes_spaces_between_chinese_characters(self) -> None:
        text = "我 在 用心 的 来 爱着 你 ， 为何 不见 你 对 我 用 真情"

        self.assertEqual(_clean_display_text(text), "我在用心的来爱着你，为何不见你对我用真情")

    def test_keeps_spaces_between_latin_words(self) -> None:
        text = "Play the song Hello World"

        self.assertEqual(_clean_display_text(text), "Play the song Hello World")


class VoiceTurnTextEventTest(unittest.TestCase):
    def test_builds_standard_voice_turn_text_event(self) -> None:
        event = _make_voice_turn_text_event(
            session_id="session-1",
            turn_id="turn-1",
            role="user",
            text="帮我做一首歌",
            output_id="user-output-1",
        )

        self.assertEqual(event["type"], "voice_turn_text")
        self.assertEqual(event["session_id"], "session-1")
        self.assertEqual(event["turn_id"], "turn-1")
        self.assertEqual(event["role"], "user")
        self.assertEqual(event["text"], "帮我做一首歌")
        self.assertEqual(event["source"], "doubao_s2s")
        self.assertEqual(event["output_id"], "user-output-1")
        self.assertRegex(event["at"], r"^\d{2}:\d{2}:\d{2}$")


class TranscriptEventTest(unittest.TestCase):
    def test_builds_standard_transcript_event(self) -> None:
        event = _make_transcript_event(
            session_id="session-1",
            turn_id="turn-1",
            role="user",
            text="帮我做一首歌",
            output_id="user-output-1",
        )

        self.assertEqual(event["type"], "transcript_event")
        self.assertEqual(event["session_id"], "session-1")
        self.assertEqual(event["turn_id"], "turn-1")
        self.assertEqual(event["role"], "user")
        self.assertEqual(event["text"], "帮我做一首歌")
        self.assertEqual(event["source"], "doubao_s2s")
        self.assertEqual(event["output_id"], "user-output-1")
        self.assertRegex(event["at"], r"^\d{2}:\d{2}:\d{2}$")


class GatewayDebugLogTest(unittest.TestCase):
    def test_user_asr_sends_frontend_event_voice_turn_and_transcript_event(self) -> None:
        client_ws = _FakeClientWebSocket()
        gateway = RealtimeGateway(client_ws)
        gateway.session_id = "session-1"

        asyncio.run(gateway._handle_user_asr_text("帮 我 做 一 首 歌"))

        sent_types = [json.loads(message)["type"] for message in client_ws.sent]
        self.assertEqual(sent_types, ["event", "voice_turn_text", "transcript_event", "route_decision"])
        transcript = json.loads(client_ws.sent[2])
        self.assertEqual(transcript["text"], "帮我做一首歌")
        self.assertEqual(transcript["role"], "user")
        self.assertEqual(transcript["source"], "doubao_s2s")
        decision = json.loads(client_ws.sent[3])
        self.assertEqual(decision["mode"], "scenario")
        self.assertEqual(decision["scenario_id"], "music_creation")
        self.assertEqual(decision["scenario_intent"], "create_song")

    def test_send_json_records_standardized_voice_turn_text(self) -> None:
        logger = _FakeDebugLogger()
        client_ws = _FakeClientWebSocket()
        gateway = RealtimeGateway(client_ws)
        gateway.debug_logger = logger

        asyncio.run(
            gateway._send_json(
                {
                    "type": "voice_turn_text",
                    "session_id": "session-1",
                    "turn_id": "turn-1",
                    "role": "user",
                    "text": "帮我做一首歌",
                    "source": "doubao_s2s",
                    "output_id": "user-output-1",
                    "at": "10:00:00",
                }
            )
        )

        self.assertEqual(logger.records, [("voice_turn_text", {"role": "user", "text": "帮我做一首歌", "turn_id": "turn-1"})])

    def test_send_json_records_standardized_transcript_event(self) -> None:
        logger = _FakeDebugLogger()
        client_ws = _FakeClientWebSocket()
        gateway = RealtimeGateway(client_ws)
        gateway.debug_logger = logger

        asyncio.run(
            gateway._send_json(
                {
                    "type": "transcript_event",
                    "session_id": "session-1",
                    "turn_id": "turn-1",
                    "role": "assistant",
                    "text": "好的，我来做。",
                    "source": "doubao_s2s",
                    "output_id": "assistant-output-1",
                    "at": "10:00:00",
                }
            )
        )

        self.assertEqual(
            logger.records,
            [("transcript_event", {"role": "assistant", "text": "好的，我来做。", "turn_id": "turn-1"})],
        )

    def test_upstream_debug_payload_keeps_error_code_and_summarizes_binary_payload(self) -> None:
        frame = ServerFrame(code=403, event=153, message_type=0x0F, session_id="session-1", payload=b"\x00\x01\x02")

        payload = _make_upstream_debug_payload(frame)

        self.assertEqual(payload["code"], 403)
        self.assertEqual(payload["event"], 153)
        self.assertEqual(payload["message_type"], 0x0F)
        self.assertEqual(payload["session_id"], "session-1")
        self.assertEqual(payload["payload_bytes"], 3)
        self.assertNotIn("payload", payload)

    def test_audio_latency_debug_payload_uses_milliseconds(self) -> None:
        payload = _make_audio_latency_debug_payload(
            session_id="session-1",
            session_started_at=10.0,
            first_audio_at=10.247,
            payload_bytes=960,
        )

        self.assertEqual(payload["session_id"], "session-1")
        self.assertEqual(payload["latency_ms"], 247)
        self.assertEqual(payload["payload_bytes"], 960)


class _FakeClientWebSocket:
    def __init__(self) -> None:
        self.sent: list[str] = []

    async def send_text(self, text: str) -> None:
        self.sent.append(text)


class _FakeDebugLogger:
    def __init__(self) -> None:
        self.records: list[tuple[str, dict[str, str]]] = []

    def record(self, kind: str, payload: dict[str, str]) -> None:
        self.records.append((kind, payload))


if __name__ == "__main__":
    unittest.main()

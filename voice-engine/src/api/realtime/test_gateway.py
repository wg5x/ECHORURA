import asyncio
import json
import unittest
from pathlib import Path
from unittest.mock import patch

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

    def test_user_asr_uses_selected_agent_profile_for_route_decision(self) -> None:
        client_ws = _FakeClientWebSocket()
        gateway = RealtimeGateway(client_ws)
        gateway.session_id = "session-1"
        gateway.agent_profile_id = "phone-assistant"

        asyncio.run(gateway._handle_user_asr_text("打开淘宝"))

        decision = json.loads(client_ws.sent[3])
        self.assertEqual(decision["agent_profile_id"], "phone-assistant")
        self.assertEqual(decision["mode"], "native_action")
        self.assertEqual(decision["intent"], "app.open")

    def test_user_asr_falls_back_to_chat_when_router_fails(self) -> None:
        client_ws = _FakeClientWebSocket()
        logger = _FakeDebugLogger()
        gateway = RealtimeGateway(client_ws)
        gateway.session_id = "session-1"
        gateway.semantic_router = _FailingSemanticRouter()
        gateway.debug_logger = logger

        asyncio.run(gateway._handle_user_asr_text("打开淘宝"))

        sent = [json.loads(message) for message in client_ws.sent]
        self.assertEqual([message["type"] for message in sent], ["event", "voice_turn_text", "transcript_event", "route_decision"])
        self.assertEqual(sent[3]["mode"], "chat")
        self.assertEqual(sent[3]["intent"], "general")
        self.assertIn("error", [kind for kind, _payload in logger.records])

    def test_start_message_stores_selected_agent_profile(self) -> None:
        gateway = RealtimeGateway(_FakeClientWebSocket())
        message = {"type": "start", "agent_profile_id": "phone-assistant"}

        gateway._set_agent_profile_from_message(message)

        self.assertEqual(gateway.agent_profile_id, "phone-assistant")

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

    def test_normalizes_dialog_audio_idle_timeout_error(self) -> None:
        client_ws = _FakeClientWebSocket()
        gateway = RealtimeGateway(client_ws)

        asyncio.run(gateway._send_upstream_error("sami error: codes=52000042, desc=DialogAudioIdleTimeoutError"))

        messages = [json.loads(message) for message in client_ws.sent]
        self.assertEqual(messages[0]["type"], "error")
        self.assertEqual(messages[0]["message"], "实时语音会话已空闲超时。请重新开始通话后直接说话，或使用下方文本测试。")
        self.assertEqual(messages[1], {"type": "status", "status": "idle"})

    def test_start_message_injects_memory_context_into_system_role(self) -> None:
        client_ws = _FakeClientWebSocket()
        gateway = RealtimeGateway(client_ws)
        gateway.memory_store = _FakeMemoryStore(
            context={
                "agent_profile_id": "phone-assistant",
                "memories": [{"content": "我喜欢女声"}],
                "system_role_text": "长期记忆：\n- 我喜欢女声",
            }
        )
        started_sessions: list[dict] = []

        async def capture_start(session: dict) -> None:
            started_sessions.append(session)

        gateway._start_volc_session = capture_start

        with patch("api.realtime.gateway.has_volc_credentials", return_value=True):
            asyncio.run(
                gateway._handle_text(
                    json.dumps(
                        {
                            "type": "start",
                            "agent_profile_id": "phone-assistant",
                            "memory_session_ids": ["session-b", "session-a"],
                            "config": {"systemRole": "你是手机助手。"},
                        },
                        ensure_ascii=False,
                    )
                )
            )

        self.assertEqual(gateway.memory_store.context_requests, [("phone-assistant", ["session-b", "session-a"])])
        self.assertEqual(gateway.memory_context["memories"][0]["content"], "我喜欢女声")
        self.assertEqual(gateway.memory_context["session_ids"], ["session-b", "session-a"])
        self.assertEqual(started_sessions[0]["config"]["systemRole"], "你是手机助手。\n\n长期记忆：\n- 我喜欢女声")

    def test_send_json_records_transcript_and_route_to_conversation_store(self) -> None:
        client_ws = _FakeClientWebSocket()
        gateway = RealtimeGateway(client_ws)
        conversation_store = _FakeConversationStore()
        gateway.conversation_store = conversation_store

        asyncio.run(
            gateway._send_json(
                {
                    "type": "transcript_event",
                    "session_id": "session-1",
                    "turn_id": "turn-1",
                    "role": "user",
                    "text": "记住我喜欢女声",
                    "source": "doubao_s2s",
                    "output_id": "user-output-1",
                    "at": "10:00:00",
                }
            )
        )
        asyncio.run(
            gateway._send_json(
                {
                    "type": "route_decision",
                    "session_id": "session-1",
                    "turn_id": "turn-1",
                    "agent_profile_id": "phone-assistant",
                    "mode": "chat",
                    "intent": "general",
                }
            )
        )

        self.assertEqual(conversation_store.transcripts[0]["text"], "记住我喜欢女声")
        self.assertEqual(conversation_store.route_decisions[0]["intent"], "general")

    def test_handle_binary_records_input_audio_to_conversation_store(self) -> None:
        gateway = RealtimeGateway(_FakeClientWebSocket())
        gateway.session_id = "session-1"
        gateway.upstream = _FakeUpstream()
        conversation_store = _FakeConversationStore()
        gateway.conversation_store = conversation_store

        asyncio.run(gateway._handle_binary(b"\x01\x02"))

        self.assertEqual(conversation_store.input_audio, [b"\x01\x02"])

    def test_user_text_records_transcript_for_memory_extraction(self) -> None:
        gateway = RealtimeGateway(_FakeClientWebSocket())
        gateway.session_id = "session-1"
        gateway.upstream = _FakeUpstream()
        conversation_store = _FakeConversationStore()
        gateway.conversation_store = conversation_store

        asyncio.run(gateway._handle_text(json.dumps({"type": "user_text", "text": "记住我喜欢女生"}, ensure_ascii=False)))

        self.assertEqual(conversation_store.transcripts[0]["role"], "user")
        self.assertEqual(conversation_store.transcripts[0]["text"], "记住我喜欢女生")

    def test_user_text_does_not_merge_into_next_asr_turn(self) -> None:
        client_ws = _FakeClientWebSocket()
        gateway = RealtimeGateway(client_ws)
        gateway.session_id = "session-1"
        gateway.upstream = _FakeUpstream()
        conversation_store = _FakeConversationStore()
        gateway.conversation_store = conversation_store

        asyncio.run(gateway._handle_text(json.dumps({"type": "user_text", "text": "请记住我的微信号是123456"}, ensure_ascii=False)))
        asyncio.run(gateway._handle_user_asr_text("打开淘宝"))

        user_event = json.loads(client_ws.sent[0])
        self.assertEqual(user_event["event"]["text"], "打开淘宝")
        self.assertEqual(user_event["event"]["outputId"], "user-output-2")
        self.assertEqual([item["text"] for item in conversation_store.transcripts], ["请记住我的微信号是123456", "打开淘宝"])

    def test_user_text_send_failure_does_not_record_transcript_for_memory(self) -> None:
        client_ws = _FakeClientWebSocket()
        gateway = RealtimeGateway(client_ws)
        gateway.session_id = "session-1"
        gateway.upstream = _FailingUpstream()
        conversation_store = _FakeConversationStore()
        gateway.conversation_store = conversation_store

        asyncio.run(gateway._handle_text(json.dumps({"type": "user_text", "text": "记住我的手机号是123456"}, ensure_ascii=False)))

        self.assertEqual(conversation_store.transcripts, [])
        self.assertEqual(json.loads(client_ws.sent[0])["type"], "error")

    def test_close_finalizes_conversation_and_persists_memory(self) -> None:
        gateway = RealtimeGateway(_FakeClientWebSocket())
        gateway.session_id = "session-1"
        gateway.agent_profile_id = "phone-assistant"
        gateway.memory_store = _FakeMemoryStore()
        conversation_store = _FakeConversationStore(
            transcripts=[
                {"role": "user", "text": "记住我喜欢女声"},
                {"role": "assistant", "text": "好的，我记住了。"},
            ]
        )
        gateway.conversation_store = conversation_store

        asyncio.run(gateway._close_upstream())

        self.assertEqual(
            gateway.memory_store.extraction_requests,
            [
                (
                    "session-1",
                    "phone-assistant",
                    [
                        {"role": "user", "text": "记住我喜欢女声"},
                        {"role": "assistant", "text": "好的，我记住了。"},
                    ],
                )
            ],
        )
        self.assertEqual(conversation_store.finalized_with["accepted_source"], "rule")

    def test_start_volc_session_creates_conversation_store_with_memory_context(self) -> None:
        gateway = RealtimeGateway(_FakeClientWebSocket())
        gateway.agent_profile_id = "phone-assistant"
        gateway.memory_context = {
            "agent_profile_id": "phone-assistant",
            "memories": [{"content": "我喜欢女声"}],
            "system_role_text": "长期记忆：\n- 我喜欢女声",
        }
        created: list[dict] = []

        class CapturingConversationStore(_FakeConversationStore):
            def __init__(
                self,
                base_dir: Path,
                session_id: str,
                agent_profile_id: str,
                config: dict,
                memory_context: dict,
            ) -> None:
                super().__init__()
                created.append(
                    {
                        "base_dir": base_dir,
                        "session_id": session_id,
                        "agent_profile_id": agent_profile_id,
                        "config": config,
                        "memory_context": memory_context,
                    }
                )

        with (
            patch("api.realtime.gateway.ConversationStore", CapturingConversationStore),
            patch("api.realtime.gateway.get_conversations_dir", return_value=Path("/tmp/conversations")),
            patch("api.realtime.gateway.websockets.connect", side_effect=RuntimeError("offline")),
        ):
            asyncio.run(
                gateway._start_volc_session(
                    {
                        "payload": {"dialog": {"system_role": "你是手机助手。"}},
                        "warnings": [],
                        "config": {"systemRole": "你是手机助手。"},
                    }
                )
            )

        self.assertEqual(created[0]["base_dir"], Path("/tmp/conversations"))
        self.assertEqual(created[0]["agent_profile_id"], "phone-assistant")
        self.assertEqual(created[0]["config"]["systemRole"], "你是手机助手。")
        self.assertEqual(created[0]["memory_context"]["memories"][0]["content"], "我喜欢女声")


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


class _FakeUpstream:
    def __init__(self) -> None:
        self.sent: list[bytes] = []

    async def send(self, payload: bytes) -> None:
        self.sent.append(payload)


class _FailingUpstream:
    async def send(self, payload: bytes) -> None:
        raise RuntimeError("upstream unavailable")


class _FailingSemanticRouter:
    def route_text(self, **kwargs) -> dict:
        raise RuntimeError("router unavailable")


class _FakeConversationStore:
    def __init__(self, transcripts: list[dict] | None = None) -> None:
        self.transcripts = transcripts or []
        self.route_decisions: list[dict] = []
        self.input_audio: list[bytes] = []
        self.output_audio: list[bytes] = []
        self.finalized_with: dict | None = None

    def write_input_audio(self, pcm: bytes) -> None:
        self.input_audio.append(pcm)

    def write_output_audio(self, pcm: bytes) -> None:
        self.output_audio.append(pcm)

    def record_transcript(self, event: dict) -> None:
        self.transcripts.append(event)

    def record_route_decision(self, decision: dict) -> None:
        self.route_decisions.append(decision)

    def read_transcript(self) -> list[dict]:
        return self.transcripts

    def finalize(self, memory_extraction: dict | None = None) -> None:
        self.finalized_with = memory_extraction or {}


class _FakeMemoryStore:
    def __init__(self, context: dict | None = None) -> None:
        self.context = context or {
            "agent_profile_id": "phone-assistant",
            "session_ids": [],
            "memories": [],
            "system_role_text": "",
        }
        self.context_requests: list[tuple[str, list[str]]] = []
        self.extraction_requests: list[tuple[str, str, list[dict]]] = []

    def build_memory_context(self, agent_profile_id: str, session_ids: list[str] | None = None) -> dict:
        session_ids = session_ids or []
        self.context_requests.append((agent_profile_id, session_ids))
        return {**self.context, "session_ids": session_ids}

    def extract_compare_and_persist(self, session_id: str, agent_profile_id: str, transcript: list[dict]) -> dict:
        self.extraction_requests.append((session_id, agent_profile_id, transcript))
        return {
            "session_id": session_id,
            "agent_profile_id": agent_profile_id,
            "accepted_source": "rule",
            "rule": {"status": "ok", "memories": [{"content": "我喜欢女声"}]},
            "model": {"status": "not_configured", "memories": []},
            "diff": [{"field": "memories", "rule": ["我喜欢女声"], "model": []}],
        }


if __name__ == "__main__":
    unittest.main()

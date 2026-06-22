import asyncio
import json
import unittest
from unittest.mock import AsyncMock, Mock, patch

from apps.api.realtime.gateway import (
    RealtimeGateway,
    _is_realtime_payload_log_enabled,
    _make_asr_payload_log,
    _make_event,
    _merge_asr_text,
    _merge_result_texts,
    _merge_stream_text,
)


class RealtimeGatewayTest(unittest.TestCase):
    def test_merge_result_texts_prefers_asr_revision_over_concatenation(self):
        text = _merge_result_texts(
            [
                "你哎就你哎叫你哎你擅长什么呀你擅长解 bug 吗",
                "你哎，叫你哎，你擅长什么呀？你擅长解 bug 吗？",
            ]
        )

        self.assertEqual(text, "你哎，叫你哎，你擅长什么呀？你擅长解 bug 吗？")

    def test_merge_asr_text_prefers_revision_over_concatenation(self):
        old = "哎你刚才说出门记得防晒这件事不是有点废话吗我问的你今天多少度"
        new = "哎，你刚才说出门记得防晒这件事不是有点废话吗？我问的你今天多少度？"

        text = _merge_asr_text(old, new)

        self.assertEqual(text, new)

    def test_merge_asr_text_keeps_full_text_on_partial_rollback(self):
        old = "哎，你刚才说出门记得防晒这件事不是有点废话吗？我问的你今天多少度？"
        new = "我问的你今天多少度"

        text = _merge_asr_text(old, new)

        self.assertEqual(text, old)

    def test_gateway_asr_revisions_update_current_user_text(self):
        client_ws = Mock()
        gateway = RealtimeGateway(client_ws)

        asyncio.run(gateway._emit_asr_text("哎你刚才说出门记得防晒这件事不是有点废话吗我问的你今天多少度"))
        asyncio.run(gateway._emit_asr_text("哎，你刚才说出门记得防晒这件事不是有点废话吗？我问的你今天多少度？"))

        event_payloads = [json.loads(call.args[0])["event"] for call in client_ws.send_text.call_args_list]

        self.assertEqual(event_payloads[-1]["text"], "ASRResponse: 哎，你刚才说出门记得防晒这件事不是有点废话吗？我问的你今天多少度？")
        self.assertNotIn("多少度哎，你刚才", event_payloads[-1]["text"])

    def test_merge_result_texts_collapses_visual_asr_repetition(self):
        cases = [
            (["VD 式模型", "VD式模型"], "VD 式模型"),
            (["VD式模型", "VD 式模型"], "VD式模型"),
            (["VD 式模型\u200bVD 式模型"], "VD 式模型"),
            (["VD 式模型\xa0VD 式模型"], "VD 式模型"),
            (["八零后", "80 后"], "80 后"),
            (["八零", "80"], "80"),
            (["我说八零", "我说 80"], "我说 80"),
        ]

        for parts, expected in cases:
            with self.subTest(parts=parts):
                self.assertEqual(_merge_result_texts(parts), expected)

    def test_assistant_output_id_reuses_repeated_text(self):
        gateway = RealtimeGateway(Mock())

        first = gateway._assistant_output_id_for_text("你好，我在。")
        repeated = gateway._assistant_output_id_for_text("你好，我在。")
        next_output = gateway._assistant_output_id_for_text("我们继续聊。")

        self.assertEqual(first, repeated)
        self.assertNotEqual(first, next_output)

    def test_make_event_can_include_output_id(self):
        event = _make_event("assistant", "ChatResponse: 你好", "assistant-output-1")

        self.assertEqual(event["outputId"], "assistant-output-1")

    def test_payload_log_env_flag(self):
        with patch.dict("os.environ", {}, clear=True):
            self.assertFalse(_is_realtime_payload_log_enabled())
        with patch.dict("os.environ", {"AI_ENGINE_REALTIME_PAYLOAD_LOG": "1"}):
            self.assertTrue(_is_realtime_payload_log_enabled())

    def test_make_asr_payload_log_contains_replayable_texts(self):
        log_payload = _make_asr_payload_log(
            {"results": [{"text": "VD 式模型"}, {"text": "VD式模型"}]},
            ["VD 式模型", "VD式模型"],
            "VD 式模型",
        )

        self.assertEqual(log_payload["rawTexts"][0]["text"], "VD 式模型")
        self.assertEqual(log_payload["rawTexts"][0]["normalized"], "VD式模型")
        self.assertIn("U+0020", log_payload["rawTexts"][0]["codepoints"])
        self.assertEqual(log_payload["mergedText"]["text"], "VD 式模型")

    def test_chat_response_emits_display_fallback_event(self):
        client_ws = Mock()
        gateway = RealtimeGateway(client_ws)

        asyncio.run(gateway._handle_chat_response_content("文字回复"))

        event_payload = json.loads(client_ws.send_text.call_args.args[0])
        self.assertEqual(event_payload["event"]["text"], "ChatResponse: 文字回复")
        self.assertEqual(event_payload["event"]["outputId"], "assistant-output-1")

    def test_chat_response_chunks_share_output_id_and_accumulate_text(self):
        client_ws = Mock()
        gateway = RealtimeGateway(client_ws)

        for content in ("暂时不", "匹配", "，谢谢您", "的理解", "，", "那", "我们就先到"):
            asyncio.run(gateway._handle_chat_response_content(content))

        event_payloads = [json.loads(call.args[0])["event"] for call in client_ws.send_text.call_args_list]
        output_ids = {event["outputId"] for event in event_payloads}

        self.assertEqual(output_ids, {"assistant-output-1"})
        self.assertEqual(event_payloads[-1]["text"], "ChatResponse: 暂时不匹配，谢谢您的理解，那我们就先到")

    def test_stream_merge_skips_delta_already_contained_in_previous(self):
        self.assertEqual(_merge_stream_text("你的问题", "的"), "你的问题")
        self.assertEqual(_merge_stream_text("好的，我们继续", "好的"), "好的，我们继续")
        self.assertEqual(_merge_stream_text("暂时不", "匹配"), "暂时不匹配")

    def test_user_text_starts_next_assistant_output_id(self):
        client_ws = Mock()
        gateway = RealtimeGateway(client_ws)

        asyncio.run(gateway._handle_assistant_text("好的，我们继续"))
        gateway._prepare_for_user_input()
        asyncio.run(gateway._handle_chat_response_content("好的"))

        event_payloads = [json.loads(call.args[0])["event"] for call in client_ws.send_text.call_args_list]

        self.assertEqual(event_payloads[0]["outputId"], "assistant-output-1")
        self.assertEqual(event_payloads[1]["outputId"], "assistant-output-2")

    def test_repeated_assistant_tail_after_user_input_keeps_previous_output_id(self):
        client_ws = Mock()
        gateway = RealtimeGateway(client_ws)

        asyncio.run(gateway._handle_chat_response_content("不好意思，我们这次访谈的样本城市主要是济南、成都、郑州、杭州、深圳、长沙及周边，北京暂时不在样本范围内，这次可能没法继续访问了。感谢您的理解啊。"))
        gateway._prepare_for_user_input()
        asyncio.run(gateway._handle_tts_sentence_end_text("不好意思，我们这次访谈的样本城市主要是济南、成都、郑州、杭州、深圳、长沙及周边，北京暂时不在样本范围内，这次可能没法继续访问了。谢谢您的理解呀。"))

        event_payloads = [json.loads(call.args[0])["event"] for call in client_ws.send_text.call_args_list]
        output_ids = {event["outputId"] for event in event_payloads}

        self.assertEqual(output_ids, {"assistant-output-1"})

    def test_tts_sentence_end_reuses_chat_response_output_id(self):
        client_ws = Mock()
        gateway = RealtimeGateway(client_ws)

        asyncio.run(gateway._handle_chat_response_content("暂时不"))
        asyncio.run(gateway._handle_chat_response_content("匹配"))
        asyncio.run(gateway._handle_tts_sentence_end_text("暂时不匹配，谢谢您的理解"))

        event_payloads = [json.loads(call.args[0])["event"] for call in client_ws.send_text.call_args_list]
        output_ids = {event["outputId"] for event in event_payloads}

        self.assertEqual(output_ids, {"assistant-output-1"})
        self.assertEqual(event_payloads[-1]["text"], "ChatResponse: 暂时不匹配，谢谢您的理解")

    def test_tts_sentence_text_corrects_visible_chat_response_text(self):
        client_ws = Mock()
        gateway = RealtimeGateway(client_ws)

        asyncio.run(gateway._handle_chat_response_content("好的，那就是杭州。您最近半年有参加过其他汽车相关的市场调查吗？"))
        asyncio.run(gateway._handle_tts_sentence_start_text("好的，那就是。您最近半年有参加过其他汽车相关的市场调查吗？"))

        event_payloads = [json.loads(call.args[0])["event"] for call in client_ws.send_text.call_args_list]

        self.assertEqual(event_payloads[0]["outputId"], "assistant-output-1")
        self.assertEqual(event_payloads[1]["outputId"], "assistant-output-1")
        self.assertEqual(event_payloads[1]["text"], "ChatResponse: 好的，那就是。您最近半年有参加过其他汽车相关的市场调查吗？")

    def test_tts_sentence_minor_insert_correction_reuses_chat_response_output_id(self):
        client_ws = Mock()
        gateway = RealtimeGateway(client_ws)

        asyncio.run(gateway._handle_chat_response_content("抱歉，这次我们的访谈样本主要针对济南、成都、郑州、杭州、深圳、长沙及周边的用户，北京的样本暂时不需要可能没法继续访谈了，谢谢您的理解。"))
        asyncio.run(gateway._handle_tts_sentence_end_text("抱歉，这次我们的访谈样本主要针对济南、成都、郑州、杭州、深圳、长沙及周边的用户，北京的样本暂时不需要，这次可能没法继续访谈了，谢谢您的理解。"))

        event_payloads = [json.loads(call.args[0])["event"] for call in client_ws.send_text.call_args_list]
        output_ids = {event["outputId"] for event in event_payloads}

        self.assertEqual(output_ids, {"assistant-output-1"})
        self.assertEqual(event_payloads[-1]["text"], "ChatResponse: 抱歉，这次我们的访谈样本主要针对济南、成都、郑州、杭州、深圳、长沙及周边的用户，北京的样本暂时不需要，这次可能没法继续访谈了，谢谢您的理解。")

    def test_tts_sentence_start_end_minor_insert_reuses_output_id(self):
        client_ws = Mock()
        gateway = RealtimeGateway(client_ws)

        asyncio.run(gateway._handle_tts_sentence_start_text("抱歉，这次我们的访谈样本主要针对济南、成都、郑州、杭州、深圳、长沙及周边的用户，北京的样本暂时不需要可能没法继续访谈了，谢谢您的理解。"))
        asyncio.run(gateway._handle_tts_sentence_end_text("抱歉，这次我们的访谈样本主要针对济南、成都、郑州、杭州、深圳、长沙及周边的用户，北京的样本暂时不需要，这次可能没法继续访谈了，谢谢您的理解。"))

        event_payloads = [json.loads(call.args[0])["event"] for call in client_ws.send_text.call_args_list]
        output_ids = {event["outputId"] for event in event_payloads}

        self.assertEqual(output_ids, {"assistant-output-1"})
        self.assertEqual(event_payloads[-1]["text"], "ChatResponse: 抱歉，这次我们的访谈样本主要针对济南、成都、郑州、杭州、深圳、长沙及周边的用户，北京的样本暂时不需要，这次可能没法继续访谈了，谢谢您的理解。")

    def test_tts_sentence_short_insert_correction_reuses_output_id(self):
        client_ws = Mock()
        gateway = RealtimeGateway(client_ws)

        asyncio.run(gateway._handle_tts_sentence_start_text("那当然，我说话可是很清晰的，你可要好听哦。"))
        asyncio.run(gateway._handle_tts_sentence_end_text("那当然，我说话可是很清晰的，你可要好好听哦。"))

        event_payloads = [json.loads(call.args[0])["event"] for call in client_ws.send_text.call_args_list]
        output_ids = {event["outputId"] for event in event_payloads}

        self.assertEqual(output_ids, {"assistant-output-1"})
        self.assertEqual(event_payloads[-1]["text"], "ChatResponse: 那当然，我说话可是很清晰的，你可要好好听哦。")

    def test_short_different_assistant_text_starts_new_output_id(self):
        client_ws = Mock()
        gateway = RealtimeGateway(client_ws)

        asyncio.run(gateway._handle_tts_sentence_start_text("好的，那我们继续。"))
        asyncio.run(gateway._handle_tts_sentence_start_text("好的，那我们结束。"))

        event_payloads = [json.loads(call.args[0])["event"] for call in client_ws.send_text.call_args_list]
        output_ids = [event["outputId"] for event in event_payloads]

        self.assertEqual(output_ids, ["assistant-output-1", "assistant-output-2"])

    def test_tts_text_and_audio_share_output_id(self):
        client_ws = Mock()
        gateway = RealtimeGateway(client_ws)

        asyncio.run(gateway._handle_tts_sentence_start_text("实际播报"))
        asyncio.run(gateway._handle_tts_audio(b"\x00\x00"))

        event_payload = json.loads(client_ws.send_text.call_args_list[0].args[0])
        audio_payload = json.loads(client_ws.send_text.call_args_list[1].args[0])

        self.assertEqual(event_payload["event"]["text"], "ChatResponse: 实际播报")
        self.assertEqual(event_payload["event"]["outputId"], "assistant-output-1")
        self.assertEqual(audio_payload["outputId"], "assistant-output-1")

    def test_gateway_records_client_and_assistant_audio_when_recorder_is_active(self):
        class Recorder:
            def __init__(self):
                self.client_audio = b""
                self.assistant_audio = b""

            def write_client_audio(self, audio: bytes) -> None:
                self.client_audio += audio

            def write_assistant_audio(self, audio: bytes) -> None:
                self.assistant_audio += audio

        client_ws = Mock()
        recorder = Recorder()
        upstream = AsyncMock()
        gateway = RealtimeGateway(client_ws)
        gateway.voice_recording = recorder
        gateway.upstream = upstream
        gateway.session_id = "session-1"

        asyncio.run(gateway._handle_binary(b"\x01\x02"))
        asyncio.run(gateway._handle_tts_audio(b"\x03\x04"))

        self.assertEqual(recorder.client_audio, b"\x01\x02")
        self.assertEqual(recorder.assistant_audio, b"\x03\x04")

    def test_start_volc_session_passes_request_id_and_record_audio_flag_to_recorder(self):
        client_ws = Mock()
        client_ws.send_text = AsyncMock()
        gateway = RealtimeGateway(client_ws)

        with (
            patch("apps.api.realtime.gateway.start_voice_recording") as start_recording,
            patch("apps.api.realtime.gateway.websockets.connect", new_callable=AsyncMock) as connect,
        ):
            connect.side_effect = RuntimeError("stop before upstream")
            asyncio.run(
                gateway._start_volc_session(
                    {"payload": {}, "warnings": [], "config": {"openingLine": ""}},
                    {
                        "requestId": "request_1",
                        "userId": "scene_route",
                        "sceneId": "hs6_user_interview",
                        "recordAudio": True,
                    },
                )
            )

        start_recording.assert_called_once()
        self.assertEqual(start_recording.call_args.args[1]["requestId"], "request_1")
        self.assertTrue(start_recording.call_args.kwargs["enabled"])

    def test_start_volc_session_does_not_record_when_record_audio_is_false(self):
        client_ws = Mock()
        client_ws.send_text = AsyncMock()
        gateway = RealtimeGateway(client_ws)

        with (
            patch("apps.api.realtime.gateway.start_voice_recording") as start_recording,
            patch("apps.api.realtime.gateway.websockets.connect", new_callable=AsyncMock) as connect,
        ):
            connect.side_effect = RuntimeError("stop before upstream")
            asyncio.run(
                gateway._start_volc_session(
                    {"payload": {}, "warnings": [], "config": {"openingLine": ""}},
                    {"sceneId": "hs6_user_interview", "recordAudio": False},
                )
            )

        start_recording.assert_called_once()
        self.assertFalse(start_recording.call_args.kwargs["enabled"])

    def test_start_volc_session_retries_transient_upstream_403(self):
        client_ws = Mock()
        client_ws.send_text = AsyncMock()
        upstream = AsyncMock()
        gateway = RealtimeGateway(client_ws)

        async def noop_upstream_loop(*_args):
            return None

        with (
            patch("apps.api.realtime.gateway.start_voice_recording"),
            patch("apps.api.realtime.gateway.websockets.connect", new_callable=AsyncMock) as connect,
            patch("apps.api.realtime.gateway.asyncio.sleep", new_callable=AsyncMock),
        ):
            connect.side_effect = [
                RuntimeError("server rejected WebSocket connection: HTTP 403"),
                upstream,
            ]
            gateway._upstream_loop = noop_upstream_loop
            asyncio.run(
                gateway._start_volc_session(
                    {"payload": {}, "warnings": [], "config": {"openingLine": ""}},
                    {"sceneId": "hs6_user_interview", "recordAudio": False},
                )
            )
            asyncio.run(gateway._cancel_tasks())

        self.assertEqual(connect.await_count, 2)
        self.assertGreaterEqual(upstream.send.await_count, 1)
        sent_payloads = [json.loads(call.args[0]) for call in client_ws.send_text.call_args_list]
        self.assertNotIn("error", [payload["type"] for payload in sent_payloads])

    def test_interrupt_ack_returns_target_output_id_and_next_response_is_new_turn(self):
        client_ws = Mock()
        upstream = AsyncMock()
        gateway = RealtimeGateway(client_ws)
        gateway.upstream = upstream
        gateway.session_id = "session-1"

        asyncio.run(gateway._handle_assistant_text("旧播报"))
        asyncio.run(gateway._handle_text(json.dumps({"type": "interrupt", "targetOutputId": "assistant-output-1"})))
        asyncio.run(gateway._handle_chat_response_content("新回复"))

        sent_payloads = [json.loads(call.args[0]) for call in client_ws.send_text.call_args_list]

        self.assertEqual(sent_payloads[1]["type"], "interrupt_ack")
        self.assertEqual(sent_payloads[1]["targetOutputId"], "assistant-output-1")
        self.assertEqual(sent_payloads[2]["event"]["text"], "ChatResponse: 新回复")
        self.assertEqual(sent_payloads[2]["event"]["outputId"], "assistant-output-2")
        upstream.send.assert_awaited()

    def test_tts_sentence_end_can_emit_missing_text_event(self):
        client_ws = Mock()
        gateway = RealtimeGateway(client_ws)

        asyncio.run(gateway._handle_tts_sentence_end_text("后续播报"))

        event_payload = json.loads(client_ws.send_text.call_args.args[0])
        self.assertEqual(event_payload["event"]["text"], "ChatResponse: 后续播报")
        self.assertEqual(event_payload["event"]["outputId"], "assistant-output-1")

    def test_tts_sentence_end_does_not_duplicate_existing_text_event(self):
        client_ws = Mock()
        gateway = RealtimeGateway(client_ws)

        asyncio.run(gateway._handle_assistant_text("开场白"))
        client_ws.send_text.reset_mock()
        asyncio.run(gateway._handle_tts_sentence_end_text("开场白"))

        client_ws.send_text.assert_not_called()

    def test_close_client_ws_ignores_already_closed_socket(self):
        client_ws = Mock()
        client_ws.close = AsyncMock(side_effect=RuntimeError("Unexpected ASGI message 'websocket.close'"))
        gateway = RealtimeGateway(client_ws)

        asyncio.run(gateway._close_client_ws())

        client_ws.close.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()

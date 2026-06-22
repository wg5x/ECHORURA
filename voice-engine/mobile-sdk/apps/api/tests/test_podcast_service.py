import unittest
from unittest.mock import patch

from apps.api.integrations.volc.events import SERVER_EVENTS
from apps.api.integrations.volc.frames import ServerFrame, make_audio_frame, make_json_frame, parse_server_frame
from apps.api.runtime.podcast_service import MAX_ROUND_CHARS, build_podcast_audio_payload, build_podcast_audio_request, build_podcast_draft
from apps.api.runtime.podcast_synthesis_service import (
    PodcastSynthesisState,
    build_podcast_audio_result,
    consume_podcast_frame,
)


class PodcastServiceTest(unittest.TestCase):
    def test_builds_reviewable_duo_draft(self):
        draft = build_podcast_draft(
            {
                "topic": "用户长期记忆",
                "sourceText": "长期记忆需要可删除。用户画像必须有来源。第一版先生成脚本草稿。",
            }
        )

        self.assertEqual(draft["format"], "duo_brief")
        self.assertGreaterEqual(len(draft["rounds"]), 4)
        self.assertTrue(draft["synthesis"]["readyForReview"])
        self.assertTrue(all(len(round_item["text"]) <= MAX_ROUND_CHARS for round_item in draft["rounds"]))

    def test_long_source_expands_rounds_by_duration(self):
        source_text = "。".join(f"第{index}段材料包含一个需要展开的观点和证据" for index in range(1, 31))

        draft = build_podcast_draft(
            {
                "topic": "长报告解读",
                "sourceText": source_text,
                "durationMinutes": 6,
            }
        )
        total_chars = sum(len(round_item["text"]) for round_item in draft["rounds"])

        self.assertGreaterEqual(len(draft["rounds"]), 20)
        self.assertGreater(total_chars, 1000)
        self.assertTrue(all(len(round_item["text"]) <= MAX_ROUND_CHARS for round_item in draft["rounds"]))

    def test_long_unpunctuated_source_is_split_into_multiple_rounds(self):
        source_text = "这是一段没有句读但需要被拆分成长播客材料的内容" * 160

        draft = build_podcast_draft(
            {
                "topic": "无标点长材料",
                "sourceText": source_text,
                "durationMinutes": 6,
            }
        )
        total_chars = sum(len(round_item["text"]) for round_item in draft["rounds"])

        self.assertGreaterEqual(len(draft["rounds"]), 20)
        self.assertGreater(total_chars, 1000)
        self.assertTrue(all(len(round_item["text"]) <= MAX_ROUND_CHARS for round_item in draft["rounds"]))

    def test_missing_source_returns_warning(self):
        draft = build_podcast_draft({"topic": "播客"})

        self.assertIn("缺少来源材料，草稿只会围绕话题做结构化展开。", draft["warnings"])

    def test_builds_action_3_audio_payload(self):
        audio = build_podcast_audio_request(
            {
                "hostA": "mizi",
                "hostB": "dayi",
                "rounds": [
                    {"idx": 1, "speaker": "host_a", "text": "欢迎收听。"},
                    {"idx": 2, "speaker": "host_b", "text": "我们开始解读。"},
                ],
            },
            configured=False,
        )

        self.assertEqual(audio["status"], "needs_config")
        self.assertEqual(audio["payload"]["action"], 3)
        self.assertEqual(
            audio["payload"]["speaker_info"]["speakers"],
            ["zh_female_mizaitongxue_v2_saturn_bigtts", "zh_male_dayixiansheng_v2_saturn_bigtts"],
        )
        self.assertEqual(audio["payload"]["nlp_texts"][0]["speaker"], "zh_female_mizaitongxue_v2_saturn_bigtts")
        self.assertIsNone(audio["audioUrl"])

    def test_maps_business_hosts_to_configured_volc_speakers(self):
        with patch.dict(
            "os.environ",
            {
                "VOLC_PODCAST_SPEAKER_MIZI": "volc_mizi",
                "VOLC_PODCAST_SPEAKER_DAYI": "volc_dayi",
            },
            clear=True,
        ):
            payload = build_podcast_audio_payload(
                {
                    "hostA": "mizi",
                    "hostB": "dayi",
                    "rounds": [
                        {"idx": 1, "speaker": "host_a", "text": "欢迎收听。"},
                        {"idx": 2, "speaker": "host_b", "text": "我们开始解读。"},
                    ],
                }
            )

        self.assertEqual(payload["speaker_info"]["speakers"], ["volc_mizi", "volc_dayi"])
        self.assertEqual(payload["nlp_texts"][0]["speaker"], "volc_mizi")
        self.assertEqual(payload["nlp_texts"][1]["speaker"], "volc_dayi")

    def test_builds_ready_audio_preview_when_configured(self):
        audio = build_podcast_audio_request(
            {
                "hostA": "mizi",
                "hostB": "dayi",
                "rounds": [{"idx": 1, "speaker": "host_a", "text": "欢迎收听。"}],
            },
            configured=True,
        )

        self.assertEqual(audio["status"], "ready")
        self.assertEqual(audio["payload"]["audio_config"]["format"], "mp3")
        self.assertEqual(audio["payload"]["audio_config"]["sample_rate"], 24000)

    def test_consumes_podcast_events_into_playable_result(self):
        state = PodcastSynthesisState()

        self._consume_frame(state, make_json_frame(SERVER_EVENTS["SESSION_STARTED"], {}))
        self._consume_frame(
            state,
            make_json_frame(
                SERVER_EVENTS["PODCAST_ROUND_START"],
                {"idx": 1, "speaker": "mizi", "text": "欢迎收听。"},
            ),
        )
        self._consume_frame(state, make_audio_frame(SERVER_EVENTS["PODCAST_ROUND_RESPONSE"], b"mp3-bytes"))
        self._consume_frame(
            state,
            make_json_frame(
                SERVER_EVENTS["PODCAST_ROUND_END"],
                {"idx": 1, "audio_duration": 1200, "start_time": 0, "end_time": 1200},
            ),
        )
        self._consume_frame(
            state,
            make_json_frame(
                SERVER_EVENTS["PODCAST_END"],
                {
                    "meta_info": {"audio_url": "https://example.test/podcast.mp3"},
                    "input_metrics": {"input_chars": 12},
                },
            ),
        )
        self._consume_frame(state, make_json_frame(SERVER_EVENTS["USAGE_RESPONSE"], {"usage": {"tokens": 8}}))

        result = build_podcast_audio_result({"action": 3}, state)

        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["audioUrl"], "https://example.test/podcast.mp3")
        self.assertEqual(result["chapters"][0]["audioDuration"], 1200)
        self.assertEqual(result["usage"], {"tokens": 8})
        self.assertEqual(result["inputMetrics"], {"input_chars": 12})

    def test_uses_stream_audio_data_url_when_audio_url_missing(self):
        state = PodcastSynthesisState()

        self._consume_frame(state, make_audio_frame(SERVER_EVENTS["PODCAST_ROUND_RESPONSE"], b"abc"))
        self._consume_frame(state, make_json_frame(SERVER_EVENTS["PODCAST_END"], {"meta_info": {}}))

        result = build_podcast_audio_result({"action": 3}, state)

        self.assertEqual(result["audioUrl"], "data:audio/mpeg;base64,YWJj")
        self.assertIn("data URL", result["warnings"][0])

    def test_podcast_error_frame_is_replayable(self):
        state = PodcastSynthesisState()

        with self.assertRaisesRegex(ValueError, "speaker invalid"):
            consume_podcast_frame(
                state,
                ServerFrame(
                    code=400,
                    event=SERVER_EVENTS["SESSION_FAILED"],
                    message_type=1,
                    session_id="",
                    payload={"error": "speaker invalid"},
                ),
            )

    def test_resource_speaker_mismatch_error_is_actionable(self):
        state = PodcastSynthesisState()

        with self.assertRaisesRegex(ValueError, "VOLC_PODCAST_SPEAKER_MAP"):
            consume_podcast_frame(
                state,
                ServerFrame(
                    code=400,
                    event=None,
                    message_type=0x0F,
                    session_id="",
                    payload="resource ID is mismatched with speaker related resource",
                ),
            )

    def _consume_frame(self, state: PodcastSynthesisState, data: bytes) -> None:
        frame = parse_server_frame(data)
        self.assertIsNotNone(frame)
        consume_podcast_frame(state, frame)


if __name__ == "__main__":
    unittest.main()

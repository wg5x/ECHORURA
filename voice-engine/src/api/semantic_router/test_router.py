import asyncio
import json
import unittest

from api.main import decide_route
from api.semantic_router.router import SemanticRouter


class SemanticRouterTest(unittest.TestCase):
    def setUp(self) -> None:
        self.router = SemanticRouter()

    def test_routes_create_song_as_scenario(self) -> None:
        decision = self.router.route_text("session-1", "turn-1", "帮我做一首下班路上听的中文 LoFi")

        self.assertEqual(decision["type"], "route_decision")
        self.assertEqual(decision["mode"], "scenario")
        self.assertEqual(decision["scenario_id"], "music_creation")
        self.assertEqual(decision["scenario_intent"], "create_song")
        self.assertEqual(decision["intent"], "create_song")
        self.assertEqual(decision["arguments"]["language"], "zh")
        self.assertEqual(decision["arguments"]["genre"], "lofi")

    def test_routes_revise_song_as_scenario(self) -> None:
        decision = self.router.route_text("session-1", "turn-2", "副歌慢一点")

        self.assertEqual(decision["mode"], "scenario")
        self.assertEqual(decision["scenario_id"], "music_creation")
        self.assertEqual(decision["scenario_intent"], "revise_song")

    def test_publish_requires_confirmation(self) -> None:
        decision = self.router.route_text("session-1", "turn-3", "保存并发布")

        self.assertEqual(decision["mode"], "scenario")
        self.assertEqual(decision["scenario_intent"], "publish_work")
        self.assertTrue(decision["requires_confirmation"])

    def test_routes_open_page_as_native_action(self) -> None:
        decision = self.router.route_text("session-1", "turn-4", "打开作品页")

        self.assertEqual(decision["mode"], "native_action")
        self.assertEqual(decision["intent"], "open_page")
        self.assertEqual(decision["arguments"], {"target": "work_detail"})

    def test_routes_general_text_as_chat(self) -> None:
        decision = self.router.route_text("session-1", "turn-5", "今天天气怎么样")

        self.assertEqual(decision["mode"], "chat")
        self.assertEqual(decision["intent"], "general")
        self.assertNotIn("scenario_id", decision)

    def test_phone_assistant_uses_only_enabled_capabilities(self) -> None:
        decision = self.router.route_text(
            "session-1",
            "turn-6",
            "帮我做一首下班路上听的中文 LoFi",
            agent_profile_id="phone-assistant",
        )

        self.assertEqual(decision["agent_profile_id"], "phone-assistant")
        self.assertEqual(decision["mode"], "chat")
        self.assertEqual(decision["intent"], "general")
        self.assertNotIn("scenario_id", decision)

    def test_phone_assistant_routes_calendar_event(self) -> None:
        decision = self.router.route_text(
            "session-1",
            "turn-phone-1",
            "今天下午三点开会",
            agent_profile_id="phone-assistant",
        )

        self.assertEqual(decision["mode"], "native_action")
        self.assertEqual(decision["intent"], "calendar.create_event")
        self.assertTrue(decision["requires_confirmation"])
        self.assertEqual(decision["arguments"]["title"], "开会")
        self.assertEqual(decision["arguments"]["time_text"], "今天下午三点")
        self.assertEqual(decision["arguments"]["android_action"], "android.intent.action.INSERT")

    def test_phone_assistant_routes_phone_dial(self) -> None:
        decision = self.router.route_text(
            "session-1",
            "turn-phone-2",
            "打电话 13641194007",
            agent_profile_id="phone-assistant",
        )

        self.assertEqual(decision["mode"], "native_action")
        self.assertEqual(decision["intent"], "phone.dial")
        self.assertEqual(decision["arguments"]["phone_number"], "13641194007")

    def test_phone_assistant_routes_sms_compose(self) -> None:
        decision = self.router.route_text(
            "session-1",
            "turn-phone-3",
            "发短信告诉他我晚点到",
            agent_profile_id="phone-assistant",
        )

        self.assertEqual(decision["mode"], "native_action")
        self.assertEqual(decision["intent"], "sms.compose")
        self.assertEqual(decision["arguments"]["message_text"], "告诉他我晚点到")

    def test_phone_assistant_routes_app_open(self) -> None:
        decision = self.router.route_text(
            "session-1",
            "turn-phone-4",
            "打开淘宝",
            agent_profile_id="phone-assistant",
        )

        self.assertEqual(decision["mode"], "native_action")
        self.assertEqual(decision["intent"], "app.open")
        self.assertEqual(decision["arguments"]["app_name"], "淘宝")

    def test_phone_assistant_routes_browser_url(self) -> None:
        decision = self.router.route_text(
            "session-1",
            "turn-phone-5",
            "打开 https://example.com",
            agent_profile_id="phone-assistant",
        )

        self.assertEqual(decision["mode"], "native_action")
        self.assertEqual(decision["intent"], "browser.open_url")
        self.assertEqual(decision["arguments"]["url"], "https://example.com")

    def test_phone_assistant_routes_gallery_pick_image(self) -> None:
        decision = self.router.route_text(
            "session-1",
            "turn-phone-6",
            "打开相册选一张图片",
            agent_profile_id="phone-assistant",
        )

        self.assertEqual(decision["mode"], "native_action")
        self.assertEqual(decision["intent"], "gallery.pick_image")
        self.assertEqual(decision["arguments"]["media_type"], "image")

    def test_phone_assistant_routes_media_video_search(self) -> None:
        decision = self.router.route_text(
            "session-1",
            "turn-phone-7",
            "看视频",
            agent_profile_id="phone-assistant",
        )

        self.assertEqual(decision["mode"], "native_action")
        self.assertEqual(decision["intent"], "media.play_from_search")
        self.assertEqual(decision["arguments"]["media_type"], "video")

    def test_phone_assistant_routes_wifi_settings(self) -> None:
        decision = self.router.route_text(
            "session-1",
            "turn-phone-8",
            "打开 Wi-Fi 设置",
            agent_profile_id="phone-assistant",
        )

        self.assertEqual(decision["mode"], "native_action")
        self.assertEqual(decision["intent"], "settings.open_wifi")
        self.assertEqual(decision["arguments"]["panel"], "wifi")

    def test_decision_can_be_serialized_for_cli_output(self) -> None:
        decision = self.router.route_text("session-1", "turn-7", "打开作品页")

        output = json.dumps(decision, ensure_ascii=False)

        self.assertIn('"type": "route_decision"', output)
        self.assertIn('"mode": "native_action"', output)


class SemanticRouterHttpTest(unittest.TestCase):
    def test_decide_route_endpoint_returns_decision(self) -> None:
        decision = asyncio.run(decide_route({"text": "保存并发布", "session_id": "debug-session"}))

        self.assertEqual(decision["session_id"], "debug-session")
        self.assertEqual(decision["mode"], "scenario")
        self.assertEqual(decision["scenario_intent"], "publish_work")
        self.assertTrue(decision["requires_confirmation"])

    def test_decide_route_endpoint_accepts_agent_profile_id(self) -> None:
        decision = asyncio.run(
            decide_route(
                {
                    "text": "帮我做一首下班路上听的中文 LoFi",
                    "session_id": "debug-session",
                    "agent_profile_id": "phone-assistant",
                }
            )
        )

        self.assertEqual(decision["agent_profile_id"], "phone-assistant")
        self.assertEqual(decision["mode"], "chat")
        self.assertEqual(decision["intent"], "general")


if __name__ == "__main__":
    unittest.main()

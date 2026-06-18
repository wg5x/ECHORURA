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

    def test_decision_can_be_serialized_for_cli_output(self) -> None:
        decision = self.router.route_text("session-1", "turn-6", "打开作品页")

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


if __name__ == "__main__":
    unittest.main()

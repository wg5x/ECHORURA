import unittest

from .policy_guard import enforce_route_policy


class RoutePolicyGuardTest(unittest.TestCase):
    def test_downgrades_capability_not_enabled_for_agent_profile(self) -> None:
        decision = enforce_route_policy(
            {
                "type": "route_decision",
                "session_id": "session-1",
                "turn_id": "turn-1",
                "agent_profile_id": "default",
                "mode": "native_action",
                "intent": "app.open",
                "confidence": 0.9,
                "arguments": {},
            },
            text="打开淘宝",
            agent_profile_id="default",
        )

        self.assertEqual(decision["mode"], "chat")
        self.assertEqual(decision["intent"], "general")

    def test_corrects_open_app_when_model_returns_app_search(self) -> None:
        decision = enforce_route_policy(
            {
                "type": "route_decision",
                "session_id": "session-1",
                "turn_id": "turn-1",
                "agent_profile_id": "phone-assistant",
                "mode": "native_action",
                "intent": "app.search",
                "confidence": 0.9,
                "arguments": {},
            },
            text="打开淘宝",
            agent_profile_id="phone-assistant",
        )

        self.assertEqual(decision["mode"], "native_action")
        self.assertEqual(decision["intent"], "app.open")

    def test_keeps_app_search_when_text_contains_search_query(self) -> None:
        decision = enforce_route_policy(
            {
                "type": "route_decision",
                "session_id": "session-1",
                "turn_id": "turn-1",
                "agent_profile_id": "phone-assistant",
                "mode": "native_action",
                "intent": "app.search",
                "confidence": 0.9,
                "arguments": {},
            },
            text="淘宝搜索耳机",
            agent_profile_id="phone-assistant",
        )

        self.assertEqual(decision["mode"], "native_action")
        self.assertEqual(decision["intent"], "app.search")

    def test_downgrades_music_scenario_for_phone_assistant(self) -> None:
        decision = enforce_route_policy(
            {
                "type": "route_decision",
                "session_id": "session-1",
                "turn_id": "turn-1",
                "agent_profile_id": "phone-assistant",
                "mode": "scenario",
                "intent": "create_song",
                "scenario_id": "music_creation",
                "scenario_intent": "create_song",
                "confidence": 0.9,
                "arguments": {},
            },
            text="帮我做一首歌",
            agent_profile_id="phone-assistant",
        )

        self.assertEqual(decision["mode"], "chat")
        self.assertEqual(decision["intent"], "general")

    def test_keeps_music_scenario_for_default_profile(self) -> None:
        decision = enforce_route_policy(
            {
                "type": "route_decision",
                "session_id": "session-1",
                "turn_id": "turn-1",
                "agent_profile_id": "default",
                "mode": "scenario",
                "intent": "create_song",
                "confidence": 0.9,
                "arguments": {},
            },
            text="帮我做一首歌",
            agent_profile_id="default",
        )

        self.assertEqual(decision["mode"], "scenario")
        self.assertEqual(decision["intent"], "create_song")


if __name__ == "__main__":
    unittest.main()

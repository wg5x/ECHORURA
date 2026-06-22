import unittest
from unittest.mock import patch

from apps.api.memory.card_service import compress_memory_card, normalize_memory_card
from apps.api.runtime.user_profile_service import build_user_profile


class MemoryProfileServiceTest(unittest.TestCase):
    def test_normalize_old_card_adds_facts(self):
        card = normalize_memory_card({"preferences": ["回答短一点"]}, "user_1", "scene_1")

        self.assertEqual(card["facts"], [])
        self.assertEqual(card["preferences"], ["回答短一点"])

    def test_compress_extracts_stable_facts_and_skips_sensitive_text(self):
        result = compress_memory_card(
            user_id="user_1",
            scene_id="scene_1",
            max_chars=1200,
            previous_card={},
            report={
                "transcript": [
                    {"role": "user", "text": "我是产品经理，主要做语音产品。"},
                    {"role": "user", "text": "我的手机号是 13800000000。"},
                    {"role": "user", "text": "我喜欢短一点的回答。"},
                ]
            },
        )

        card = result["card"]
        self.assertIn("我是产品经理，主要做语音产品。", card["facts"])
        self.assertIn("我喜欢短一点的回答。", card["preferences"])
        self.assertTrue(all("13800000000" not in item for item in [*card["facts"], *card["preferences"], *card["openThreads"]]))

    def test_user_profile_aggregates_memory_cards(self):
        cards = [
            {
                "sceneId": "scene_1",
                "updatedAt": "2026-06-12T01:00:00Z",
                "facts": ["我是产品经理"],
                "profile": ["偏业务型用户"],
                "preferences": ["回答短一点"],
                "conversationStyle": ["少问"],
                "openThreads": ["最近提到：播客"],
                "doNotAssume": ["不要推断健康信息"],
            }
        ]

        with patch("apps.api.runtime.user_profile_service.list_memory_cards", return_value=cards):
            profile = build_user_profile("user_1")

        self.assertEqual(profile["stableFacts"], ["我是产品经理"])
        self.assertEqual(profile["preferences"], ["回答短一点"])
        self.assertEqual(profile["evidence"], [{"sceneId": "scene_1", "updatedAt": "2026-06-12T01:00:00Z"}])


if __name__ == "__main__":
    unittest.main()

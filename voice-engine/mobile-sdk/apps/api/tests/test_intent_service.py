import unittest

from apps.api.runtime.intent_service import classify_intent


class IntentServiceTest(unittest.TestCase):
    def test_empty_text_returns_unknown(self):
        result = classify_intent("")

        self.assertEqual(result["intent"], "unknown")
        self.assertEqual(result["confidence"], 0.0)

    def test_exit_session_intent(self):
        result = classify_intent("先这样吧，结束通话")

        self.assertEqual(result["intent"], "exit_session")
        self.assertIn("finish_session", result["actions"])

    def test_podcast_request_intent(self):
        result = classify_intent("把这份文档生成播客，读给我听")

        self.assertEqual(result["intent"], "podcast_request")
        self.assertIn("create_podcast_draft", result["actions"])

    def test_memory_update_intent(self):
        result = classify_intent("记住我喜欢短一点的回答")

        self.assertEqual(result["intent"], "memory_update")
        self.assertIn("extract_memory_candidate", result["actions"])

    def test_ad_opportunity_intent(self):
        result = classify_intent("帮我看看附近有没有适合亲子游的酒店套餐")

        self.assertEqual(result["intent"], "ad_opportunity")
        self.assertIn("evaluate_ad_opportunity", result["actions"])


if __name__ == "__main__":
    unittest.main()

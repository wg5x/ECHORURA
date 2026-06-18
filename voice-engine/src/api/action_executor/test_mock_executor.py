import asyncio
import unittest

from api.action_executor.mock_executor import execute_mock_action
from api.main import mock_execute_action
from api.semantic_router.router import SemanticRouter


class MockActionExecutorTest(unittest.TestCase):
    def setUp(self) -> None:
        self.router = SemanticRouter()

    def test_executes_phone_dial_as_mock_native_action_result(self) -> None:
        decision = self.router.route_text(
            "session-1",
            "turn-1",
            "打电话 13641194007",
            agent_profile_id="phone-assistant",
        )

        result = execute_mock_action(decision)

        self.assertEqual(result["type"], "action_result")
        self.assertEqual(result["result_type"], "native_action_result")
        self.assertEqual(result["status"], "mocked")
        self.assertEqual(result["intent"], "phone.dial")
        self.assertEqual(result["summary"], "准备拨号 13641194007")
        self.assertTrue(result["requires_confirmation"])
        self.assertFalse(result["requires_native_bridge"])

    def test_marks_deep_link_message_as_native_bridge_required(self) -> None:
        decision = self.router.route_text(
            "session-1",
            "turn-2",
            "发微信给张三说我到了",
            agent_profile_id="phone-assistant",
        )

        result = execute_mock_action(decision)

        self.assertEqual(result["intent"], "app.open_deep_link")
        self.assertEqual(result["summary"], "准备通过微信给张三发送：我到了")
        self.assertTrue(result["requires_native_bridge"])
        self.assertTrue(result["requires_confirmation"])

    def test_executes_chat_as_noop_result(self) -> None:
        decision = self.router.route_text(
            "session-1",
            "turn-3",
            "帮我做一首歌",
            agent_profile_id="phone-assistant",
        )

        result = execute_mock_action(decision)

        self.assertEqual(result["result_type"], "noop")
        self.assertEqual(result["status"], "skipped")
        self.assertEqual(result["summary"], "当前路由结果不需要执行原生动作。")


class MockActionExecutorHttpTest(unittest.TestCase):
    def test_mock_execute_endpoint_routes_and_executes_text(self) -> None:
        result = asyncio.run(
            mock_execute_action(
                {
                    "text": "拍张照片",
                    "session_id": "session-http",
                    "turn_id": "turn-http",
                    "agent_profile_id": "phone-assistant",
                }
            )
        )

        self.assertEqual(result["route_decision"]["intent"], "camera.capture_photo")
        self.assertEqual(result["action_result"]["intent"], "camera.capture_photo")
        self.assertEqual(result["action_result"]["summary"], "准备打开相机拍照")


if __name__ == "__main__":
    unittest.main()

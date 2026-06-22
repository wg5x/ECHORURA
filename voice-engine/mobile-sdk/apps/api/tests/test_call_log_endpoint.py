import asyncio
import unittest
from unittest.mock import patch

from fastapi.responses import JSONResponse

from apps.api.main import create_runtime_call_log


class FakeRequest:
    def __init__(self, payload):
        self.headers = {}
        self._payload = payload

    async def json(self):
        return self._payload


class CallLogEndpointTest(unittest.TestCase):
    def test_embedded_scene_route_can_save_call_log_with_request_and_session_id(self):
        payload = {
            "id": "log_1",
            "requestId": "req_1",
            "sessionId": "session_1",
            "userId": "scene_route",
            "sceneId": "hs6_user_interview",
            "report": {"id": "log_1", "transcript": [{"role": "user", "text": "我在杭州", "at": "10:00:00"}]},
        }

        with patch("apps.api.main.save_call_log", return_value=payload) as save_call_log:
            response = asyncio.run(create_runtime_call_log(FakeRequest(payload)))

        if isinstance(response, JSONResponse):
            self.assertEqual(response.status_code, 200)
            self.fail(response.body.decode("utf-8"))
        self.assertEqual(response["log"]["requestId"], "req_1")
        save_call_log.assert_called_once_with(payload)

    def test_anonymous_call_log_without_embedded_request_is_rejected(self):
        response = asyncio.run(
            create_runtime_call_log(
                FakeRequest({
                "id": "log_1",
                "userId": "scene_route",
                "sceneId": "hs6_user_interview",
                "report": {"id": "log_1", "transcript": []},
                })
            )
        )

        self.assertIsInstance(response, JSONResponse)
        self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
    unittest.main()

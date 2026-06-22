import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from projects.interview_link.app_config import APP_CONFIG
from projects.interview_link.api.request_store import create_request, list_requests, update_request


class InterviewLinkRequestStoreTest(unittest.TestCase):
    def test_create_request_persists_business_entry_params(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("projects.interview_link.api.request_store.STORE_PATH", Path(temp_dir) / "requests.json"):
                request = create_request(
                    {
                        "name": "张三",
                        "phone": "13800000000",
                        "city": "杭州",
                    }
                )

                self.assertRegex(request["requestId"], r"^req_")
                self.assertEqual(request["status"], "created")
                self.assertEqual(request["entryParams"]["name"], "张三")
                self.assertEqual(request["sceneKind"], APP_CONFIG["sceneKind"])
                self.assertEqual(request["sceneId"], APP_CONFIG["sceneId"])

    def test_update_request_links_platform_session_id(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("projects.interview_link.api.request_store.STORE_PATH", Path(temp_dir) / "requests.json"):
                created = create_request({"name": "张三", "phone": "13800000000", "city": "杭州"})

                updated = update_request(
                    created["requestId"],
                    {"platformSessionId": "session_1", "status": "finished"},
                )

                self.assertEqual(updated["platformSessionId"], "session_1")
                self.assertEqual(updated["status"], "finished")

    def test_list_requests_returns_newest_first(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("projects.interview_link.api.request_store.STORE_PATH", Path(temp_dir) / "requests.json"):
                first = create_request({"name": "张三", "phone": "13800000000", "city": "杭州"})
                second = create_request({"name": "李四", "phone": "13900000000", "city": "深圳"})

                request_ids = [item["requestId"] for item in list_requests()]

                self.assertEqual(request_ids, [second["requestId"], first["requestId"]])


if __name__ == "__main__":
    unittest.main()

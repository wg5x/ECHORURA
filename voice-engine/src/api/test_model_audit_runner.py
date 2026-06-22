from __future__ import annotations

import json
import tempfile
import unittest
import urllib.error
from unittest import mock
from pathlib import Path

from api.memory_eval_runner import load_eval_cases as load_memory_eval_cases
from api.model_audit_runner import generate_memory_model_memories, generate_router_model_decisions
from api.model_audit_runner import OpenAICompatibleJsonClient, _memory_prompt, _parse_json_object_from_text, _router_prompt
from api.semantic_router.eval_runner import load_eval_cases as load_router_eval_cases


class ModelAuditRunnerTest(unittest.TestCase):
    def test_openai_client_defaults_to_agnes_audit_model(self) -> None:
        with mock.patch.dict(
            "os.environ",
            {
                "MODEL_AUDIT_API_KEY": "test-key",
            },
            clear=True,
        ):
            client = OpenAICompatibleJsonClient.from_env()

        self.assertEqual(client.base_url, "https://apihub.agnes-ai.com/v1")
        self.assertEqual(client.model, "agnes-2.0-flash")
        self.assertEqual(client.api_key, "test-key")

    def test_generate_router_model_decisions_writes_eval_compatible_jsonl(self) -> None:
        cases = load_router_eval_cases(
            _write_jsonl(
                [
                    {
                        "id": "router-001",
                        "text": "打开淘宝",
                        "agent_profile_id": "phone-assistant",
                        "expected": {"mode": "native_action", "intent": "app.open"},
                        "tags": ["app"],
                    }
                ]
            )
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            out_path = Path(temp_dir) / "model_decisions.jsonl"

            generate_router_model_decisions(cases, _FakeModelClient({"mode": "chat", "intent": "general"}), out_path)

            record = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertEqual(record["case_id"], "router-001")
            self.assertEqual(record["decision"], {"mode": "chat", "intent": "general"})

    def test_generate_router_model_decisions_applies_policy_guard_and_preserves_raw_decision(self) -> None:
        cases = load_router_eval_cases(
            _write_jsonl(
                [
                    {
                        "id": "router-default-app-001",
                        "text": "打开淘宝",
                        "agent_profile_id": "default",
                        "expected": {"mode": "chat", "intent": "general"},
                        "tags": ["cross_agent"],
                    }
                ]
            )
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            out_path = Path(temp_dir) / "model_decisions.jsonl"

            generate_router_model_decisions(
                cases,
                _FakeModelClient({"mode": "native_action", "intent": "app.open"}),
                out_path,
            )

            record = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertEqual(record["raw_decision"], {"mode": "native_action", "intent": "app.open"})
            self.assertEqual(record["decision"], {"mode": "chat", "intent": "general"})

    def test_generate_router_model_decisions_can_use_parallel_workers(self) -> None:
        cases = load_router_eval_cases(
            _write_jsonl(
                [
                    {
                        "id": f"router-{index}",
                        "text": "打开淘宝",
                        "agent_profile_id": "phone-assistant",
                        "expected": {"mode": "native_action", "intent": "app.open"},
                        "tags": ["app"],
                    }
                    for index in range(3)
                ]
            )
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            out_path = Path(temp_dir) / "model_decisions.jsonl"

            generate_router_model_decisions(
                cases,
                _FakeModelClient({"mode": "native_action", "intent": "app.open"}),
                out_path,
                workers=2,
            )

            self.assertEqual(len(out_path.read_text(encoding="utf-8").splitlines()), 3)

    def test_generate_memory_model_memories_writes_eval_compatible_jsonl(self) -> None:
        cases = load_memory_eval_cases(
            _write_jsonl(
                [
                    {
                        "id": "memory-001",
                        "agent_profile_id": "phone-assistant",
                        "transcript": [{"role": "user", "text": "我喜欢女声"}],
                        "expected": {"contents": ["我喜欢女声"]},
                        "tags": ["memory"],
                    }
                ]
            )
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            out_path = Path(temp_dir) / "model_memories.jsonl"

            generate_memory_model_memories(
                cases,
                _FakeModelClient({"memories": [{"type": "preference", "content": "我喜欢女声", "confidence": 0.8}]}),
                out_path,
            )

            record = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertEqual(record["case_id"], "memory-001")
            self.assertEqual(record["memories"][0]["content"], "我喜欢女声")

    def test_parse_json_object_from_markdown_or_prose(self) -> None:
        self.assertEqual(_parse_json_object_from_text('```json\n{"mode":"chat"}\n```'), {"mode": "chat"})
        self.assertEqual(_parse_json_object_from_text('结果如下：{"memories":[]}'), {"memories": []})

    def test_parse_json_object_uses_first_object_when_model_returns_extra_json(self) -> None:
        self.assertEqual(
            _parse_json_object_from_text('{"mode":"chat","intent":"general"}\n{"mode":"native_action"}'),
            {"mode": "chat", "intent": "general"},
        )

    def test_openai_client_retries_transient_url_errors(self) -> None:
        client = OpenAICompatibleJsonClient(
            base_url="https://example.test/v1",
            api_key="test-key",
            model="test-model",
            retry_delay_seconds=0,
        )
        response = _FakeHttpResponse({"choices": [{"message": {"content": "{\"mode\":\"chat\"}"}}]})

        with mock.patch(
            "api.model_audit_runner.urllib.request.urlopen",
            side_effect=[urllib.error.URLError("transient eof"), response],
        ) as urlopen:
            self.assertEqual(client.complete_json("hello"), {"mode": "chat"})

        self.assertEqual(urlopen.call_count, 2)

    def test_router_prompt_forces_closed_label_set(self) -> None:
        case = load_router_eval_cases(
            _write_jsonl(
                [
                    {
                        "id": "router-001",
                        "text": "今天下午三点开会",
                        "agent_profile_id": "phone-assistant",
                        "expected": {"mode": "native_action", "intent": "calendar.create_event"},
                        "tags": ["calendar"],
                    }
                ]
            )
        )[0]

        prompt = _router_prompt(case)

        self.assertIn("Choose exactly one route from this closed catalog", prompt)
        self.assertIn('"mode":"native_action","intent":"calendar.create_event"', prompt)
        self.assertIn("Do not use scenario for Android phone actions", prompt)

    def test_router_prompt_includes_open_page_and_profile_boundaries(self) -> None:
        case = load_router_eval_cases(
            _write_jsonl(
                [
                    {
                        "id": "router-open-page-001",
                        "text": "打开作品页",
                        "agent_profile_id": "default",
                        "expected": {"mode": "native_action", "intent": "open_page"},
                        "tags": ["open_page"],
                    }
                ]
            )
        )[0]

        prompt = _router_prompt(case)

        self.assertIn('"mode":"native_action","intent":"open_page"', prompt)
        self.assertIn("default profile supports only", prompt)
        self.assertIn("phone-assistant profile supports only", prompt)

    def test_router_prompt_routes_open_gallery_as_pick_image(self) -> None:
        case = load_router_eval_cases(
            _write_jsonl(
                [
                    {
                        "id": "router-gallery-001",
                        "text": "打开相册",
                        "agent_profile_id": "phone-assistant",
                        "expected": {"mode": "native_action", "intent": "gallery.pick_image"},
                        "tags": ["gallery"],
                    }
                ]
            )
        )[0]

        prompt = _router_prompt(case)

        self.assertIn("打开相册", prompt)
        self.assertIn("gallery.pick_image", prompt)
        self.assertIn("Do not use app.open for gallery or album", prompt)

    def test_router_prompt_disambiguates_phone_action_phrases(self) -> None:
        case = load_router_eval_cases(
            _write_jsonl(
                [
                    {
                        "id": "router-phone-disambiguation-001",
                        "text": "帮我发短信告诉他我晚点到",
                        "agent_profile_id": "phone-assistant",
                        "expected": {"mode": "native_action", "intent": "sms.compose"},
                        "tags": ["sms"],
                    }
                ]
            )
        )[0]

        prompt = _router_prompt(case)

        self.assertIn("发短信", prompt)
        self.assertIn("发信息告诉他", prompt)
        self.assertIn("发消息", prompt)
        self.assertIn("sms.compose", prompt)
        self.assertIn("京东搜索", prompt)
        self.assertIn("app.search", prompt)
        self.assertIn("发微信给", prompt)
        self.assertIn("app.open_deep_link", prompt)
        self.assertIn("看电影", prompt)
        self.assertIn("media.play_from_search", prompt)

    def test_router_prompt_disambiguates_default_music_publish(self) -> None:
        case = load_router_eval_cases(
            _write_jsonl(
                [
                    {
                        "id": "router-music-publish-001",
                        "text": "发出去",
                        "agent_profile_id": "default",
                        "expected": {"mode": "scenario", "intent": "publish_work"},
                        "tags": ["music"],
                    }
                ]
            )
        )[0]

        prompt = _router_prompt(case)

        self.assertIn("发出去", prompt)
        self.assertIn("publish_work", prompt)

    def test_router_prompt_includes_default_music_create_example(self) -> None:
        case = load_router_eval_cases(
            _write_jsonl(
                [
                    {
                        "id": "router-music-create-001",
                        "text": "帮我做一首下班路上听的中文 LoFi",
                        "agent_profile_id": "default",
                        "expected": {"mode": "scenario", "intent": "create_song"},
                        "tags": ["music"],
                    }
                ]
            )
        )[0]

        prompt = _router_prompt(case)

        self.assertIn("For default profile music creation", prompt)
        self.assertIn("帮我做一首下班路上听的中文 LoFi", prompt)
        self.assertIn("create_song", prompt)

    def test_memory_prompt_requires_verbatim_user_phrase(self) -> None:
        case = load_memory_eval_cases(
            _write_jsonl(
                [
                    {
                        "id": "memory-001",
                        "agent_profile_id": "phone-assistant",
                        "transcript": [{"role": "user", "text": "我喜欢女声"}],
                        "expected": {"contents": ["我喜欢女声"]},
                        "tags": ["memory"],
                    }
                ]
            )
        )[0]

        prompt = _memory_prompt(case)

        self.assertIn("content must be copied verbatim", prompt)
        self.assertIn("Do not translate", prompt)
        self.assertIn("If there is no durable memory, return", prompt)

    def test_memory_prompt_requires_explicit_memory_request(self) -> None:
        case = load_memory_eval_cases(
            _write_jsonl(
                [
                    {
                        "id": "memory-implicit-001",
                        "agent_profile_id": "phone-assistant",
                        "transcript": [{"role": "user", "text": "我喜欢女声"}],
                        "expected": {"contents": []},
                        "tags": ["implicit"],
                    }
                ]
            )
        )[0]

        prompt = _memory_prompt(case)

        self.assertIn("Only extract memory when the user explicitly asks", prompt)
        self.assertIn("我喜欢女声", prompt)
        self.assertIn("return {\"memories\":[]}", prompt)
        self.assertIn("记住我喜欢女声", prompt)


class _FakeModelClient:
    def __init__(self, response: dict) -> None:
        self.response = response
        self.prompts: list[str] = []

    def complete_json(self, prompt: str) -> dict:
        self.prompts.append(prompt)
        return self.response


class _FakeHttpResponse:
    def __init__(self, body: dict) -> None:
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.body).encode("utf-8")


def _write_jsonl(records: list[dict]) -> Path:
    handle = tempfile.NamedTemporaryFile("w", suffix=".jsonl", encoding="utf-8", delete=False)
    with handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return Path(handle.name)


if __name__ == "__main__":
    unittest.main()

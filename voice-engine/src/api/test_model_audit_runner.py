from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from api.memory_eval_runner import load_eval_cases as load_memory_eval_cases
from api.model_audit_runner import generate_memory_model_memories, generate_router_model_decisions
from api.model_audit_runner import _parse_json_object_from_text
from api.semantic_router.eval_runner import load_eval_cases as load_router_eval_cases


class ModelAuditRunnerTest(unittest.TestCase):
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


class _FakeModelClient:
    def __init__(self, response: dict) -> None:
        self.response = response
        self.prompts: list[str] = []

    def complete_json(self, prompt: str) -> dict:
        self.prompts.append(prompt)
        return self.response


def _write_jsonl(records: list[dict]) -> Path:
    handle = tempfile.NamedTemporaryFile("w", suffix=".jsonl", encoding="utf-8", delete=False)
    with handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return Path(handle.name)


if __name__ == "__main__":
    unittest.main()

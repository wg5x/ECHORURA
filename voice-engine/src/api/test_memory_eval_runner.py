from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from api.memory_eval_runner import (
    default_eval_cases_path,
    load_eval_cases,
    load_model_memories,
    run_memory_eval,
)


class MemoryEvalRunnerTest(unittest.TestCase):
    def test_load_eval_cases_reads_jsonl_cases(self) -> None:
        cases = load_eval_cases(
            _write_jsonl(
                [
                    {
                        "id": "memory-remember-001",
                        "agent_profile_id": "phone-assistant",
                        "transcript": [{"role": "user", "text": "记住我喜欢女声"}],
                        "expected": {"contents": ["我喜欢女声"]},
                        "tags": ["explicit", "voice-preference"],
                    }
                ]
            )
        )

        self.assertEqual(len(cases), 1)
        self.assertEqual(cases[0].id, "memory-remember-001")
        self.assertEqual(cases[0].expected_contents, ("我喜欢女声",))
        self.assertEqual(cases[0].tags, ("explicit", "voice-preference"))

    def test_run_memory_eval_scores_rule_extractor_against_expected_contents(self) -> None:
        cases = load_eval_cases(
            _write_jsonl(
                [
                    {
                        "id": "memory-pass-001",
                        "agent_profile_id": "phone-assistant",
                        "transcript": [{"role": "user", "text": "记住我喜欢女声"}],
                        "expected": {"contents": ["我喜欢女声"]},
                        "tags": ["explicit"],
                    },
                    {
                        "id": "memory-fail-001",
                        "agent_profile_id": "phone-assistant",
                        "transcript": [{"role": "user", "text": "今天的天气怎么样"}],
                        "expected": {"contents": ["我关心天气"]},
                        "tags": ["known-failure"],
                    },
                ]
            )
        )

        report = run_memory_eval(cases)

        self.assertEqual(report["summary"]["case_count"], 2)
        self.assertEqual(report["summary"]["rule"]["passed"], 1)
        self.assertEqual(report["summary"]["rule"]["failed"], 1)
        self.assertTrue(report["records"][0]["rule_pass"])
        self.assertFalse(report["records"][1]["rule_pass"])

    def test_model_memories_are_compared_with_rule_and_expected(self) -> None:
        cases = load_eval_cases(
            _write_jsonl(
                [
                    {
                        "id": "memory-model-001",
                        "agent_profile_id": "phone-assistant",
                        "transcript": [{"role": "user", "text": "记住我喜欢女声"}],
                        "expected": {"contents": ["我喜欢女声"]},
                        "tags": ["explicit"],
                    }
                ]
            )
        )
        model_memories = load_model_memories(
            _write_jsonl(
                [
                    {
                        "case_id": "memory-model-001",
                        "memories": [{"type": "preference", "content": "用户偏好女声音色", "confidence": 0.8}],
                    }
                ]
            )
        )

        report = run_memory_eval(cases, model_memories=model_memories)

        self.assertEqual(report["summary"]["model"]["evaluated"], 1)
        self.assertEqual(report["summary"]["model"]["failed"], 1)
        self.assertEqual(report["summary"]["disagreements"], 1)
        self.assertEqual(report["records"][0]["rule_model_diff"][0]["field"], "contents")

    def test_model_memories_report_normalized_match_for_reworded_contents(self) -> None:
        cases = load_eval_cases(
            _write_jsonl(
                [
                    {
                        "id": "memory-model-normalized-001",
                        "agent_profile_id": "phone-assistant",
                        "transcript": [{"role": "user", "text": "记住我喜欢女声"}],
                        "expected": {"contents": ["我喜欢女声"]},
                        "tags": ["explicit"],
                    }
                ]
            )
        )
        model_memories = load_model_memories(
            _write_jsonl(
                [
                    {
                        "case_id": "memory-model-normalized-001",
                        "memories": [{"type": "preference", "content": "用户喜欢女声（prefer female voice）"}],
                    }
                ]
            )
        )

        report = run_memory_eval(cases, model_memories=model_memories)

        self.assertEqual(report["summary"]["model"]["passed"], 0)
        self.assertEqual(report["summary"]["model_normalized"]["passed"], 1)
        self.assertFalse(report["records"][0]["model_pass"])
        self.assertTrue(report["records"][0]["model_normalized_pass"])

    def test_model_memories_normalize_avoidance_wording(self) -> None:
        cases = load_eval_cases(
            _write_jsonl(
                [
                    {
                        "id": "memory-model-avoidance-normalized-001",
                        "agent_profile_id": "phone-assistant",
                        "transcript": [{"role": "user", "text": "以后别再用男声"}],
                        "expected": {"contents": ["不要用男声"]},
                        "tags": ["explicit", "avoidance"],
                    }
                ]
            )
        )
        model_memories = load_model_memories(
            _write_jsonl(
                [
                    {
                        "case_id": "memory-model-avoidance-normalized-001",
                        "memories": [{"type": "preference", "content": "以后别再用男声"}],
                    }
                ]
            )
        )

        report = run_memory_eval(cases, model_memories=model_memories)

        self.assertEqual(report["summary"]["model"]["passed"], 0)
        self.assertEqual(report["summary"]["model_normalized"]["passed"], 1)
        self.assertFalse(report["records"][0]["model_pass"])
        self.assertTrue(report["records"][0]["model_normalized_pass"])

    def test_default_eval_dataset_has_400_persisted_cases(self) -> None:
        cases = load_eval_cases(default_eval_cases_path())
        ids = {case.id for case in cases}
        agent_transcripts = {
            (case.agent_profile_id, tuple(event.get("text") for event in case.transcript)) for case in cases
        }

        self.assertEqual(len(cases), 400)
        self.assertEqual(len(ids), 400)
        self.assertEqual(len(agent_transcripts), 400)
        self.assertIn("memory-remember-001", ids)
        self.assertIn("memory-negative-001", ids)


def _write_jsonl(records: list[dict]) -> Path:
    handle = tempfile.NamedTemporaryFile("w", suffix=".jsonl", encoding="utf-8", delete=False)
    with handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return Path(handle.name)


if __name__ == "__main__":
    unittest.main()

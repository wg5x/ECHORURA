from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from api.semantic_router.eval_runner import (
    default_eval_cases_path,
    load_eval_cases,
    load_model_decisions,
    run_router_eval,
)


class RouterEvalRunnerTest(unittest.TestCase):
    def test_load_eval_cases_reads_jsonl_cases(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "cases.jsonl"
            path.write_text(
                json.dumps(
                    {
                        "id": "phone-weather-001",
                        "text": "今天的天气怎么样",
                        "agent_profile_id": "phone-assistant",
                        "expected": {"mode": "chat", "intent": "general"},
                        "tags": ["weather", "negative-calendar"],
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )

            cases = load_eval_cases(path)

        self.assertEqual(len(cases), 1)
        self.assertEqual(cases[0].id, "phone-weather-001")
        self.assertEqual(cases[0].expected, {"mode": "chat", "intent": "general"})
        self.assertEqual(cases[0].tags, ("weather", "negative-calendar"))

    def test_run_router_eval_scores_rule_router_against_expected_fields(self) -> None:
        cases = load_eval_cases(
            _write_jsonl(
                [
                    {
                        "id": "calendar-001",
                        "text": "今天下午三点开会",
                        "agent_profile_id": "phone-assistant",
                        "expected": {"mode": "native_action", "intent": "calendar.create_event"},
                        "tags": ["calendar"],
                    },
                    {
                        "id": "weather-001",
                        "text": "今天的天气怎么样",
                        "agent_profile_id": "phone-assistant",
                        "expected": {"mode": "native_action", "intent": "calendar.create_event"},
                        "tags": ["weather", "known-failure"],
                    },
                ]
            )
        )

        report = run_router_eval(cases)

        self.assertEqual(report["summary"]["case_count"], 2)
        self.assertEqual(report["summary"]["rule"]["passed"], 1)
        self.assertEqual(report["summary"]["rule"]["failed"], 1)
        self.assertTrue(report["records"][0]["rule_pass"])
        self.assertFalse(report["records"][1]["rule_pass"])

    def test_model_decisions_are_compared_with_rule_and_expected(self) -> None:
        cases = load_eval_cases(
            _write_jsonl(
                [
                    {
                        "id": "phone-dial-001",
                        "text": "打电话 13641194007",
                        "agent_profile_id": "phone-assistant",
                        "expected": {"mode": "native_action", "intent": "phone.dial"},
                        "tags": ["phone"],
                    }
                ]
            )
        )
        model_decisions = load_model_decisions(
            _write_jsonl(
                [
                    {
                        "case_id": "phone-dial-001",
                        "decision": {"mode": "chat", "intent": "general"},
                    }
                ]
            )
        )

        report = run_router_eval(cases, model_decisions=model_decisions)

        self.assertEqual(report["summary"]["model"]["evaluated"], 1)
        self.assertEqual(report["summary"]["model"]["failed"], 1)
        self.assertEqual(report["summary"]["disagreements"], 1)
        self.assertEqual(report["records"][0]["rule_model_diff"][0]["field"], "mode")

    def test_default_eval_dataset_has_400_persisted_cases(self) -> None:
        cases = load_eval_cases(default_eval_cases_path())
        ids = {case.id for case in cases}
        agent_texts = {(case.agent_profile_id, case.text) for case in cases}

        self.assertEqual(len(cases), 400)
        self.assertEqual(len(ids), 400)
        self.assertEqual(len(agent_texts), 400)
        self.assertIn("phone-weather-001", ids)
        self.assertIn("phone-calendar-001", ids)


def _write_jsonl(records: list[dict]) -> Path:
    handle = tempfile.NamedTemporaryFile("w", suffix=".jsonl", encoding="utf-8", delete=False)
    with handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return Path(handle.name)

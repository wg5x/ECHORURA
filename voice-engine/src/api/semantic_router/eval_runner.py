from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .router import SemanticRouter


EVAL_DECISION_FIELDS = ("mode", "intent", "scenario_id", "scenario_intent")


@dataclass(frozen=True)
class EvalCase:
    id: str
    text: str
    agent_profile_id: str
    expected: dict[str, Any]
    tags: tuple[str, ...]


def default_eval_cases_path() -> Path:
    return Path(__file__).with_name("eval_cases.jsonl")


def load_eval_cases(path: str | Path) -> list[EvalCase]:
    cases: list[EvalCase] = []
    for line_number, record in _read_jsonl(path):
        case_id = str(record.get("id") or "").strip()
        text = str(record.get("text") or "").strip()
        agent_profile_id = str(record.get("agent_profile_id") or "default").strip() or "default"
        expected = record.get("expected")
        tags = record.get("tags") or []

        if not case_id:
            raise ValueError(f"{path}:{line_number} missing id")
        if not text:
            raise ValueError(f"{path}:{line_number} missing text")
        if not isinstance(expected, dict) or not expected:
            raise ValueError(f"{path}:{line_number} missing expected decision fields")
        if not isinstance(tags, list):
            raise ValueError(f"{path}:{line_number} tags must be a list")

        cases.append(
            EvalCase(
                id=case_id,
                text=text,
                agent_profile_id=agent_profile_id,
                expected=dict(expected),
                tags=tuple(str(tag) for tag in tags),
            )
        )
    return cases


def load_model_decisions(path: str | Path) -> dict[str, dict[str, Any]]:
    decisions: dict[str, dict[str, Any]] = {}
    for line_number, record in _read_jsonl(path):
        case_id = str(record.get("case_id") or record.get("id") or "").strip()
        decision = record.get("decision") or record.get("route_decision")
        if not case_id:
            raise ValueError(f"{path}:{line_number} missing case_id")
        if not isinstance(decision, dict):
            raise ValueError(f"{path}:{line_number} missing decision")
        decisions[case_id] = dict(decision)
    return decisions


def run_router_eval(
    cases: list[EvalCase],
    model_decisions: dict[str, dict[str, Any]] | None = None,
    router: SemanticRouter | None = None,
) -> dict[str, Any]:
    router = router or SemanticRouter()
    model_decisions = model_decisions or {}
    records: list[dict[str, Any]] = []
    rule_passed = 0
    model_evaluated = 0
    model_passed = 0
    disagreements = 0

    for case in cases:
        rule_decision = router.route_text(
            session_id="router-eval",
            turn_id=case.id,
            text=case.text,
            source="router_eval",
            agent_profile_id=case.agent_profile_id,
        )
        rule_projection = _project_decision(rule_decision)
        rule_pass = _matches_expected(rule_decision, case.expected)
        if rule_pass:
            rule_passed += 1

        model_decision = model_decisions.get(case.id)
        model_pass: bool | None = None
        rule_model_diff: list[dict[str, Any]] = []
        if model_decision is not None:
            model_evaluated += 1
            model_pass = _matches_expected(model_decision, case.expected)
            if model_pass:
                model_passed += 1
            rule_model_diff = _diff_decisions(rule_decision, model_decision)
            if rule_model_diff:
                disagreements += 1

        records.append(
            {
                "case_id": case.id,
                "text": case.text,
                "agent_profile_id": case.agent_profile_id,
                "tags": list(case.tags),
                "expected": case.expected,
                "rule_decision": rule_projection,
                "rule_pass": rule_pass,
                "model_decision": _project_decision(model_decision) if model_decision is not None else None,
                "model_pass": model_pass,
                "rule_model_diff": rule_model_diff,
            }
        )

    case_count = len(cases)
    rule_failed = case_count - rule_passed
    model_failed = model_evaluated - model_passed
    return {
        "summary": {
            "case_count": case_count,
            "rule": {
                "evaluated": case_count,
                "passed": rule_passed,
                "failed": rule_failed,
                "accuracy": _accuracy(rule_passed, case_count),
            },
            "model": {
                "evaluated": model_evaluated,
                "passed": model_passed,
                "failed": model_failed,
                "accuracy": _accuracy(model_passed, model_evaluated),
            },
            "disagreements": disagreements,
        },
        "records": records,
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Compare semantic router decisions against persisted eval cases.")
    parser.add_argument("--cases", default=str(default_eval_cases_path()), help="JSONL eval case file")
    parser.add_argument("--model-decisions", help="Optional JSONL model decision file")
    parser.add_argument("--out", help="Optional JSON report output path")
    args = parser.parse_args(argv)

    cases = load_eval_cases(args.cases)
    model_decisions = load_model_decisions(args.model_decisions) if args.model_decisions else None
    report = run_router_eval(cases, model_decisions=model_decisions)
    output = json.dumps(report, ensure_ascii=False, indent=2)

    if args.out:
        Path(args.out).write_text(output + "\n", encoding="utf-8")
    print(output)


def _read_jsonl(path: str | Path) -> list[tuple[int, dict[str, Any]]]:
    records: list[tuple[int, dict[str, Any]]] = []
    for line_number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        record = json.loads(stripped)
        if not isinstance(record, dict):
            raise ValueError(f"{path}:{line_number} must be a JSON object")
        records.append((line_number, record))
    return records


def _matches_expected(decision: dict[str, Any], expected: dict[str, Any]) -> bool:
    return all(decision.get(field) == value for field, value in expected.items())


def _project_decision(decision: dict[str, Any] | None) -> dict[str, Any]:
    if decision is None:
        return {}
    return {field: decision[field] for field in EVAL_DECISION_FIELDS if field in decision}


def _diff_decisions(rule_decision: dict[str, Any], model_decision: dict[str, Any]) -> list[dict[str, Any]]:
    diff: list[dict[str, Any]] = []
    for field in EVAL_DECISION_FIELDS:
        rule_value = rule_decision.get(field)
        model_value = model_decision.get(field)
        if rule_value != model_value:
            diff.append({"field": field, "rule": rule_value, "model": model_value})
    return diff


def _accuracy(passed: int, evaluated: int) -> float | None:
    if evaluated == 0:
        return None
    return round(passed / evaluated, 4)


if __name__ == "__main__":
    main()

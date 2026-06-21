from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .memory_store import RuleMemoryExtractor


@dataclass(frozen=True)
class MemoryEvalCase:
    id: str
    agent_profile_id: str
    transcript: list[dict[str, Any]]
    expected_contents: tuple[str, ...]
    tags: tuple[str, ...]


def default_eval_cases_path() -> Path:
    return Path(__file__).with_name("memory_eval_cases.jsonl")


def load_eval_cases(path: str | Path) -> list[MemoryEvalCase]:
    cases: list[MemoryEvalCase] = []
    for line_number, record in _read_jsonl(path):
        case_id = str(record.get("id") or "").strip()
        agent_profile_id = str(record.get("agent_profile_id") or "default").strip() or "default"
        transcript = record.get("transcript")
        expected = record.get("expected")
        tags = record.get("tags") or []

        if not case_id:
            raise ValueError(f"{path}:{line_number} missing id")
        if not isinstance(transcript, list) or not transcript:
            raise ValueError(f"{path}:{line_number} missing transcript")
        if not all(isinstance(event, dict) and event.get("text") for event in transcript):
            raise ValueError(f"{path}:{line_number} transcript events must include text")
        if not isinstance(expected, dict) or not isinstance(expected.get("contents"), list):
            raise ValueError(f"{path}:{line_number} missing expected contents")
        if not isinstance(tags, list):
            raise ValueError(f"{path}:{line_number} tags must be a list")

        cases.append(
            MemoryEvalCase(
                id=case_id,
                agent_profile_id=agent_profile_id,
                transcript=[dict(event) for event in transcript],
                expected_contents=tuple(str(content) for content in expected["contents"]),
                tags=tuple(str(tag) for tag in tags),
            )
        )
    return cases


def load_model_memories(path: str | Path) -> dict[str, list[dict[str, Any]]]:
    memories_by_case: dict[str, list[dict[str, Any]]] = {}
    for line_number, record in _read_jsonl(path):
        case_id = str(record.get("case_id") or record.get("id") or "").strip()
        memories = record.get("memories")
        if not case_id:
            raise ValueError(f"{path}:{line_number} missing case_id")
        if not isinstance(memories, list):
            raise ValueError(f"{path}:{line_number} missing memories")
        memories_by_case[case_id] = [dict(memory) for memory in memories if isinstance(memory, dict)]
    return memories_by_case


def run_memory_eval(
    cases: list[MemoryEvalCase],
    model_memories: dict[str, list[dict[str, Any]]] | None = None,
    rule_extractor: RuleMemoryExtractor | None = None,
) -> dict[str, Any]:
    rule_extractor = rule_extractor or RuleMemoryExtractor()
    model_memories = model_memories or {}
    records: list[dict[str, Any]] = []
    rule_passed = 0
    rule_normalized_passed = 0
    model_evaluated = 0
    model_passed = 0
    model_normalized_passed = 0
    disagreements = 0

    for case in cases:
        rule_memories = rule_extractor.extract(
            session_id=f"memory-eval-{case.id}",
            agent_profile_id=case.agent_profile_id,
            transcript=case.transcript,
        )
        rule_contents = _memory_contents(rule_memories)
        expected_contents = list(case.expected_contents)
        expected_normalized_contents = _normalize_contents(expected_contents)
        rule_normalized_contents = _normalize_contents(rule_contents)
        rule_pass = rule_contents == expected_contents
        rule_normalized_pass = _contents_match(rule_normalized_contents, expected_normalized_contents)
        if rule_pass:
            rule_passed += 1
        if rule_normalized_pass:
            rule_normalized_passed += 1

        imported_model_memories = model_memories.get(case.id)
        model_contents: list[str] | None = None
        model_normalized_contents: list[str] | None = None
        model_pass: bool | None = None
        model_normalized_pass: bool | None = None
        rule_model_diff: list[dict[str, Any]] = []
        if imported_model_memories is not None:
            model_evaluated += 1
            model_contents = _memory_contents(imported_model_memories)
            model_normalized_contents = _normalize_contents(model_contents)
            model_pass = model_contents == expected_contents
            model_normalized_pass = _contents_match(model_normalized_contents, expected_normalized_contents)
            if model_pass:
                model_passed += 1
            if model_normalized_pass:
                model_normalized_passed += 1
            rule_model_diff = _diff_contents(rule_contents, model_contents)
            if rule_model_diff:
                disagreements += 1

        records.append(
            {
                "case_id": case.id,
                "agent_profile_id": case.agent_profile_id,
                "tags": list(case.tags),
                "transcript": case.transcript,
                "expected_contents": expected_contents,
                "rule_memories": _project_memories(rule_memories),
                "rule_contents": rule_contents,
                "rule_normalized_contents": rule_normalized_contents,
                "rule_pass": rule_pass,
                "rule_normalized_pass": rule_normalized_pass,
                "model_memories": _project_memories(imported_model_memories) if imported_model_memories is not None else None,
                "model_contents": model_contents,
                "model_normalized_contents": model_normalized_contents,
                "model_pass": model_pass,
                "model_normalized_pass": model_normalized_pass,
                "rule_model_diff": rule_model_diff,
            }
        )

    case_count = len(cases)
    return {
        "summary": {
            "case_count": case_count,
            "rule": {
                "evaluated": case_count,
                "passed": rule_passed,
                "failed": case_count - rule_passed,
                "accuracy": _accuracy(rule_passed, case_count),
            },
            "rule_normalized": {
                "evaluated": case_count,
                "passed": rule_normalized_passed,
                "failed": case_count - rule_normalized_passed,
                "accuracy": _accuracy(rule_normalized_passed, case_count),
            },
            "model": {
                "evaluated": model_evaluated,
                "passed": model_passed,
                "failed": model_evaluated - model_passed,
                "accuracy": _accuracy(model_passed, model_evaluated),
            },
            "model_normalized": {
                "evaluated": model_evaluated,
                "passed": model_normalized_passed,
                "failed": model_evaluated - model_normalized_passed,
                "accuracy": _accuracy(model_normalized_passed, model_evaluated),
            },
            "disagreements": disagreements,
        },
        "records": records,
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Compare memory extraction results against persisted eval cases.")
    parser.add_argument("--cases", default=str(default_eval_cases_path()), help="JSONL eval case file")
    parser.add_argument("--model-memories", help="Optional JSONL model memory extraction file")
    parser.add_argument("--out", help="Optional JSON report output path")
    args = parser.parse_args(argv)

    cases = load_eval_cases(args.cases)
    model_memories = load_model_memories(args.model_memories) if args.model_memories else None
    report = run_memory_eval(cases, model_memories=model_memories)
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


def _memory_contents(memories: list[dict[str, Any]]) -> list[str]:
    return [str(memory.get("content") or "") for memory in memories if memory.get("content")]


def _project_memories(memories: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    if memories is None:
        return []
    projected: list[dict[str, Any]] = []
    for memory in memories:
        projected.append(
            {
                key: memory[key]
                for key in ("type", "content", "source", "confidence")
                if key in memory
            }
        )
    return projected


def _diff_contents(rule_contents: list[str], model_contents: list[str]) -> list[dict[str, Any]]:
    if rule_contents == model_contents:
        return []
    return [{"field": "contents", "rule": rule_contents, "model": model_contents}]


def _accuracy(passed: int, evaluated: int) -> float | None:
    if evaluated == 0:
        return None
    return round(passed / evaluated, 4)


def _normalize_contents(contents: list[str]) -> list[str]:
    return [_normalize_content(content) for content in contents if _normalize_content(content)]


def _normalize_content(content: str) -> str:
    text = str(content or "")
    text = text.split("（", 1)[0].split("(", 1)[0]
    text = text.strip()
    for prefix in ("用户偏好", "用户喜欢", "用户不喜欢", "用户讨厌", "用户", "我"):
        if text.startswith(prefix):
            text = text[len(prefix) :]
            break
    for prefix in ("以后别再", "以后不要再", "以后不要", "不要再", "别再"):
        if text.startswith(prefix):
            text = "不要" + text[len(prefix) :]
            break
    remove_chars = set(" \t\r\n，。,.；;：:、-_/")
    return "".join(char for char in text.lower() if char not in remove_chars)


def _contents_match(actual: list[str], expected: list[str]) -> bool:
    if len(actual) != len(expected):
        return False
    unmatched = actual[:]
    for expected_content in expected:
        match_index = next(
            (
                index
                for index, actual_content in enumerate(unmatched)
                if actual_content == expected_content
                or actual_content in expected_content
                or expected_content in actual_content
            ),
            -1,
        )
        if match_index < 0:
            return False
        unmatched.pop(match_index)
    return True


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import json
import os
import urllib.request
from pathlib import Path
from typing import Protocol

from .memory_eval_runner import default_eval_cases_path as default_memory_cases_path
from .memory_eval_runner import load_eval_cases as load_memory_eval_cases
from .semantic_router.eval_runner import default_eval_cases_path as default_router_cases_path
from .semantic_router.eval_runner import load_eval_cases as load_router_eval_cases


class JsonModelClient(Protocol):
    def complete_json(self, prompt: str) -> dict:
        ...


class OpenAICompatibleJsonClient:
    def __init__(self, base_url: str, api_key: str, model: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model

    @classmethod
    def from_env(cls) -> "OpenAICompatibleJsonClient":
        base_url = os.environ.get("MODEL_AUDIT_BASE_URL", "").strip()
        api_key = os.environ.get("MODEL_AUDIT_API_KEY", "").strip()
        model = os.environ.get("MODEL_AUDIT_MODEL", "").strip()
        if not base_url or not api_key or not model:
            raise RuntimeError("MODEL_AUDIT_BASE_URL, MODEL_AUDIT_API_KEY, and MODEL_AUDIT_MODEL are required.")
        return cls(base_url=base_url, api_key=api_key, model=model)

    def complete_json(self, prompt: str) -> dict:
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "Return only one valid JSON object. Do not include markdown or prose.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }
        request = urllib.request.Request(
            url=f"{self.base_url}/chat/completions",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            body = json.loads(response.read().decode("utf-8"))
        content = body["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        if not isinstance(parsed, dict):
            raise ValueError("Model response must be a JSON object.")
        return parsed


def generate_router_model_decisions(cases, client: JsonModelClient, out_path: Path, limit: int | None = None) -> Path:
    selected_cases = cases[:limit] if limit else cases
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as file:
        for case in selected_cases:
            decision = client.complete_json(_router_prompt(case))
            file.write(
                json.dumps(
                    {
                        "case_id": case.id,
                        "decision": {
                            key: decision[key]
                            for key in ("mode", "intent", "scenario_id", "scenario_intent")
                            if key in decision
                        },
                    },
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
                + "\n"
            )
    return out_path


def generate_memory_model_memories(cases, client: JsonModelClient, out_path: Path, limit: int | None = None) -> Path:
    selected_cases = cases[:limit] if limit else cases
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as file:
        for case in selected_cases:
            response = client.complete_json(_memory_prompt(case))
            memories = response.get("memories") if isinstance(response.get("memories"), list) else []
            file.write(
                json.dumps(
                    {
                        "case_id": case.id,
                        "memories": [memory for memory in memories if isinstance(memory, dict)],
                    },
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
                + "\n"
            )
    return out_path


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Generate offline model labels for rule audit eval cases.")
    parser.add_argument("--kind", choices=("router", "memory", "both"), default="both")
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args(argv)

    client = OpenAICompatibleJsonClient.from_env()
    outputs: dict[str, str] = {}
    if args.kind in {"router", "both"}:
        outputs["router_model_decisions"] = str(
            generate_router_model_decisions(
                load_router_eval_cases(default_router_cases_path()),
                client,
                args.out_dir / "router_model_decisions.jsonl",
                limit=args.limit,
            )
        )
    if args.kind in {"memory", "both"}:
        outputs["memory_model_memories"] = str(
            generate_memory_model_memories(
                load_memory_eval_cases(default_memory_cases_path()),
                client,
                args.out_dir / "memory_model_memories.jsonl",
                limit=args.limit,
            )
        )
    print(json.dumps(outputs, ensure_ascii=False, indent=2))


def _router_prompt(case) -> str:
    return (
        "Label this voice command for semantic routing. "
        "Return JSON with fields mode and intent, and optional scenario_id/scenario_intent.\n"
        f"agent_profile_id: {case.agent_profile_id}\n"
        f"text: {case.text}"
    )


def _memory_prompt(case) -> str:
    return (
        "Extract long-term user memories from this transcript. "
        "Return JSON: {\"memories\":[{\"type\":\"preference\",\"content\":\"...\",\"confidence\":0.0}]}.\n"
        f"agent_profile_id: {case.agent_profile_id}\n"
        f"transcript: {json.dumps(case.transcript, ensure_ascii=False)}"
    )


if __name__ == "__main__":
    main()

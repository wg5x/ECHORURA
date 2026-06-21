from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Protocol


class MemoryExtractor(Protocol):
    def extract(self, session_id: str, agent_profile_id: str, transcript: list[dict]) -> list[dict]:
        ...


class RuleMemoryExtractor:
    patterns = (
        re.compile(r"(?:请你)?记住(.+)$"),
        re.compile(r"以后你要记得(.+)$"),
        re.compile(r"我的偏好是(.+)$"),
        re.compile(r"我不喜欢(.+)$"),
        re.compile(r"我讨厌(.+)$"),
        re.compile(r"^(?:以后)?(?:不要|别)再?(.+)$"),
        re.compile(r"我喜欢(.+)$"),
    )

    def extract(self, session_id: str, agent_profile_id: str, transcript: list[dict]) -> list[dict]:
        memories: list[dict] = []
        for event in transcript:
            if event.get("role") != "user":
                continue
            content = self._extract_content(str(event.get("text") or ""))
            if not content:
                continue
            memories.append(
                {
                    "id": f"{session_id}-memory-{len(memories) + 1}",
                    "session_id": session_id,
                    "agent_profile_id": agent_profile_id,
                    "type": "explicit",
                    "content": content,
                    "source": "rule",
                    "confidence": 1.0,
                    "created_at": _now(),
                }
            )
        return memories

    def _extract_content(self, text: str) -> str:
        text = text.strip()
        for pattern in self.patterns:
            match = pattern.search(text)
            if not match:
                continue
            content = match.group(1).strip(" ，。,.")
            if pattern.pattern.startswith("我不喜欢"):
                content = f"我不喜欢{content}"
            if pattern.pattern.startswith("我讨厌"):
                content = f"我讨厌{content}"
            if pattern.pattern.startswith("^(?:以后)?"):
                content = f"不要{content}"
            if pattern.pattern.startswith("我喜欢"):
                content = f"我喜欢{content}"
            return content
        return ""


class NoopModelMemoryExtractor:
    status = "not_configured"

    def extract(self, session_id: str, agent_profile_id: str, transcript: list[dict]) -> list[dict]:
        return []


class LongTermMemoryStore:
    def __init__(
        self,
        base_dir: Path,
        rule_extractor: MemoryExtractor | None = None,
        model_extractor: MemoryExtractor | None = None,
    ) -> None:
        self.base_dir = base_dir
        self.rule_extractor = rule_extractor or RuleMemoryExtractor()
        self.model_extractor = model_extractor or NoopModelMemoryExtractor()

    def extract_compare_and_persist(self, session_id: str, agent_profile_id: str, transcript: list[dict]) -> dict:
        with ThreadPoolExecutor(max_workers=2) as executor:
            rule_future = executor.submit(self.rule_extractor.extract, session_id, agent_profile_id, transcript)
            model_future = executor.submit(self.model_extractor.extract, session_id, agent_profile_id, transcript)
            rule_memories = rule_future.result()
            model_memories = model_future.result()
        extraction = {
            "session_id": session_id,
            "agent_profile_id": agent_profile_id,
            "accepted_source": "rule",
            "rule": {"status": "ok", "memories": rule_memories},
            "model": {
                "status": getattr(self.model_extractor, "status", "ok"),
                "memories": model_memories,
            },
            "diff": _diff_memories(rule_memories, model_memories),
        }
        self._append_memories(agent_profile_id, rule_memories)
        return extraction

    def build_memory_context(
        self,
        agent_profile_id: str,
        session_ids: list[str] | None = None,
        limit: int = 8,
    ) -> dict:
        session_ids = _sanitize_ids(session_ids or [])
        memories = _dedupe_memories(
            [*self.load_memories(agent_profile_id), *self.load_session_memories(agent_profile_id, session_ids)]
        )
        memories = memories[-limit:]
        lines = [f"- {memory['content']}" for memory in memories if memory.get("content")]
        return {
            "agent_profile_id": agent_profile_id,
            "session_ids": session_ids,
            "memories": memories,
            "system_role_text": "长期记忆：\n" + "\n".join(lines) if lines else "",
        }

    def load_memories(self, agent_profile_id: str) -> list[dict]:
        path = self._memory_file(agent_profile_id)
        if not path.exists():
            return []
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def _append_memories(self, agent_profile_id: str, memories: list[dict]) -> None:
        if not memories:
            return
        self.base_dir.mkdir(parents=True, exist_ok=True)
        with self._memory_file(agent_profile_id).open("a", encoding="utf-8") as file:
            for memory in memories:
                file.write(json.dumps(memory, ensure_ascii=False, separators=(",", ":")) + "\n")
        self.save_session_memories(
            session_id=str(memories[0].get("session_id") or ""),
            agent_profile_id=agent_profile_id,
            memories=memories,
        )

    def save_session_memories(self, session_id: str, agent_profile_id: str, memories: list[dict]) -> None:
        session_id = _safe_id(session_id)
        if not session_id or not memories:
            return
        self._session_memory_dir().mkdir(parents=True, exist_ok=True)
        with self._session_memory_file(session_id).open("a", encoding="utf-8") as file:
            for memory in memories:
                if memory.get("agent_profile_id") != agent_profile_id:
                    continue
                file.write(json.dumps(memory, ensure_ascii=False, separators=(",", ":")) + "\n")

    def load_session_memories(self, agent_profile_id: str, session_ids: list[str]) -> list[dict]:
        memories: list[dict] = []
        for session_id in _sanitize_ids(session_ids):
            path = self._session_memory_file(session_id)
            if not path.exists():
                continue
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                memory = json.loads(line)
                if memory.get("agent_profile_id") == agent_profile_id:
                    memories.append(memory)
        return memories

    def _memory_file(self, agent_profile_id: str) -> Path:
        return self.base_dir / f"{_safe_id(agent_profile_id or 'default')}.jsonl"

    def _session_memory_dir(self) -> Path:
        return self.base_dir / "sessions"

    def _session_memory_file(self, session_id: str) -> Path:
        return self._session_memory_dir() / f"{_safe_id(session_id)}.jsonl"


def _diff_memories(rule_memories: list[dict], model_memories: list[dict]) -> list[dict]:
    rule_contents = [memory.get("content") for memory in rule_memories]
    model_contents = [memory.get("content") for memory in model_memories]
    if rule_contents == model_contents:
        return []
    return [{"field": "memories", "rule": rule_contents, "model": model_contents}]


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _sanitize_ids(ids: list[str]) -> list[str]:
    result: list[str] = []
    for raw_id in ids:
        safe_id = _safe_id(str(raw_id or ""))
        if safe_id:
            result.append(safe_id)
    return result


def _safe_id(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]", "_", value).strip("_")


def _dedupe_memories(memories: list[dict]) -> list[dict]:
    seen: set[tuple[str, str, str]] = set()
    deduped: list[dict] = []
    for memory in memories:
        key = (
            str(memory.get("agent_profile_id") or ""),
            str(memory.get("session_id") or ""),
            str(memory.get("content") or ""),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(memory)
    return deduped

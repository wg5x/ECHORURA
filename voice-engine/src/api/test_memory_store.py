import json
import tempfile
import threading
import unittest
from pathlib import Path

from .memory_store import LongTermMemoryStore, RuleMemoryExtractor


class MemoryStoreTest(unittest.TestCase):
    def test_rule_extractor_reads_explicit_memory_requests(self) -> None:
        extractor = RuleMemoryExtractor()

        memories = extractor.extract(
            session_id="session-1",
            agent_profile_id="phone-assistant",
            transcript=[
                {"role": "user", "text": "记住我喜欢女声"},
                {"role": "assistant", "text": "好的，我记住了。"},
                {"role": "user", "text": "以后你要记得我常用淘宝"},
            ],
        )

        self.assertEqual([memory["content"] for memory in memories], ["我喜欢女声", "我常用淘宝"])
        self.assertEqual(memories[0]["source"], "rule")
        self.assertEqual(memories[0]["session_id"], "session-1")

    def test_rule_extractor_reads_negative_preference_requests(self) -> None:
        extractor = RuleMemoryExtractor()

        memories = extractor.extract(
            session_id="session-1",
            agent_profile_id="phone-assistant",
            transcript=[
                {"role": "user", "text": "记住我不喜欢男声"},
                {"role": "user", "text": "记住我讨厌每次都问确认"},
                {"role": "user", "text": "以后别再用男声"},
                {"role": "assistant", "text": "好的，我会记住。"},
            ],
        )

        self.assertEqual(
            [memory["content"] for memory in memories],
            ["我不喜欢男声", "我讨厌每次都问确认", "不要用男声"],
        )

    def test_rule_extractor_ignores_implicit_preference_chat(self) -> None:
        extractor = RuleMemoryExtractor()

        memories = extractor.extract(
            session_id="session-1",
            agent_profile_id="phone-assistant",
            transcript=[
                {"role": "user", "text": "我喜欢女生"},
                {"role": "user", "text": "我不喜欢男声"},
                {"role": "user", "text": "我讨厌每次都问确认"},
            ],
        )

        self.assertEqual(memories, [])

    def test_store_runs_rule_and_model_extractors_but_accepts_rule_memories(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = LongTermMemoryStore(
                base_dir=Path(temp_dir),
                model_extractor=_FakeModelExtractor(
                    [{"type": "preference", "content": "用户偏好女声音色", "confidence": 0.8}]
                ),
            )

            extraction = store.extract_compare_and_persist(
                session_id="session-1",
                agent_profile_id="phone-assistant",
                transcript=[{"role": "user", "text": "记住我喜欢女声"}],
            )
            context = store.build_memory_context("phone-assistant")

            memory_records = _read_jsonl(Path(temp_dir) / "phone-assistant.jsonl")
            self.assertEqual(extraction["accepted_source"], "rule")
            self.assertEqual(extraction["rule"]["memories"][0]["content"], "我喜欢女声")
            self.assertEqual(extraction["model"]["memories"][0]["content"], "用户偏好女声音色")
            self.assertEqual(extraction["diff"][0]["field"], "memories")
            self.assertEqual(memory_records[0]["content"], "我喜欢女声")
            self.assertIn("我喜欢女声", context["system_role_text"])

    def test_build_memory_context_combines_global_and_selected_session_memories(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = LongTermMemoryStore(base_dir=Path(temp_dir))
            store.extract_compare_and_persist(
                session_id="global-session",
                agent_profile_id="phone-assistant",
                transcript=[{"role": "user", "text": "记住我喜欢简短回答"}],
            )
            store.save_session_memories(
                session_id="session-a",
                agent_profile_id="phone-assistant",
                memories=[
                    {
                        "session_id": "session-a",
                        "agent_profile_id": "phone-assistant",
                        "content": "我不喜欢男声",
                        "source": "rule",
                    }
                ],
            )
            store.save_session_memories(
                session_id="session-b",
                agent_profile_id="phone-assistant",
                memories=[
                    {
                        "session_id": "session-b",
                        "agent_profile_id": "phone-assistant",
                        "content": "我喜欢女声",
                        "source": "rule",
                    }
                ],
            )

            context = store.build_memory_context(
                agent_profile_id="phone-assistant",
                session_ids=["session-b", "session-a"],
            )

            self.assertEqual(
                [memory["content"] for memory in context["memories"]],
                ["我喜欢简短回答", "我喜欢女声", "我不喜欢男声"],
            )
            self.assertEqual(context["session_ids"], ["session-b", "session-a"])

    def test_build_memory_context_deduplicates_global_and_session_memories(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = LongTermMemoryStore(base_dir=Path(temp_dir))
            store.extract_compare_and_persist(
                session_id="session-a",
                agent_profile_id="phone-assistant",
                transcript=[{"role": "user", "text": "记住我喜欢女声"}],
            )

            context = store.build_memory_context(
                agent_profile_id="phone-assistant",
                session_ids=["session-a"],
            )

            self.assertEqual([memory["content"] for memory in context["memories"]], ["我喜欢女声"])

    def test_later_session_can_use_explicit_user_preference_memory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = LongTermMemoryStore(base_dir=Path(temp_dir))
            store.extract_compare_and_persist(
                session_id="preference-session",
                agent_profile_id="phone-assistant",
                transcript=[{"role": "user", "text": "记住我喜欢女生"}],
            )

            context = store.build_memory_context(
                agent_profile_id="phone-assistant",
                session_ids=["preference-session"],
            )

            self.assertEqual([memory["content"] for memory in context["memories"]], ["我喜欢女生"])
            self.assertEqual(context["system_role_text"], "长期记忆：\n- 我喜欢女生")

    def test_noop_model_extractor_records_not_configured_status(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = LongTermMemoryStore(base_dir=Path(temp_dir))

            extraction = store.extract_compare_and_persist(
                session_id="session-1",
                agent_profile_id="phone-assistant",
                transcript=[{"role": "user", "text": "记住我喜欢女声"}],
            )

            self.assertEqual(extraction["model"]["status"], "not_configured")
            self.assertEqual(extraction["accepted_source"], "rule")

    def test_store_runs_rule_and_model_extractors_concurrently(self) -> None:
        rule_started = threading.Event()
        model_started = threading.Event()
        with tempfile.TemporaryDirectory() as temp_dir:
            store = LongTermMemoryStore(
                base_dir=Path(temp_dir),
                rule_extractor=_CoordinatedExtractor(
                    source="rule",
                    own_started=rule_started,
                    other_started=model_started,
                    memories=[{"type": "explicit", "content": "我喜欢女声", "confidence": 1.0}],
                ),
                model_extractor=_CoordinatedExtractor(
                    source="model",
                    own_started=model_started,
                    other_started=rule_started,
                    memories=[{"type": "preference", "content": "用户偏好女声音色", "confidence": 0.8}],
                ),
            )

            extraction = store.extract_compare_and_persist(
                session_id="session-1",
                agent_profile_id="phone-assistant",
                transcript=[{"role": "user", "text": "记住我喜欢女声"}],
            )

            self.assertEqual(extraction["rule"]["memories"][0]["content"], "我喜欢女声")
            self.assertEqual(extraction["model"]["memories"][0]["content"], "用户偏好女声音色")


class _FakeModelExtractor:
    def __init__(self, memories: list[dict]) -> None:
        self.memories = memories

    def extract(self, session_id: str, agent_profile_id: str, transcript: list[dict]) -> list[dict]:
        return [
            {
                **memory,
                "session_id": session_id,
                "agent_profile_id": agent_profile_id,
                "source": "model",
            }
            for memory in self.memories
        ]


class _CoordinatedExtractor:
    def __init__(
        self,
        source: str,
        own_started: threading.Event,
        other_started: threading.Event,
        memories: list[dict],
    ) -> None:
        self.source = source
        self.own_started = own_started
        self.other_started = other_started
        self.memories = memories

    def extract(self, session_id: str, agent_profile_id: str, transcript: list[dict]) -> list[dict]:
        self.own_started.set()
        if not self.other_started.wait(0.2):
            raise AssertionError("paired extractor did not start concurrently")
        return [
            {
                **memory,
                "session_id": session_id,
                "agent_profile_id": agent_profile_id,
                "source": self.source,
            }
            for memory in self.memories
        ]


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


if __name__ == "__main__":
    unittest.main()

import json
import tempfile
import unittest
import wave
from pathlib import Path

from .conversation_store import ConversationStore


class ConversationStoreTest(unittest.TestCase):
    def test_persists_session_text_audio_routes_and_memory_extraction(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = ConversationStore(
                base_dir=Path(temp_dir),
                session_id="session-1",
                agent_profile_id="phone-assistant",
                config={"systemRole": "base role"},
                memory_context={"memories": [{"content": "用户喜欢女声"}]},
            )

            store.write_input_audio(b"\x01\x00\x02\x00")
            store.write_output_audio(b"\x03\x00\x04\x00")
            store.record_transcript(
                {
                    "session_id": "session-1",
                    "turn_id": "user-output-1",
                    "role": "user",
                    "text": "记住我喜欢女声",
                    "at": "10:00:00",
                }
            )
            store.record_route_decision(
                {
                    "type": "route_decision",
                    "turn_id": "user-output-1",
                    "mode": "chat",
                    "intent": "general",
                }
            )
            store.finalize(
                memory_extraction={
                    "accepted_source": "rule",
                    "rule": {"memories": [{"content": "我喜欢女声"}]},
                    "model": {"status": "not_configured", "memories": []},
                    "diff": [{"field": "memories", "rule": 1, "model": 0}],
                }
            )

            session_dir = Path(temp_dir) / "session-1"
            session = json.loads((session_dir / "session.json").read_text(encoding="utf-8"))
            transcript = _read_jsonl(session_dir / "transcript.jsonl")
            routes = _read_jsonl(session_dir / "route_decisions.jsonl")
            memory_extraction = json.loads((session_dir / "memory_extraction.json").read_text(encoding="utf-8"))

            self.assertEqual(session["session_id"], "session-1")
            self.assertEqual(session["agent_profile_id"], "phone-assistant")
            self.assertEqual(session["memory_context"]["memories"][0]["content"], "用户喜欢女声")
            self.assertTrue(session["ended_at"])
            self.assertEqual(transcript[0]["text"], "记住我喜欢女声")
            self.assertEqual(routes[0]["intent"], "general")
            self.assertEqual(memory_extraction["accepted_source"], "rule")
            self.assertEqual(_read_wav(session_dir / "input.wav"), (16000, 2))
            self.assertEqual(_read_wav(session_dir / "output.wav"), (24000, 2))


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _read_wav(path: Path) -> tuple[int, int]:
    with wave.open(str(path), "rb") as wav_file:
        return wav_file.getframerate(), wav_file.getnframes()


if __name__ == "__main__":
    unittest.main()

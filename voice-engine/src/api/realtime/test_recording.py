import tempfile
import unittest
import wave
from pathlib import Path

from .recording import LocalSessionRecorder


class LocalSessionRecorderTest(unittest.TestCase):
    def test_disabled_recorder_does_not_write_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            recorder = LocalSessionRecorder(False, Path(temp_dir), "session-1")
            recorder.write_input(b"\x01\x00")
            recorder.write_output(b"\x02\x00")
            recorder.close()

            self.assertEqual(list(Path(temp_dir).iterdir()), [])

    def test_enabled_recorder_writes_input_and_output_wav_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            recorder = LocalSessionRecorder(True, Path(temp_dir), "session-1")
            recorder.write_input(b"\x01\x00\x02\x00")
            recorder.write_output(b"\x03\x00\x04\x00")
            recorder.close()

            session_dir = Path(temp_dir) / "session-1"
            self.assertEqual(_read_wav(session_dir / "input.wav"), (16000, 2))
            self.assertEqual(_read_wav(session_dir / "output.wav"), (24000, 2))


def _read_wav(path: Path) -> tuple[int, int]:
    with wave.open(str(path), "rb") as wav_file:
        return wav_file.getframerate(), wav_file.getnframes()


if __name__ == "__main__":
    unittest.main()

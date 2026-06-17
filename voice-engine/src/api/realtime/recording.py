from __future__ import annotations

import wave
from pathlib import Path


class LocalSessionRecorder:
    def __init__(self, enabled: bool, base_dir: Path, session_id: str) -> None:
        self.enabled = enabled
        self.base_dir = base_dir
        self.session_id = session_id
        self.input_wav: wave.Wave_write | None = None
        self.output_wav: wave.Wave_write | None = None

    def write_input(self, pcm: bytes) -> None:
        if not self.enabled or not pcm:
            return
        self.input_wav = self.input_wav or self._open_wav("input.wav", 16000)
        self.input_wav.writeframes(pcm)

    def write_output(self, pcm: bytes) -> None:
        if not self.enabled or not pcm:
            return
        self.output_wav = self.output_wav or self._open_wav("output.wav", 24000)
        self.output_wav.writeframes(pcm)

    def close(self) -> None:
        for wav_file in (self.input_wav, self.output_wav):
            if wav_file:
                wav_file.close()
        self.input_wav = None
        self.output_wav = None

    def _open_wav(self, filename: str, sample_rate: int) -> wave.Wave_write:
        session_dir = self.base_dir / self.session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        wav_file = wave.open(str(session_dir / filename), "wb")
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        return wav_file

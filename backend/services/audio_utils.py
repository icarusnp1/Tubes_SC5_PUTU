from __future__ import annotations

import shutil
import uuid
import wave
import math
import struct
from pathlib import Path
from fastapi import UploadFile

from config import UPLOAD_DIR, OUTPUT_DIR


def safe_suffix(filename: str | None) -> str:
    if not filename:
        return ".wav"
    suffix = Path(filename).suffix.lower()
    return suffix if suffix in {".wav", ".mp3", ".m4a", ".webm", ".ogg", ".flac"} else ".wav"


async def save_upload_file(file: UploadFile) -> Path:
    suffix = safe_suffix(file.filename)
    target = UPLOAD_DIR / f"audio_{uuid.uuid4().hex}{suffix}"
    with target.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return target


def make_output_filename(prefix: str = "audio", suffix: str = ".wav") -> str:
    return f"{prefix}_{uuid.uuid4().hex}{suffix}"


def generate_tone_wav(text: str = "", duration_seconds: float = 1.2) -> str:
    """Fallback terakhir jika engine TTS tidak tersedia. Menghasilkan file WAV sederhana agar endpoint tetap mengembalikan audio."""
    filename = make_output_filename("tts_fallback", ".wav")
    output_path = OUTPUT_DIR / filename
    sample_rate = 16000
    freq = 440.0
    amplitude = 8000
    frames = int(duration_seconds * sample_rate)

    with wave.open(str(output_path), "w") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        for i in range(frames):
            value = int(amplitude * math.sin(2 * math.pi * freq * i / sample_rate))
            wav_file.writeframes(struct.pack("<h", value))

    return filename

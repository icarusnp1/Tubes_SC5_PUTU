from __future__ import annotations

import os
import time
import uuid
import wave
import math
import struct
from pathlib import Path

import pyttsx3
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[1]
OUTPUT_DIR = BASE_DIR / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TTS_MODE = os.getenv("TTS_MODE", "pyttsx3")
TTS_RATE = int(os.getenv("TTS_RATE", "150"))
TTS_VOLUME = float(os.getenv("TTS_VOLUME", "1.0"))


def _make_output_filename() -> str:
    return f"tts_{uuid.uuid4().hex}.wav"


def _create_fallback_tone(filename: str) -> None:
    """
    Fallback terakhir kalau pyttsx3 gagal membuat audio.
    Ini hanya membuat audio nada sederhana agar endpoint tetap menghasilkan file.
    """
    output_path = OUTPUT_DIR / filename

    sample_rate = 16000
    duration_seconds = 1.0
    frequency = 440.0
    amplitude = 16000

    total_samples = int(sample_rate * duration_seconds)

    with wave.open(str(output_path), "w") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)

        for i in range(total_samples):
            value = int(amplitude * math.sin(2 * math.pi * frequency * i / sample_rate))
            wav_file.writeframes(struct.pack("<h", value))


def synthesize_with_pyttsx3(text: str) -> dict:
    filename = _make_output_filename()
    output_path = OUTPUT_DIR / filename

    engine = pyttsx3.init()
    engine.setProperty("rate", TTS_RATE)
    engine.setProperty("volume", TTS_VOLUME)

    engine.save_to_file(text, str(output_path))
    engine.runAndWait()
    engine.stop()

    # Beri waktu sebentar agar file selesai ditulis oleh engine Windows/SAPI.
    time.sleep(0.5)

    if not output_path.exists() or output_path.stat().st_size == 0:
        raise RuntimeError("pyttsx3 gagal membuat file audio.")

    return {
        "filename": filename,
        "mode": "pyttsx3",
        "error": None,
    }


def synthesize_speech(text: str) -> dict:
    """
    Fungsi utama TTS yang dipanggil oleh main.py.
    Input  : teks ringkasan
    Output : dict berisi nama file audio
    """
    text = (text or "").strip()

    if not text:
        raise ValueError("Teks untuk TTS tidak boleh kosong.")

    try:
        if TTS_MODE == "pyttsx3":
            return synthesize_with_pyttsx3(text)

        # Untuk pengembangan berikutnya:
        # mode Coqui/VITS bisa ditambahkan di sini.
        return synthesize_with_pyttsx3(text)

    except Exception as exc:
        # Fallback terakhir agar aplikasi tetap menghasilkan audio.
        filename = _make_output_filename()
        _create_fallback_tone(filename)

        return {
            "filename": filename,
            "mode": "fallback-tone",
            "error": str(exc),
        }


def get_tts_status() -> dict:
    return {
        "enabled": True,
        "mode": TTS_MODE,
        "rate": TTS_RATE,
        "volume": TTS_VOLUME,
        "output_dir": str(OUTPUT_DIR),
    }
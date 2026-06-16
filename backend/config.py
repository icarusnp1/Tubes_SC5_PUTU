from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

APP_NAME = "Aplikasi Catatan Kuliah Otomatis"
API_PREFIX = "/api"

UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"
MODELS_DIR = BASE_DIR / "models"
STT_MODEL_DIR = MODELS_DIR / "stt_model"
TTS_MODEL_DIR = MODELS_DIR / "tts_model"

for directory in [UPLOAD_DIR, OUTPUT_DIR, STT_MODEL_DIR, TTS_MODEL_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()

# STT
STT_SAMPLE_RATE = int(os.getenv("STT_SAMPLE_RATE", "16000"))
STT_FALLBACK_TEXT = os.getenv(
    "STT_FALLBACK_TEXT",
    "materi kuliah hari ini membahas pengenalan ucapan dan teks ke ucapan",
)

# TTS
# auto = coba Coqui jika tersedia, jika tidak pakai pyttsx3.
# pyttsx3 = paksa library TTS lokal.
# coqui = paksa Coqui/VITS model lokal.
TTS_ENGINE = os.getenv("TTS_ENGINE", "pyttsx3").strip().lower()
TTS_RATE = int(os.getenv("TTS_RATE", "150"))
TTS_VOLUME = float(os.getenv("TTS_VOLUME", "1.0"))

# CORS
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")

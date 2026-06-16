from __future__ import annotations

import os
import re
from pathlib import Path

import librosa
import torch
from dotenv import load_dotenv
from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor

load_dotenv()

HF_STT_MODEL = os.getenv(
    "HF_STT_MODEL",
    "indonesian-nlp/wav2vec2-large-xlsr-indonesian",
)
STT_ENABLED = os.getenv("STT_ENABLED", "true").lower() not in {"0", "false", "no", "off"}
SAMPLE_RATE = 16000
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

_processor: Wav2Vec2Processor | None = None
_model: Wav2Vec2ForCTC | None = None


def clean_text(text: str) -> str:
    """
    Membersihkan hasil transkripsi agar lebih rapi.
    """
    text = (text or "").lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def load_stt_model():
    """
    Load model Wav2Vec2 Bahasa Indonesia dari Hugging Face.
    Pada pemanggilan pertama, model akan diunduh otomatis jika belum ada di cache lokal.
    """
    global _processor, _model

    if _processor is None or _model is None:
        print(f"[STT] Loading Hugging Face model: {HF_STT_MODEL}")
        print(f"[STT] Device: {DEVICE}")

        _processor = Wav2Vec2Processor.from_pretrained(HF_STT_MODEL)
        _model = Wav2Vec2ForCTC.from_pretrained(HF_STT_MODEL)
        _model.to(DEVICE)
        _model.eval()

    return _processor, _model


def transcribe_audio_file(audio_path: str | Path) -> str:
    """
    Mengubah file audio menjadi teks menggunakan Wav2Vec2.
    Audio otomatis dikonversi ke 16 kHz mono menggunakan librosa.
    """
    processor, model = load_stt_model()

    speech_array, _ = librosa.load(
        str(audio_path),
        sr=SAMPLE_RATE,
        mono=True,
    )

    if speech_array.size == 0:
        raise ValueError("Audio kosong atau tidak dapat dibaca.")

    inputs = processor(
        speech_array,
        sampling_rate=SAMPLE_RATE,
        return_tensors="pt",
        padding=True,
    )

    input_values = inputs.input_values.to(DEVICE)

    with torch.no_grad():
        logits = model(input_values).logits

    predicted_ids = torch.argmax(logits, dim=-1)
    transcription = processor.batch_decode(predicted_ids)[0]

    return clean_text(transcription)


def transcribe_audio(audio_path: str | Path, fallback_text: str | None = None) -> dict:
    """
    Fungsi yang dipakai oleh main.py.
    Return dibuat berbentuk dict agar cocok dengan endpoint /api/process-all.
    """
    fallback_text = clean_text(fallback_text or "")

    if not STT_ENABLED:
        return {
            "text": fallback_text,
            "mode": "fallback",
            "error": "STT dinonaktifkan melalui STT_ENABLED=false.",
        }

    try:
        text = transcribe_audio_file(audio_path)
        if not text and fallback_text:
            return {
                "text": fallback_text,
                "mode": "fallback",
                "error": "Model STT menghasilkan teks kosong.",
            }

        return {
            "text": text,
            "mode": "huggingface_wav2vec2",
            "error": None,
        }
    except Exception as exc:
        if fallback_text:
            return {
                "text": fallback_text,
                "mode": "fallback",
                "error": str(exc),
            }

        raise


def get_stt_status() -> dict:
    """
    Status modul STT untuk endpoint /api/health.
    """
    return {
        "enabled": STT_ENABLED,
        "mode": "huggingface_wav2vec2",
        "model": HF_STT_MODEL,
        "sample_rate": SAMPLE_RATE,
        "device": DEVICE,
        "loaded": _processor is not None and _model is not None,
    }

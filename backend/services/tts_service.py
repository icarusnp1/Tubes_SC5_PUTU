from __future__ import annotations

import os
import time
import uuid
import wave
import math
import struct
from pathlib import Path

import pyttsx3
import torch
import soundfile as sf
import re
import numpy as np
from transformers import SpeechT5Processor, SpeechT5ForTextToSpeech, SpeechT5HifiGan
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[1]
OUTPUT_DIR = BASE_DIR / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TTS_MODE = os.getenv("TTS_ENGINE", "pyttsx3")  # Menggunakan TTS_ENGINE dari .env
HF_TTS_MODEL = os.getenv("HF_TTS_MODEL", "./models/tts_model")
TTS_RATE = int(os.getenv("TTS_RATE", "150"))
TTS_VOLUME = float(os.getenv("TTS_VOLUME", "1.0"))

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

_tts_processor = None
_tts_model = None
_tts_vocoder = None
_speaker_embeddings = None

def load_speecht5():
    global _tts_processor, _tts_model, _tts_vocoder, _speaker_embeddings
    
    if _tts_processor is None:
        print(f"[TTS] Loading SpeechT5 from {HF_TTS_MODEL} on {DEVICE}")
        _tts_processor = SpeechT5Processor.from_pretrained(HF_TTS_MODEL)
        _tts_model = SpeechT5ForTextToSpeech.from_pretrained(HF_TTS_MODEL).to(DEVICE)
        
        print("[TTS] Loading Vocoder microsoft/speecht5_hifigan")
        _tts_vocoder = SpeechT5HifiGan.from_pretrained("microsoft/speecht5_hifigan").to(DEVICE)
        
        # Load or create speaker embedding
        embed_path = Path(HF_TTS_MODEL) / "speaker_embeddings.pt"
        if embed_path.exists():
            _speaker_embeddings = torch.load(embed_path).to(DEVICE)
        else:
            print("[TTS] No speaker_embeddings.pt found. Downloading default embedding...")
            try:
                from datasets import load_dataset
                # Unduh embedding sampel dari huggingface
                embeddings_dataset = load_dataset("Matthijs/cmu-arctic-xvectors", split="validation")
                _speaker_embeddings = torch.tensor(embeddings_dataset[7306]["xvector"]).unsqueeze(0)
                # Simpan agar tidak perlu unduh lagi di run berikutnya
                torch.save(_speaker_embeddings, embed_path)
                _speaker_embeddings = _speaker_embeddings.to(DEVICE)
            except Exception as e:
                print(f"[TTS] Gagal mengunduh embedding ({e}). Menggunakan dummy embedding.")
                torch.manual_seed(42)
                _speaker_embeddings = torch.randn(1, 512).to(DEVICE)
            
    return _tts_processor, _tts_model, _tts_vocoder, _speaker_embeddings


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


def synthesize_with_speecht5(text: str) -> dict:
    processor, model, vocoder, speaker_embeddings = load_speecht5()
    
    # 1. Bersihkan teks dari simbol markdown Gemini (*, #, _, dll)
    text = re.sub(r'[*_#`]', '', text)
    text = re.sub(r'\n+', ' ', text)
    text = text.strip()
    
    # 2. Pecah teks menjadi kalimat-kalimat yang lebih pendek
    # SpeechT5 memiliki batas maksimal token input (sekitar 600 karakter).
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    final_chunks = []
    current_chunk = ""
    for sentence in sentences:
        if len(current_chunk) + len(sentence) < 400:
            current_chunk += sentence + " "
        else:
            if current_chunk.strip():
                final_chunks.append(current_chunk.strip())
            current_chunk = sentence + " "
    if current_chunk.strip():
        final_chunks.append(current_chunk.strip())
        
    if not final_chunks:
        final_chunks = ["teks tidak terbaca"]

    all_speech = []
    
    # 3. Generate audio untuk setiap potongan teks lalu gabungkan
    with torch.no_grad():
        for chunk in final_chunks:
            inputs = processor(text=chunk, return_tensors="pt").to(DEVICE)
            try:
                speech = model.generate_speech(inputs["input_ids"], speaker_embeddings, vocoder=vocoder)
                all_speech.append(speech.cpu().numpy())
                # Tambahkan sedikit jeda hening antar kalimat (misal 0.2 detik = 3200 sample di 16kHz)
                all_speech.append(np.zeros(3200, dtype=np.float32))
            except Exception as e:
                print(f"[TTS] Peringatan: Gagal memproses chunk '{chunk[:30]}...': {e}")
                continue

    if not all_speech:
        raise RuntimeError("SpeechT5 gagal membuat audio dari semua chunk teks.")

    speech_np = np.concatenate(all_speech)
    
    filename = _make_output_filename()
    output_path = OUTPUT_DIR / filename
    
    # Simpan audio sebagai file WAV dengan sampling rate 16 kHz
    sf.write(str(output_path), speech_np, samplerate=16000)
    
    if not output_path.exists() or output_path.stat().st_size == 0:
        raise RuntimeError("SpeechT5 gagal menulis file audio.")
        
    return {
        "filename": filename,
        "mode": "speecht5",
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
        elif TTS_MODE == "speecht5":
            return synthesize_with_speecht5(text)

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
        "engine": TTS_MODE,
        "mode": TTS_MODE,
        "rate": TTS_RATE,
        "volume": TTS_VOLUME,
        "output_dir": str(OUTPUT_DIR),
    }
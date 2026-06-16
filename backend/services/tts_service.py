from __future__ import annotations

from pathlib import Path
import re

from config import OUTPUT_DIR, TTS_ENGINE, TTS_MODEL_DIR, TTS_RATE, TTS_VOLUME
from services.audio_utils import make_output_filename, generate_tone_wav

_coqui_tts = None
_last_error = None


def normalize_for_tts(text: str) -> str:
    text = (text or "").strip()
    text = re.sub(r"\s+", " ", text)
    return text


def is_coqui_model_available() -> bool:
    return (TTS_MODEL_DIR / "config.json").exists() and (
        (TTS_MODEL_DIR / "best_model.pth").exists()
        or (TTS_MODEL_DIR / "model.pth").exists()
        or any(TTS_MODEL_DIR.glob("checkpoint*.pth"))
    )


def find_coqui_model_path() -> Path | None:
    for name in ["best_model.pth", "model.pth"]:
        path = TTS_MODEL_DIR / name
        if path.exists():
            return path
    checkpoints = sorted(TTS_MODEL_DIR.glob("checkpoint*.pth"))
    return checkpoints[-1] if checkpoints else None


def get_tts_status() -> dict:
    return {
        "engine": TTS_ENGINE,
        "coqui_model_available": is_coqui_model_available(),
        "model_dir": str(TTS_MODEL_DIR),
        "last_error": _last_error,
    }


def load_coqui_tts():
    global _coqui_tts, _last_error
    if _coqui_tts is not None:
        return _coqui_tts

    model_path = find_coqui_model_path()
    config_path = TTS_MODEL_DIR / "config.json"
    if not model_path or not config_path.exists():
        raise FileNotFoundError("Model Coqui/VITS belum tersedia di backend/models/tts_model.")

    try:
        from TTS.api import TTS
        _coqui_tts = TTS(
            model_path=str(model_path),
            config_path=str(config_path),
            progress_bar=False,
            gpu=False,
        )
        _last_error = None
        return _coqui_tts
    except Exception as exc:
        _last_error = str(exc)
        raise


def synthesize_with_coqui(text: str) -> str:
    tts = load_coqui_tts()
    filename = make_output_filename("tts_coqui", ".wav")
    output_path = OUTPUT_DIR / filename
    tts.tts_to_file(text=text, file_path=str(output_path))
    return filename


def synthesize_with_pyttsx3(text: str) -> str:
    global _last_error
    try:
        import pyttsx3

        filename = make_output_filename("tts", ".wav")
        output_path = OUTPUT_DIR / filename

        engine = pyttsx3.init()
        engine.setProperty("rate", TTS_RATE)
        engine.setProperty("volume", TTS_VOLUME)
        engine.save_to_file(text, str(output_path))
        engine.runAndWait()

        if not output_path.exists() or output_path.stat().st_size == 0:
            raise RuntimeError("File audio pyttsx3 tidak berhasil dibuat.")

        _last_error = None
        return filename
    except Exception as exc:
        _last_error = str(exc)
        raise


def synthesize_speech(text: str) -> dict:
    global _last_error
    clean_text = normalize_for_tts(text)
    if not clean_text:
        raise ValueError("Teks untuk TTS tidak boleh kosong.")

    if TTS_ENGINE in {"coqui", "auto"} and is_coqui_model_available():
        try:
            filename = synthesize_with_coqui(clean_text)
            return {"filename": filename, "mode": "coqui_vits", "error": None}
        except Exception as exc:
            if TTS_ENGINE == "coqui":
                raise
            _last_error = str(exc)

    try:
        filename = synthesize_with_pyttsx3(clean_text)
        return {"filename": filename, "mode": "pyttsx3", "error": None}
    except Exception as exc:
        # Fallback terakhir hanya agar endpoint tetap mengembalikan file audio.
        filename = generate_tone_wav(clean_text)
        return {"filename": filename, "mode": "tone_fallback", "error": str(exc)}

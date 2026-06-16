from __future__ import annotations

import re
from pathlib import Path

from config import STT_MODEL_DIR, STT_SAMPLE_RATE, STT_FALLBACK_TEXT

_processor = None
_model = None
_device = None
_last_error = None


def clean_transcript(text: str) -> str:
    text = (text or "").lower().strip()
    text = re.sub(r"\s+", " ", text)
    return text


def is_stt_model_available() -> bool:
    required_any_weight = (STT_MODEL_DIR / "model.safetensors").exists() or (STT_MODEL_DIR / "pytorch_model.bin").exists()
    required_files = [
        STT_MODEL_DIR / "config.json",
        STT_MODEL_DIR / "vocab.json",
        STT_MODEL_DIR / "tokenizer_config.json",
    ]
    return required_any_weight and all(path.exists() for path in required_files)


def get_stt_status() -> dict:
    return {
        "available": is_stt_model_available(),
        "model_dir": str(STT_MODEL_DIR),
        "last_error": _last_error,
    }


def load_stt_model():
    """Load Wav2Vec2 model lokal hasil training.

    Folder yang diharapkan:
    backend/models/stt_model/config.json
    backend/models/stt_model/model.safetensors atau pytorch_model.bin
    backend/models/stt_model/vocab.json
    backend/models/stt_model/tokenizer_config.json
    """
    global _processor, _model, _device, _last_error

    if _processor is not None and _model is not None:
        return _processor, _model, _device

    if not is_stt_model_available():
        raise FileNotFoundError(
            "Model STT belum tersedia. Masukkan file hasil training Wav2Vec2 ke backend/models/stt_model."
        )

    try:
        import torch
        from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor

        _device = "cuda" if torch.cuda.is_available() else "cpu"
        _processor = Wav2Vec2Processor.from_pretrained(str(STT_MODEL_DIR))
        _model = Wav2Vec2ForCTC.from_pretrained(str(STT_MODEL_DIR))
        _model.to(_device)
        _model.eval()
        _last_error = None
        return _processor, _model, _device
    except Exception as exc:
        _last_error = str(exc)
        raise


def transcribe_with_wav2vec2(audio_path: Path) -> str:
    global _last_error
    processor, model, device = load_stt_model()

    try:
        import torch
        import librosa

        speech, _ = librosa.load(str(audio_path), sr=STT_SAMPLE_RATE, mono=True)
        inputs = processor(
            speech,
            sampling_rate=STT_SAMPLE_RATE,
            return_tensors="pt",
            padding=True,
        )

        with torch.no_grad():
            logits = model(inputs.input_values.to(device)).logits

        predicted_ids = torch.argmax(logits, dim=-1)
        transcription = processor.batch_decode(predicted_ids)[0]
        _last_error = None
        return clean_transcript(transcription)
    except Exception as exc:
        _last_error = str(exc)
        raise


def transcribe_audio(audio_path: Path, fallback_text: str | None = None) -> dict:
    """Return dict agar frontend tahu mode yang digunakan.

    Jika model Wav2Vec2 tersedia, sistem memakai model asli.
    Jika belum tersedia/error, sistem mengembalikan fallback text agar alur aplikasi tetap bisa diuji.
    """
    if is_stt_model_available():
        try:
            text = transcribe_with_wav2vec2(audio_path)
            if text:
                return {"text": text, "mode": "wav2vec2", "model_available": True, "error": None}
        except Exception as exc:
            return {
                "text": clean_transcript(fallback_text or STT_FALLBACK_TEXT),
                "mode": "fallback_after_stt_error",
                "model_available": True,
                "error": str(exc),
            }

    return {
        "text": clean_transcript(fallback_text or STT_FALLBACK_TEXT),
        "mode": "fallback_no_stt_model",
        "model_available": False,
        "error": None,
    }

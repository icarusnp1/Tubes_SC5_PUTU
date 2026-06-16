from __future__ import annotations

import re
from config import GEMINI_API_KEY, GEMINI_MODEL

_last_error = None


def is_gemini_configured() -> bool:
    return bool(GEMINI_API_KEY)


def get_summarizer_status() -> dict:
    return {
        "gemini_configured": is_gemini_configured(),
        "model": GEMINI_MODEL,
        "last_error": _last_error,
    }


def local_summary(text: str) -> str:
    """Ringkasan lokal sederhana jika API key belum tersedia/error."""
    clean = re.sub(r"\s+", " ", (text or "").strip())
    if not clean:
        return "Teks transkripsi belum tersedia."

    sentences = re.split(r"(?<=[.!?])\s+|\n+", clean)
    sentences = [s.strip(" .") for s in sentences if s.strip()]

    if len(clean.split()) <= 40:
        return "Ringkasan:\n- " + clean

    selected = sentences[:4] if len(sentences) >= 2 else [clean[:280]]
    bullets = [f"- {s}" for s in selected]
    return "Ringkasan catatan kuliah:\n" + "\n".join(bullets)


def summarize_with_gemini(text: str) -> str:
    global _last_error
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY belum diisi di file .env")

    try:
        from google import genai

        client = genai.Client(api_key=GEMINI_API_KEY)
        prompt = f"""
Anda adalah asisten pencatat kuliah. Ringkas teks transkripsi berikut menjadi catatan kuliah Bahasa Indonesia yang rapi.
Format output:
1. Ringkasan singkat 3-5 kalimat.
2. Poin penting dalam bullet.
3. Kesimpulan materi.

Teks transkripsi:
{text}
""".strip()

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
        )
        result = getattr(response, "text", None) or ""
        if not result.strip():
            raise RuntimeError("Gemini tidak mengembalikan teks ringkasan.")
        _last_error = None
        return result.strip()
    except Exception as exc:
        _last_error = str(exc)
        raise


def summarize_text(text: str) -> dict:
    if not text or not text.strip():
        return {"summary": "Teks transkripsi belum tersedia.", "mode": "empty", "error": None}

    if is_gemini_configured():
        try:
            return {"summary": summarize_with_gemini(text), "mode": "gemini", "error": None}
        except Exception as exc:
            return {"summary": local_summary(text), "mode": "fallback_after_gemini_error", "error": str(exc)}

    return {"summary": local_summary(text), "mode": "fallback_no_api_key", "error": None}

from __future__ import annotations

import json
import re
from typing import Any

from config import GEMINI_API_KEY, GEMINI_MODEL

_last_error: str | None = None

VALID_SUMMARY_MODES = {
    "singkat": "Ringkasan singkat untuk memahami inti materi dengan cepat.",
    "detail": "Catatan detail dengan penjelasan lebih lengkap dan terstruktur.",
    "ujian": "Catatan persiapan ujian yang menekankan konsep penting dan pertanyaan latihan.",
}


def is_gemini_configured() -> bool:
    return bool(GEMINI_API_KEY)


def normalize_mode(summary_mode: str | None) -> str:
    mode = (summary_mode or "singkat").strip().lower()
    return mode if mode in VALID_SUMMARY_MODES else "singkat"


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def split_sentences(text: str) -> list[str]:
    clean = clean_text(text)
    if not clean:
        return []
    sentences = re.split(r"(?<=[.!?])\s+|\n+", clean)
    return [s.strip(" .") for s in sentences if s.strip()]


def simple_keywords(text: str, max_keywords: int = 10) -> list[str]:
    clean = clean_text(text).lower()
    words = re.findall(r"[a-zA-ZÀ-ÿ0-9]+", clean)
    stopwords = {
        "yang", "dan", "di", "ke", "dari", "dengan", "untuk", "pada", "dalam", "adalah",
        "ini", "itu", "atau", "sebagai", "akan", "dapat", "juga", "karena", "maka", "oleh",
        "hari", "materi", "kuliah", "kita", "saya", "dosen", "tentang", "secara", "menjadi",
        "hasil", "proses", "sistem", "aplikasi", "menggunakan", "digunakan", "membahas",
        "sebuah", "tersebut", "yaitu", "agar", "dalam", "adanya", "melalui", "kepada",
        "memiliki", "menjelaskan", "penggunaan", "secara", "utama",
    }
    freq: dict[str, int] = {}
    for word in words:
        if len(word) < 4 or word in stopwords:
            continue
        freq[word] = freq.get(word, 0) + 1
    return [word for word, _ in sorted(freq.items(), key=lambda item: (-item[1], item[0]))[:max_keywords]]


def _limit_items(items: list[str], limit: int) -> list[str]:
    cleaned = [clean_text(str(item)).strip(" -•") for item in items if clean_text(str(item))]
    return cleaned[:limit]


def make_structured_note(
    *,
    text: str,
    summary_mode: str = "singkat",
    note_title: str = "",
    course_name: str = "",
    summary: str | list[str] | None = None,
    important_points: list[str] | None = None,
    keywords: list[str] | None = None,
    questions: list[str] | None = None,
    conclusion: str | None = None,
    action_items: list[str] | None = None,
    suggested_title: str | None = None,
) -> dict[str, Any]:
    mode = normalize_mode(summary_mode)
    title = clean_text(note_title or suggested_title or "Catatan Kuliah Otomatis")
    course = clean_text(course_name or "-")
    clean = clean_text(text)
    sentences = split_sentences(clean) or ([clean] if clean else [])

    if isinstance(summary, list):
        summary_text = " ".join(_limit_items(summary, 5))
    else:
        summary_text = clean_text(summary or "")

    if not summary_text:
        count = 3 if mode == "singkat" else 5 if mode == "detail" else 4
        summary_text = " ".join(sentences[:count]) or "Teks transkripsi belum tersedia."

    points_limit = 8 if mode == "detail" else 6
    important_points = _limit_items(important_points or sentences, points_limit)
    if not important_points:
        important_points = ["Belum ada poin penting yang dapat diidentifikasi."]

    keywords = _limit_items(keywords or simple_keywords(clean), 10)
    if not keywords:
        keywords = ["belum terdeteksi"]

    questions = _limit_items(questions or [], 6)
    if not questions:
        questions = [
            "Apa konsep utama yang dibahas pada materi ini?",
            "Mengapa konsep tersebut penting untuk dipahami?",
            "Bagaimana penerapan materi ini dalam konteks pembelajaran?",
        ]

    action_items = _limit_items(action_items or [], 6)
    if not action_items:
        action_items = [
            "Baca ulang poin penting dari catatan.",
            "Dengarkan kembali audio ringkasan yang dihasilkan sistem.",
            "Jawab pertanyaan latihan untuk mengecek pemahaman.",
        ]

    conclusion = clean_text(conclusion or "")
    if not conclusion:
        conclusion = "Materi ini memuat konsep penting yang dapat dipelajari kembali melalui transkripsi, ringkasan, kata kunci, dan audio pembacaan ulang."

    return {
        "title": title,
        "course_name": course,
        "summary_mode": mode,
        "summary_mode_description": VALID_SUMMARY_MODES[mode],
        "summary": summary_text,
        "important_points": important_points,
        "keywords": keywords,
        "questions": questions,
        "action_items": action_items,
        "conclusion": conclusion,
    }


def note_to_markdown(note: dict[str, Any], transcription: str = "") -> str:
    def bullet(items: list[str]) -> str:
        return "\n".join(f"- {item}" for item in items)

    def numbered(items: list[str]) -> str:
        return "\n".join(f"{idx + 1}. {item}" for idx, item in enumerate(items))

    parts = [
        f"# {note.get('title') or 'Catatan Kuliah Otomatis'}",
        "",
        f"Mata Kuliah: {note.get('course_name') or '-'}",
        f"Mode Catatan: {note.get('summary_mode') or '-'}",
        "",
        "## 1. Ringkasan",
        str(note.get("summary") or "-"),
        "",
        "## 2. Poin Penting",
        bullet(list(note.get("important_points") or [])) or "- -",
        "",
        "## 3. Kata Kunci",
        bullet(list(note.get("keywords") or [])) or "- -",
        "",
        "## 4. Pertanyaan Latihan",
        numbered(list(note.get("questions") or [])) or "1. -",
        "",
        "## 5. Tindak Lanjut Belajar",
        bullet(list(note.get("action_items") or [])) or "- -",
        "",
        "## 6. Kesimpulan",
        str(note.get("conclusion") or "-"),
    ]
    if transcription:
        parts.extend(["", "## 7. Transkripsi", transcription])
    return "\n".join(parts).strip()


def _extract_json_object(raw: str) -> dict[str, Any]:
    cleaned = raw.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if match:
        parsed = json.loads(match.group(0))
        if isinstance(parsed, dict):
            return parsed
    raise ValueError("Gemini tidak mengembalikan JSON yang valid.")


def local_summary(text: str, summary_mode: str = "singkat", note_title: str = "", course_name: str = "") -> dict[str, Any]:
    note = make_structured_note(
        text=text,
        summary_mode=summary_mode,
        note_title=note_title,
        course_name=course_name,
    )
    return {
        "summary": note_to_markdown(note),
        "structured_note": note,
        "mode": "fallback_local",
        "summary_mode": note["summary_mode"],
        "error": None,
    }


def get_summarizer_status() -> dict:
    return {
        "gemini_configured": is_gemini_configured(),
        "model": GEMINI_MODEL,
        "available_modes": list(VALID_SUMMARY_MODES.keys()),
        "structured_output": True,
        "last_error": _last_error,
    }


def summarize_with_gemini(
    text: str,
    summary_mode: str = "singkat",
    note_title: str = "",
    course_name: str = "",
) -> dict[str, Any]:
    global _last_error
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY belum diisi di file .env")

    mode = normalize_mode(summary_mode)
    title = clean_text(note_title or "Catatan Kuliah Otomatis")
    course = clean_text(course_name or "Tidak diisi")

    mode_instruction = {
        "singkat": "Buat ringkasan padat, langsung ke inti, dan tidak terlalu panjang.",
        "detail": "Buat catatan lebih lengkap, jelaskan poin penting dengan kalimat yang mudah dipahami.",
        "ujian": "Fokus untuk belajar ujian: konsep utama, hal yang sering ditanyakan, dan pertanyaan latihan.",
    }[mode]

    try:
        from google import genai

        client = genai.Client(api_key=GEMINI_API_KEY)
        prompt = f"""
Anda adalah asisten pencatat kuliah Bahasa Indonesia.
Ubah transkripsi kuliah menjadi catatan belajar terstruktur.

Konteks catatan:
- Judul/topik: {title}
- Mata kuliah: {course}
- Mode ringkasan: {mode}
- Instruksi mode: {mode_instruction}

Kembalikan jawaban HANYA dalam JSON valid, tanpa markdown, tanpa code fence.
Skema JSON wajib:
{{
  "title": "string",
  "course_name": "string",
  "summary_mode": "singkat|detail|ujian",
  "summary": "ringkasan utama dalam 3-6 kalimat",
  "important_points": ["poin penting 1", "poin penting 2"],
  "keywords": ["kata kunci 1", "kata kunci 2"],
  "questions": ["pertanyaan latihan 1", "pertanyaan latihan 2"],
  "action_items": ["tindak lanjut belajar 1", "tindak lanjut belajar 2"],
  "conclusion": "kesimpulan singkat"
}}

Transkripsi kuliah:
{text}
""".strip()

        response = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
        raw = getattr(response, "text", None) or ""
        if not raw.strip():
            raise RuntimeError("Gemini tidak mengembalikan teks ringkasan.")

        parsed = _extract_json_object(raw)
        note = make_structured_note(
            text=text,
            summary_mode=parsed.get("summary_mode") or mode,
            note_title=parsed.get("title") or title,
            course_name=parsed.get("course_name") or course,
            summary=parsed.get("summary"),
            important_points=parsed.get("important_points") or [],
            keywords=parsed.get("keywords") or [],
            questions=parsed.get("questions") or [],
            action_items=parsed.get("action_items") or [],
            conclusion=parsed.get("conclusion"),
        )
        _last_error = None
        return {
            "summary": note_to_markdown(note),
            "structured_note": note,
            "mode": "gemini_structured",
            "summary_mode": note["summary_mode"],
            "error": None,
        }
    except Exception as exc:
        _last_error = str(exc)
        raise


def summarize_text(
    text: str,
    summary_mode: str = "singkat",
    note_title: str = "",
    course_name: str = "",
) -> dict[str, Any]:
    if not text or not text.strip():
        result = local_summary("", summary_mode=summary_mode, note_title=note_title, course_name=course_name)
        result["mode"] = "empty"
        return result

    if is_gemini_configured():
        try:
            return summarize_with_gemini(text, summary_mode=summary_mode, note_title=note_title, course_name=course_name)
        except Exception as exc:
            result = local_summary(text, summary_mode=summary_mode, note_title=note_title, course_name=course_name)
            result["mode"] = "fallback_after_gemini_error"
            result["error"] = str(exc)
            return result

    result = local_summary(text, summary_mode=summary_mode, note_title=note_title, course_name=course_name)
    result["mode"] = "fallback_no_api_key"
    return result

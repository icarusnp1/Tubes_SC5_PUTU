from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from config import APP_NAME, FRONTEND_ORIGIN, OUTPUT_DIR
from services.audio_utils import save_upload_file
from services.stt_service import transcribe_audio as run_stt, get_stt_status
from services.summarizer_service import summarize_text, get_summarizer_status
from services.tts_service import synthesize_speech, get_tts_status

from fastapi import UploadFile, File
from pathlib import Path
import shutil
import uuid

from services.stt_service import transcribe_audio_file

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


app = FastAPI(title=APP_NAME, version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN, "http://localhost:5173", "http://127.0.0.1:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/outputs", StaticFiles(directory=str(OUTPUT_DIR)), name="outputs")


class TextRequest(BaseModel):
    text: str


class ProcessAllResponse(BaseModel):
    transcription: str
    summary: str
    audio_url: str
    stt_mode: str
    summarize_mode: str
    tts_mode: str
    warnings: list[str] = []


@app.get("/")
def root():
    return {
        "message": APP_NAME,
        "docs": "http://localhost:8000/docs",
        "health": "http://localhost:8000/api/health",
    }


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "app": APP_NAME,
        "stt": get_stt_status(),
        "summarizer": get_summarizer_status(),
        "tts": get_tts_status(),
    }


@app.post("/api/transcribe")
async def transcribe_endpoint(
    file: UploadFile = File(...),
    fallback_text: str | None = Form(default=None),
):
    try:
        audio_path = await save_upload_file(file)
        result = run_stt(audio_path, fallback_text=fallback_text)
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/summarize")
def summarize(request: TextRequest):
    try:
        result = summarize_text(request.text)
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/tts")
def tts(request: TextRequest):
    try:
        result = synthesize_speech(request.text)
        audio_url = f"http://localhost:8000/outputs/{result['filename']}"
        return {
            "audio_url": audio_url,
            "filename": result["filename"],
            "mode": result["mode"],
            "error": result["error"],
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/process-all", response_model=ProcessAllResponse)
async def process_all(
    file: UploadFile = File(...),
    fallback_text: str | None = Form(default=None),
):
    warnings: list[str] = []
    try:
        audio_path = await save_upload_file(file)

        stt_result = run_stt(audio_path, fallback_text=fallback_text)
        if stt_result.get("error"):
            warnings.append(f"STT: {stt_result['error']}")

        summary_result = summarize_text(stt_result["text"])
        if summary_result.get("error"):
            warnings.append(f"Ringkasan: {summary_result['error']}")

        tts_result = synthesize_speech(summary_result["summary"])
        if tts_result.get("error"):
            warnings.append(f"TTS: {tts_result['error']}")

        audio_url = f"http://localhost:8000/outputs/{tts_result['filename']}"
        return ProcessAllResponse(
            transcription=stt_result["text"],
            summary=summary_result["summary"],
            audio_url=audio_url,
            stt_mode=stt_result["mode"],
            summarize_mode=summary_result["mode"],
            tts_mode=tts_result["mode"],
            warnings=warnings,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
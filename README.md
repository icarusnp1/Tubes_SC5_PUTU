# Perancangan dan Implementasi Aplikasi Catatan Kuliah Otomatis Berbasis Speech-to-Text dan Text-to-Speech

Project ini adalah full build sederhana berbasis **React + FastAPI** untuk aplikasi catatan kuliah otomatis sesuai rancangan PUTU.

Alur sistem:

```text
Input audio kuliah
↓
Speech-to-Text (STT)
↓
Transkripsi teks
↓
Ringkasan Gemini API
↓
Text-to-Speech (TTS)
↓
Output audio ringkasan
```

## 1. Struktur Project

```text
putu_react_fastapi_fullbuild/
├── backend/
│   ├── main.py
│   ├── config.py
│   ├── requirements.txt
│   ├── requirements-ai.txt
│   ├── .env.example
│   ├── services/
│   │   ├── audio_utils.py
│   │   ├── stt_service.py
│   │   ├── summarizer_service.py
│   │   └── tts_service.py
│   ├── models/
│   │   ├── stt_model/
│   │   └── tts_model/
│   ├── uploads/
│   └── outputs/
└── frontend/
    ├── package.json
    ├── index.html
    └── src/
        ├── App.jsx
        ├── api.js
        ├── main.jsx
        └── style.css
```

## 2. Yang Sudah Terimplementasi

- React frontend sederhana.
- FastAPI backend.
- Upload file audio.
- Endpoint STT `/api/transcribe`.
- Endpoint ringkasan `/api/summarize`.
- Endpoint TTS `/api/tts`.
- Endpoint full pipeline `/api/process-all`.
- Static audio output di `/outputs/...`.
- Gemini API siap dipakai jika `GEMINI_API_KEY` sudah diisi.
- TTS awal memakai `pyttsx3`.
- STT Wav2Vec2 sudah disiapkan, tinggal masukkan model hasil training ke folder `backend/models/stt_model`.

## 3. Yang Harus Diisi Manual

### A. API Key Gemini

Salin file:

```bash
cd backend
copy .env.example .env
```

Lalu isi:

```env
GEMINI_API_KEY=ISI_API_KEY_KAMU
GEMINI_MODEL=gemini-2.5-flash
```

Jika API key belum diisi, sistem tetap membuat ringkasan lokal sederhana.

### B. Model STT Wav2Vec2

Masukkan file hasil training STT ke:

```text
backend/models/stt_model/
```

Contoh isi folder:

```text
backend/models/stt_model/
├── config.json
├── model.safetensors
├── processor_config.json
├── tokenizer_config.json
├── vocab.json
└── added_tokens.json
```

Jika model belum dimasukkan, sistem memakai teks cadangan dari frontend agar alur aplikasi tetap bisa diuji.

### C. Model TTS VITS/Coqui Jika Ada

Secara default aplikasi memakai `pyttsx3`. Jika nanti ingin memakai VITS/Coqui hasil training, isi folder:

```text
backend/models/tts_model/
├── config.json
└── best_model.pth
```

Lalu ubah `.env`:

```env
TTS_ENGINE=auto
```

Install dependensi opsional:

```bash
pip install -r requirements-ai.txt
```

Catatan: package `TTS` bisa berat dan bergantung versi Python. Untuk demo cepat, `pyttsx3` sudah cukup sesuai implementasi awal library TTS lokal.

## 4. Cara Menjalankan Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn main:app --reload
```

Backend berjalan di:

```text
http://localhost:8000
```

Dokumentasi API:

```text
http://localhost:8000/docs
```

## 5. Cara Menjalankan Frontend

Buka terminal baru:

```bash
cd frontend
npm install
npm run dev
```

Frontend berjalan di:

```text
http://localhost:5173
```

## 6. Cara Testing Cepat

1. Jalankan backend.
2. Jalankan frontend.
3. Upload audio apa saja.
4. Isi teks cadangan jika model STT belum ada.
5. Klik **Proses Semua Otomatis**.
6. Aplikasi akan menghasilkan:
   - transkripsi,
   - ringkasan,
   - audio TTS.

## 7. Catatan Mode Sistem

Aplikasi menampilkan mode pemrosesan:

- `wav2vec2`: STT memakai model lokal.
- `fallback_no_stt_model`: model STT belum dimasukkan.
- `gemini`: ringkasan memakai Gemini API.
- `fallback_no_api_key`: ringkasan lokal karena API key belum diisi.
- `pyttsx3`: TTS memakai library lokal.
- `coqui_vits`: TTS memakai model VITS/Coqui lokal.

## 8. Saran untuk Laporan

Narasi implementasi aman:

> Sistem dikembangkan menggunakan React.js sebagai antarmuka pengguna dan FastAPI sebagai backend pemrosesan. Modul STT dirancang untuk mendukung model Wav2Vec2 hasil pelatihan, modul ringkasan menggunakan Gemini API, sedangkan modul TTS pada implementasi awal menggunakan library TTS lokal. Struktur backend dibuat modular sehingga model Neural TTS seperti VITS/Coqui dapat diintegrasikan pada pengembangan berikutnya.

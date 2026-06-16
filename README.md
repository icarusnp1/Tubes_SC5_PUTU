# Perancangan dan Implementasi Aplikasi Catatan Kuliah Otomatis Berbasis Speech-to-Text dan Text-to-Speech

Aplikasi ini merupakan implementasi sederhana berbasis **React.js** dan **FastAPI** untuk membuat catatan kuliah otomatis. Sistem menerima input audio, mengubah audio menjadi teks menggunakan **Speech-to-Text (STT)**, membuat ringkasan menggunakan **Gemini API**, lalu mengubah ringkasan menjadi audio menggunakan **Text-to-Speech (TTS)**.

## 1. Fitur Utama

- Upload file audio perkuliahan.
- Proses Speech-to-Text menggunakan model Wav2Vec2 Bahasa Indonesia dari Hugging Face.
- Menampilkan hasil transkripsi audio.
- Membuat ringkasan catatan kuliah menggunakan Gemini API.
- Menghasilkan audio ringkasan menggunakan TTS lokal `pyttsx3`.
- Memutar hasil audio melalui audio player di website.
- Menyediakan proses penuh dari audio sampai output audio.

## 2. Teknologi yang Digunakan

### Frontend

- React.js
- Vite
- JavaScript
- CSS

### Backend

- FastAPI
- Uvicorn
- Python
- Hugging Face Transformers
- Wav2Vec2
- Gemini API
- pyttsx3
- Librosa
- PyTorch

## 3. Struktur Project

```text
Tubes_SC5_PUTU/
├── backend/
│   ├── main.py
│   ├── config.py
│   ├── requirements.txt
│   ├── .env.example
│   ├── .env
│   ├── services/
│   │   ├── audio_utils.py
│   │   ├── stt_service.py
│   │   ├── summarizer_service.py
│   │   └── tts_service.py
│   ├── uploads/
│   ├── outputs/
│   └── models/
│       ├── stt_model/
│       └── tts_model/
│
└── frontend/
    ├── package.json
    ├── index.html
    └── src/
        ├── App.jsx
        ├── api.js
        └── style.css
```

## 4. Alur Sistem

```text
Input audio kuliah
↓
Upload audio dari website
↓
FastAPI menerima file audio
↓
STT Wav2Vec2 mengubah audio menjadi teks
↓
Teks transkripsi ditampilkan di website
↓
Gemini API membuat ringkasan
↓
Ringkasan dikirim ke modul TTS
↓
pyttsx3 menghasilkan file audio
↓
Website memutar audio ringkasan
```

## 5. Persiapan Backend

Masuk ke folder backend:

```bash
cd backend
```

Buat virtual environment:

```bash
python -m venv .venv
```

Aktifkan virtual environment di Windows:

```bash
.venv\Scripts\activate
```

Install dependency:

```bash
pip install -r requirements.txt
```

Jika ada library yang belum terinstall, jalankan:

```bash
pip install fastapi uvicorn python-multipart python-dotenv google-genai pyttsx3 torch transformers librosa soundfile safetensors numpy
```

Jika muncul error terkait `torchvision`, jalankan:

```bash
pip install torchvision
```

Atau untuk PyTorch CPU:

```bash
pip install --upgrade torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
```

## 6. Konfigurasi File `.env`

Copy file `.env.example` menjadi `.env`:

```bash
copy .env.example .env
```

Isi file `.env` seperti berikut:

```env
APP_NAME=Aplikasi Catatan Kuliah Otomatis
FRONTEND_ORIGIN=http://localhost:5173

GEMINI_API_KEY=ISI_API_KEY_GEMINI_KAMU
GEMINI_MODEL=gemini-1.5-flash

HF_STT_MODEL=indonesian-nlp/wav2vec2-large-xlsr-indonesian
STT_ENABLED=true

TTS_MODE=pyttsx3
TTS_RATE=150
TTS_VOLUME=1.0
```

Catatan:

- Jangan upload file `.env` ke GitHub.
- Jangan membagikan `GEMINI_API_KEY` ke orang lain.
- `HF_STT_MODEL` memakai model Wav2Vec2 Bahasa Indonesia dari Hugging Face.
- `TTS_MODE=pyttsx3` digunakan agar TTS lokal langsung dapat berjalan tanpa training model tambahan.

## 7. Login Hugging Face Opsional

Saat pertama kali menjalankan STT, backend akan mengunduh model dari Hugging Face. Ukuran model cukup besar, sekitar 1 GB lebih.

Jika muncul peringatan:

```text
Warning: You are sending unauthenticated requests to the HF Hub.
```

itu bukan error. Artinya model tetap bisa diunduh, tetapi lebih baik login agar download lebih stabil.

Gunakan command:

```bash
hf auth login
```

Masukkan token Hugging Face bertipe **Read**.

Cek status login:

```bash
hf auth whoami
```

## 8. Menjalankan Backend

Dari folder backend, jalankan:

```bash
uvicorn main:app --reload
```

Backend berjalan di:

```text
http://localhost:8000
```

Dokumentasi Swagger:

```text
http://localhost:8000/docs
```

## 9. Menjalankan Frontend

Buka terminal baru, masuk ke folder frontend:

```bash
cd frontend
```

Install dependency:

```bash
npm install
```

Jalankan frontend:

```bash
npm run dev
```

Website berjalan di:

```text
http://localhost:5173
```

## 10. Endpoint Backend

### Health Check

```text
GET /api/health
```

Digunakan untuk mengecek status backend, STT, Gemini, dan TTS.

### Transkripsi Audio

```text
POST /api/transcribe
```

Input:

- File audio.
- Opsional: fallback text.

Output:

```json
{
  "text": "hasil transkripsi",
  "mode": "huggingface-wav2vec2",
  "error": null
}
```

### Ringkasan Teks

```text
POST /api/summarize
```

Input:

```json
{
  "text": "teks transkripsi kuliah"
}
```

Output:

```json
{
  "summary": "hasil ringkasan",
  "mode": "gemini",
  "error": null
}
```

### Text-to-Speech

```text
POST /api/tts
```

Input:

```json
{
  "text": "teks ringkasan"
}
```

Output:

```json
{
  "audio_url": "http://localhost:8000/outputs/tts_xxxxx.wav",
  "filename": "tts_xxxxx.wav",
  "mode": "pyttsx3",
  "error": null
}
```

### Proses Lengkap

```text
POST /api/process-all
```

Digunakan untuk menjalankan seluruh alur:

```text
Audio → STT → Ringkasan → TTS → Output audio
```

## 11. Cara Testing dari Website

1. Jalankan backend.
2. Jalankan frontend.
3. Buka `http://localhost:5173`.
4. Upload audio pendek Bahasa Indonesia.
5. Klik proses STT.
6. Pastikan hasil transkripsi muncul.
7. Klik buat ringkasan.
8. Pastikan hasil ringkasan muncul.
9. Klik generate audio.
10. Pastikan audio player muncul dan audio dapat diputar.

## 12. Rekomendasi Audio Testing

Gunakan audio pendek dengan ketentuan:

```text
Format: wav atau mp3
Durasi: 5–15 detik
Bahasa: Indonesia
Kualitas: suara jelas, minim noise
```

Contoh kalimat untuk direkam:

```text
Hari ini kita membahas aplikasi catatan kuliah otomatis berbasis speech to text dan text to speech.
```

Untuk pengujian awal, lebih disarankan merekam audio sendiri daripada memakai audio kuliah panjang. Audio panjang dapat membuat proses STT lebih berat.

## 13. Testing TTS

Untuk menguji TTS, tidak perlu upload audio. Gunakan teks ringkasan seperti:

```text
Materi hari ini membahas pengenalan ucapan, proses transkripsi suara, dan pembacaan ulang ringkasan menggunakan text to speech.
```

Klik tombol generate audio. Jika audio player muncul dan suara dapat diputar, maka modul TTS berhasil diuji.

## 14. Troubleshooting

### 1. Error: `transcribe_audio() got an unexpected keyword argument 'fallback_text'`

Penyebab:

- Fungsi endpoint dan fungsi service memiliki nama yang bentrok.
- `main.py` belum memakai alias `run_stt`.

Solusi:

Pastikan import di `main.py` seperti ini:

```python
from services.stt_service import transcribe_audio as run_stt, get_stt_status
```

Dan pemanggilan STT menggunakan:

```python
stt_result = run_stt(audio_path, fallback_text=fallback_text)
```

### 2. STT pertama kali lama

Penyebab:

- Model Hugging Face sedang diunduh pertama kali.
- Ukuran model besar.

Solusi:

- Tunggu sampai download selesai.
- Gunakan `hf auth login` agar lebih stabil.

### 3. Gemini tidak menghasilkan ringkasan

Penyebab:

- `GEMINI_API_KEY` belum diisi.
- API key salah.
- Backend belum direstart setelah mengubah `.env`.

Solusi:

- Isi `backend/.env`.
- Restart backend.

### 4. TTS tidak menghasilkan audio

Penyebab:

- `pyttsx3` belum terinstall.
- Engine TTS Windows bermasalah.

Solusi:

```bash
pip install pyttsx3
```

Cek folder:

```text
backend/outputs/
```

Pastikan file `.wav` berhasil dibuat.

### 5. Website tidak bisa konek backend

Penyebab:

- Backend belum berjalan.
- URL API di frontend salah.

Solusi:

Pastikan backend berjalan di:

```text
http://localhost:8000
```

Dan frontend berjalan di:

```text
http://localhost:5173
```

## 15. File dan Folder yang Tidak Perlu Diupload ke GitHub

Gunakan `.gitignore` untuk mengabaikan:

```gitignore
.venv/
__pycache__/
.env
uploads/*
outputs/*
models/*
node_modules/
dist/
```

Jika ingin folder `models`, `uploads`, dan `outputs` tetap ada di repository, buat file `.gitkeep` di masing-masing folder.

## 16. Catatan Pengembangan

Implementasi saat ini menggunakan:

- STT: Wav2Vec2 Bahasa Indonesia dari Hugging Face.
- Ringkasan: Gemini API.
- TTS: pyttsx3 sebagai library TTS lokal.

Struktur backend dibuat modular sehingga model STT lokal atau TTS Neural seperti VITS/Coqui dapat ditambahkan pada pengembangan berikutnya tanpa mengubah keseluruhan aplikasi.

## 17. Status Implementasi

| Modul | Status |
|---|---|
| Frontend React | Berjalan |
| Backend FastAPI | Berjalan |
| Upload audio | Berjalan |
| STT Wav2Vec2 Hugging Face | Berjalan setelah model berhasil diunduh |
| Ringkasan Gemini API | Membutuhkan API key |
| TTS pyttsx3 | Berjalan sebagai TTS lokal |
| Audio player | Berjalan |
| Full pipeline | Berjalan jika STT, Gemini, dan TTS aktif |

## 18. Alur Demo Singkat

1. Buka website.
2. Upload audio pendek.
3. Klik proses STT.
4. Lihat hasil transkripsi.
5. Klik buat ringkasan.
6. Lihat hasil ringkasan.
7. Klik generate audio.
8. Putar audio hasil TTS.


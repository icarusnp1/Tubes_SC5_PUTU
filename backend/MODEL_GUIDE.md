# Panduan Folder Model

## STT Wav2Vec2

Masukkan hasil `save_pretrained()` ke:

```text
backend/models/stt_model/
```

Minimal file:

```text
config.json
model.safetensors atau pytorch_model.bin
vocab.json
tokenizer_config.json
processor_config.json
```

## TTS VITS/Coqui

Opsional. Default aplikasi memakai `pyttsx3`.

Jika ingin pakai Coqui/VITS, masukkan ke:

```text
backend/models/tts_model/
```

Minimal file:

```text
config.json
best_model.pth
```

Lalu ubah `backend/.env`:

```env
TTS_ENGINE=auto
```

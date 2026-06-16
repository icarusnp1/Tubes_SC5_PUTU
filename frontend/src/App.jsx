import { useEffect, useMemo, useRef, useState } from 'react'
import { API_BASE, generateTTS, getHealth, processAll, summarizeText, transcribeAudio } from './api.js'

const DEFAULT_FALLBACK = 'materi kuliah hari ini membahas pengenalan ucapan dan teks ke ucapan'

function downloadText(filename, content) {
  const blob = new Blob([content || ''], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

function StatusBadge({ label, value, ok }) {
  return (
    <div className={`status-badge ${ok ? 'ok' : 'warn'}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  )
}

function App() {
  const [health, setHealth] = useState(null)
  const [file, setFile] = useState(null)
  const [fallbackText, setFallbackText] = useState(DEFAULT_FALLBACK)
  const [transcription, setTranscription] = useState('')
  const [summary, setSummary] = useState('')
  const [audioUrl, setAudioUrl] = useState('')
  const [modes, setModes] = useState({ stt: '-', summarize: '-', tts: '-' })
  const [loading, setLoading] = useState('')
  const [error, setError] = useState('')
  const [warnings, setWarnings] = useState([])

  const fileInputRef = useRef(null)

  const selectedFileName = useMemo(() => file?.name || 'Belum ada file audio', [file])

  async function refreshHealth() {
    try {
      const data = await getHealth()
      setHealth(data)
    } catch (err) {
      setError(err.message)
    }
  }

  useEffect(() => {
    refreshHealth()
  }, [])

  async function handleTranscribe() {
    if (!file) {
      setError('Pilih file audio terlebih dahulu.')
      return
    }
    setLoading('transcribe')
    setError('')
    setWarnings([])
    try {
      const data = await transcribeAudio(file, fallbackText)
      setTranscription(data.transcription || '')
      setModes((old) => ({ ...old, stt: data.mode || '-' }))
      if (data.error) setWarnings([`STT: ${data.error}`])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading('')
    }
  }

  async function handleSummarize() {
    if (!transcription.trim()) {
      setError('Transkripsi masih kosong.')
      return
    }
    setLoading('summarize')
    setError('')
    setWarnings([])
    try {
      const data = await summarizeText(transcription)
      setSummary(data.summary || '')
      setModes((old) => ({ ...old, summarize: data.mode || '-' }))
      if (data.error) setWarnings([`Ringkasan: ${data.error}`])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading('')
    }
  }

  async function handleTTS() {
    const text = summary.trim() || transcription.trim()
    if (!text) {
      setError('Ringkasan/transkripsi masih kosong.')
      return
    }
    setLoading('tts')
    setError('')
    setWarnings([])
    try {
      const data = await generateTTS(text)
      setAudioUrl(data.audio_url || '')
      setModes((old) => ({ ...old, tts: data.mode || '-' }))
      if (data.error) setWarnings([`TTS: ${data.error}`])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading('')
    }
  }

  async function handleProcessAll() {
    if (!file) {
      setError('Pilih file audio terlebih dahulu.')
      return
    }
    setLoading('all')
    setError('')
    setWarnings([])
    try {
      const data = await processAll(file, fallbackText)
      setTranscription(data.transcription || '')
      setSummary(data.summary || '')
      setAudioUrl(data.audio_url || '')
      setModes({
        stt: data.stt_mode || '-',
        summarize: data.summarize_mode || '-',
        tts: data.tts_mode || '-',
      })
      setWarnings(data.warnings || [])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading('')
    }
  }

  return (
    <main className="app-shell">
      <section className="hero-card">
        <div>
          <p className="eyebrow">PUTU • React + FastAPI</p>
          <h1>Perancangan dan Implementasi Aplikasi Catatan Kuliah Otomatis</h1>
          <p className="subtitle">Berbasis Speech-to-Text dan Text-to-Speech</p>
          <p className="description">
            Aplikasi menerima audio perkuliahan, mengubahnya menjadi teks, membuat ringkasan catatan kuliah menggunakan Gemini API, lalu membacakan ringkasan melalui modul TTS.
          </p>
        </div>
        <div className="status-panel">
          <StatusBadge label="Backend" value={health?.status || 'checking'} ok={health?.status === 'ok'} />
          <StatusBadge label="STT model" value={health?.stt?.available ? 'tersedia' : 'fallback'} ok={health?.stt?.available} />
          <StatusBadge label="Gemini" value={health?.summarizer?.gemini_configured ? 'aktif' : 'lokal'} ok={health?.summarizer?.gemini_configured} />
          <StatusBadge label="TTS" value={health?.tts?.engine || '-'} ok={true} />
          <button className="secondary-btn" onClick={refreshHealth}>Refresh status</button>
        </div>
      </section>

      {error && <div className="alert error">{error}</div>}
      {warnings.length > 0 && (
        <div className="alert warn">
          {warnings.map((item, index) => <div key={index}>{item}</div>)}
        </div>
      )}

      <section className="grid two-cols">
        <div className="card">
          <div className="section-title">
            <span className="step">1</span>
            <div>
              <h2>Input Audio Kuliah</h2>
              <p>Upload file audio hasil rekaman perkuliahan.</p>
            </div>
          </div>
          <input
            ref={fileInputRef}
            type="file"
            accept="audio/*"
            onChange={(event) => setFile(event.target.files?.[0] || null)}
            hidden
          />
          <button className="upload-box" onClick={() => fileInputRef.current?.click()}>
            <strong>{selectedFileName}</strong>
            <span>Klik untuk memilih file .wav, .mp3, .m4a, .webm, atau format audio lain</span>
          </button>
          {file && <audio className="audio-player" controls src={URL.createObjectURL(file)} />}

          <label className="field-label">Teks cadangan jika model STT belum dimasukkan</label>
          <textarea
            value={fallbackText}
            onChange={(event) => setFallbackText(event.target.value)}
            rows={3}
            placeholder="Teks ini dipakai hanya ketika model STT lokal belum tersedia/error."
          />
        </div>

        <div className="card pipeline-card">
          <h2>Alur Sistem</h2>
          <div className="pipeline">
            <span>Audio</span>
            <span>STT</span>
            <span>Transkripsi</span>
            <span>Gemini</span>
            <span>Ringkasan</span>
            <span>TTS</span>
            <span>Audio</span>
          </div>
          <button disabled={loading === 'all'} className="primary-btn large" onClick={handleProcessAll}>
            {loading === 'all' ? 'Memproses seluruh alur...' : 'Proses Semua Otomatis'}
          </button>
          <div className="mode-list">
            <p><strong>Mode STT:</strong> {modes.stt}</p>
            <p><strong>Mode Ringkasan:</strong> {modes.summarize}</p>
            <p><strong>Mode TTS:</strong> {modes.tts}</p>
          </div>
        </div>
      </section>

      <section className="grid three-actions">
        <button disabled={loading === 'transcribe'} className="primary-btn" onClick={handleTranscribe}>
          {loading === 'transcribe' ? 'Memproses STT...' : 'Proses STT'}
        </button>
        <button disabled={loading === 'summarize'} className="primary-btn" onClick={handleSummarize}>
          {loading === 'summarize' ? 'Meringkas...' : 'Buat Ringkasan'}
        </button>
        <button disabled={loading === 'tts'} className="primary-btn" onClick={handleTTS}>
          {loading === 'tts' ? 'Membuat Audio...' : 'Generate TTS'}
        </button>
      </section>

      <section className="grid two-cols">
        <div className="card result-card">
          <div className="result-header">
            <h2>Hasil Transkripsi</h2>
            <button className="secondary-btn" onClick={() => downloadText('transkripsi.txt', transcription)}>Download TXT</button>
          </div>
          <textarea
            value={transcription}
            onChange={(event) => setTranscription(event.target.value)}
            rows={12}
            placeholder="Hasil Speech-to-Text akan tampil di sini."
          />
        </div>

        <div className="card result-card">
          <div className="result-header">
            <h2>Ringkasan Catatan Kuliah</h2>
            <button className="secondary-btn" onClick={() => downloadText('ringkasan.txt', summary)}>Download TXT</button>
          </div>
          <textarea
            value={summary}
            onChange={(event) => setSummary(event.target.value)}
            rows={12}
            placeholder="Hasil ringkasan dari Gemini API akan tampil di sini."
          />
        </div>
      </section>

      <section className="card audio-output-card">
        <div className="result-header">
          <div>
            <h2>Output Audio TTS</h2>
            <p>Audio yang diputar merupakan hasil pembacaan ringkasan atau transkripsi.</p>
          </div>
          {audioUrl && <a className="secondary-btn" href={audioUrl} download>Download Audio</a>}
        </div>
        {audioUrl ? (
          <audio className="audio-player wide" controls src={audioUrl} />
        ) : (
          <div className="empty-state">Belum ada audio. Klik Generate TTS atau Proses Semua Otomatis.</div>
        )}
      </section>

      <footer>
        <p>Backend API: {API_BASE}</p>
      </footer>
    </main>
  )
}

export default App

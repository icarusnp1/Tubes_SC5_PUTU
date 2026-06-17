import { useEffect, useMemo, useRef, useState } from 'react'
import {
  API_BASE,
  generateTTS,
  getHealth,
  processAll,
  summarizeText,
  transcribeAudio,
} from './api.js'

const DEFAULT_FALLBACK = 'materi kuliah hari ini membahas pengenalan ucapan dan teks ke ucapan'
const STORAGE_KEY = 'putu_catatan_kuliah_history_minimal_ui'
const EMPTY_MODES = { stt: '-', summarize: '-', tts: '-' }

const MODE_LABEL = {
  singkat: 'Singkat',
  detail: 'Detail',
  ujian: 'Ujian',
}

function createId() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) return crypto.randomUUID()
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`
}

function normalizeArray(value) {
  if (Array.isArray(value)) return value.filter(Boolean).map((item) => String(item))
  return []
}

function formatDate(value) {
  if (!value) return '-'
  return new Date(value).toLocaleString('id-ID', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function buildNoteText(payload) {
  const note = payload.structuredNote || {}
  const parts = []
  parts.push(payload.noteTitle || note.title || 'Catatan Kuliah')
  parts.push(`${payload.courseName || note.course_name || '-'}`)
  parts.push('')

  if (note.summary) parts.push('Ringkasan', note.summary, '')

  const sections = [
    ['Poin Penting', normalizeArray(note.important_points), 'bullet'],
    ['Kata Kunci', normalizeArray(note.keywords), 'bullet'],
    ['Pertanyaan Latihan', normalizeArray(note.questions), 'number'],
    ['Tindak Lanjut', normalizeArray(note.action_items), 'bullet'],
  ]

  for (const [title, items, type] of sections) {
    if (!items.length) continue
    parts.push(title)
    items.forEach((item, index) => parts.push(type === 'number' ? `${index + 1}. ${item}` : `- ${item}`))
    parts.push('')
  }

  if (note.conclusion) parts.push('Kesimpulan', note.conclusion, '')
  if (!note.summary && payload.summary) parts.push('Catatan', payload.summary, '')
  if (payload.transcription) parts.push('Transkripsi', payload.transcription, '')
  return parts.join('\n').trim()
}

function exportPdf(payload) {
  const note = payload.structuredNote || {}
  const title = payload.noteTitle || note.title || 'Catatan Kuliah'
  const course = payload.courseName || note.course_name || '-'
  const noteText = buildNoteText(payload)
  const html = noteText
    .split('\n')
    .map((line) => line.trim())
    .map((line, index) => {
      if (!line) return '<br />'
      const escaped = line.replace(/[&<>]/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[char]))
      if (index === 0) return `<h1>${escaped}</h1>`
      if (index === 1) return `<p class="meta">${escaped}</p>`
      if (/^(Ringkasan|Poin Penting|Kata Kunci|Pertanyaan Latihan|Tindak Lanjut|Kesimpulan|Catatan|Transkripsi)$/i.test(line)) return `<h2>${escaped}</h2>`
      if (line.startsWith('- ')) return `<li>${escaped.slice(2)}</li>`
      if (/^\d+\./.test(line)) return `<p class="numbered">${escaped}</p>`
      return `<p>${escaped}</p>`
    })
    .join('')

  const win = window.open('', '_blank')
  if (!win) return
  win.document.write(`
    <html>
      <head>
        <title>${title}</title>
        <style>
          body { font-family: Arial, sans-serif; padding: 36px; line-height: 1.6; color: #202124; }
          h1 { font-size: 24px; margin: 0 0 6px; }
          .meta { color: #5f6368; margin-bottom: 22px; }
          h2 { font-size: 15px; margin: 20px 0 8px; color: #5f4700; }
          p { margin: 6px 0; }
          li { margin: 5px 0; }
        </style>
      </head>
      <body>${html}</body>
    </html>
  `)
  win.document.close()
  win.focus()
  win.print()
}

function TopBar({ query, onQueryChange, onRefresh, onToggleSettings, health }) {
  return (
    <header className="topbar">
      <div className="brand" title="AutoNote Kuliah">
        <span className="brand-mark">📝</span>
        <strong>AutoNote</strong>
      </div>
      <div className="search-wrap">
        <span>⌕</span>
        <input value={query} onChange={(e) => onQueryChange(e.target.value)} placeholder="Cari..." />
      </div>
      <div className="top-actions">
        <span className={`tiny-dot ${health?.status === 'ok' ? 'ok' : ''}`} title={`API: ${health?.status || 'checking'}`} />
        <button className="icon-btn" onClick={onRefresh} title="Refresh">↻</button>
        <button className="icon-btn" onClick={onToggleSettings} title="Pengaturan">⚙</button>
      </div>
    </header>
  )
}

function ProgressDots({ loading, hasTranscription, hasSummary, hasAudio }) {
  const steps = [
    ['🎙', Boolean(loading || hasTranscription || hasSummary || hasAudio), 'Audio'],
    ['✍', Boolean(hasTranscription), 'Transkripsi'],
    ['✨', Boolean(hasSummary), 'Catatan'],
    ['▶', Boolean(hasAudio), 'Audio TTS'],
  ]
  return (
    <div className="progress-dots">
      {steps.map(([icon, done, label]) => <span key={label} className={done ? 'done' : ''} title={label}>{icon}</span>)}
    </div>
  )
}

function NotePreview({ note }) {
  if (!note) return <div className="empty-note">Belum ada catatan.</div>

  const points = normalizeArray(note.important_points)
  const keywords = normalizeArray(note.keywords)
  const questions = normalizeArray(note.questions)
  const actions = normalizeArray(note.action_items)

  return (
    <article className="note-preview">
      {note.summary && <p className="summary-text">{note.summary}</p>}

      {points.length > 0 && (
        <section>
          <h3>• Poin</h3>
          <ul>{points.map((item, index) => <li key={index}>{item}</li>)}</ul>
        </section>
      )}

      {keywords.length > 0 && <div className="chip-list">{keywords.map((item, index) => <span key={index}>#{item}</span>)}</div>}

      {questions.length > 0 && (
        <section>
          <h3>? Latihan</h3>
          <ol>{questions.map((item, index) => <li key={index}>{item}</li>)}</ol>
        </section>
      )}

      {actions.length > 0 && (
        <section>
          <h3>✓ Lanjut</h3>
          <ul>{actions.map((item, index) => <li key={index}>{item}</li>)}</ul>
        </section>
      )}

      {note.conclusion && <p className="conclusion-text">{note.conclusion}</p>}
    </article>
  )
}

function HistoryCard({ note, onOpen, onDelete, onExportPdf }) {
  const keywords = normalizeArray(note.structuredNote?.keywords).slice(0, 3)
  const preview = note.structuredNote?.summary || note.summary || note.transcription || '-'

  return (
    <article className="history-card">
      <button className="history-open" onClick={() => onOpen(note)} title="Buka catatan">
        <h3>{note.noteTitle || note.structuredNote?.title || 'Catatan'}</h3>
        <p>{note.courseName || note.structuredNote?.course_name || 'Tanpa mata kuliah'}</p>
        <small>{formatDate(note.createdAt)}</small>
        <div className="history-preview">{preview}</div>
        {keywords.length > 0 && <div className="mini-chip-list">{keywords.map((item, index) => <span key={index}>#{item}</span>)}</div>}
      </button>
      <div className="history-actions">
        <button onClick={() => onOpen(note)} title="Buka">↗</button>
        <button onClick={() => onExportPdf(note)} title="PDF">📄</button>
        <button onClick={() => onDelete(note.id)} title="Hapus">🗑</button>
      </div>
    </article>
  )
}

function App() {
  const [health, setHealth] = useState(null)
  const [file, setFile] = useState(null)
  const [filePreviewUrl, setFilePreviewUrl] = useState('')
  const [fallbackText, setFallbackText] = useState(DEFAULT_FALLBACK)
  const [noteTitle, setNoteTitle] = useState('')
  const [courseName, setCourseName] = useState('')
  const [summaryMode, setSummaryMode] = useState('singkat')
  const [transcription, setTranscription] = useState('')
  const [summary, setSummary] = useState('')
  const [structuredNote, setStructuredNote] = useState(null)
  const [audioUrl, setAudioUrl] = useState('')
  const [modes, setModes] = useState(EMPTY_MODES)
  const [loading, setLoading] = useState('')
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [warnings, setWarnings] = useState([])
  const [history, setHistory] = useState([])
  const [historyQuery, setHistoryQuery] = useState('')
  const [composerOpen, setComposerOpen] = useState(true)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [editOpen, setEditOpen] = useState(false)

  const fileInputRef = useRef(null)

  const currentTitle = noteTitle || structuredNote?.title || 'Catatan baru'
  const currentCourse = courseName || structuredNote?.course_name || 'Mata kuliah'
  const selectedFileName = file?.name || 'Audio'

  const notePayload = useMemo(() => ({
    noteTitle: currentTitle,
    courseName: currentCourse,
    summaryMode,
    transcription,
    summary,
    structuredNote,
    audioUrl,
    modes,
  }), [currentTitle, currentCourse, summaryMode, transcription, summary, structuredNote, audioUrl, modes])

  const filteredHistory = useMemo(() => {
    const q = historyQuery.toLowerCase().trim()
    if (!q) return history
    return history.filter((note) => [
      note.noteTitle,
      note.courseName,
      note.summary,
      note.transcription,
      note.structuredNote?.summary,
      normalizeArray(note.structuredNote?.keywords).join(' '),
    ].join(' ').toLowerCase().includes(q))
  }, [history, historyQuery])

  useEffect(() => {
    if (!file) {
      setFilePreviewUrl('')
      return undefined
    }
    const url = URL.createObjectURL(file)
    setFilePreviewUrl(url)
    return () => URL.revokeObjectURL(url)
  }, [file])

  useEffect(() => {
    refreshHealth()
    loadHistory()
  }, [])

  async function refreshHealth() {
    try {
      const data = await getHealth()
      setHealth(data)
    } catch (err) {
      setError(err.message)
    }
  }

  function loadHistory() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY)
      setHistory(raw ? JSON.parse(raw) : [])
    } catch {
      setHistory([])
    }
  }

  function saveHistory(nextHistory) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(nextHistory))
    setHistory(nextHistory)
  }

  function resetMessages() {
    setError('')
    setSuccess('')
    setWarnings([])
  }

  function saveCurrentNote() {
    if (!transcription.trim() && !summary.trim() && !structuredNote) {
      setError('Belum ada catatan.')
      return
    }

    const note = {
      id: createId(),
      createdAt: new Date().toISOString(),
      noteTitle: currentTitle,
      courseName: currentCourse,
      summaryMode,
      transcription,
      summary,
      structuredNote,
      audioUrl,
      modes,
    }
    saveHistory([note, ...history].slice(0, 80))
    resetMessages()
    setSuccess('Tersimpan.')
  }

  function openHistory(note) {
    setNoteTitle(note.noteTitle || '')
    setCourseName(note.courseName || '')
    setSummaryMode(note.summaryMode || 'singkat')
    setTranscription(note.transcription || '')
    setSummary(note.summary || '')
    setStructuredNote(note.structuredNote || null)
    setAudioUrl(note.audioUrl || '')
    setModes(note.modes || EMPTY_MODES)
    setComposerOpen(false)
    setEditOpen(false)
    resetMessages()
  }

  function deleteHistory(id) {
    saveHistory(history.filter((note) => note.id !== id))
  }

  function clearCurrent() {
    setFile(null)
    setNoteTitle('')
    setCourseName('')
    setSummaryMode('singkat')
    setTranscription('')
    setSummary('')
    setStructuredNote(null)
    setAudioUrl('')
    setModes(EMPTY_MODES)
    setComposerOpen(true)
    setEditOpen(false)
    resetMessages()
  }

  async function transcribeOnly() {
    if (!file) {
      setError('Pilih audio dulu.')
      return
    }
    setLoading('transcribe')
    resetMessages()
    try {
      const data = await transcribeAudio(file, fallbackText)
      const text = data.transcription || data.text || ''
      setTranscription(text)
      setModes((old) => ({ ...old, stt: data.mode || '-' }))
      if (data.error) setWarnings([`STT: ${data.error}`])
      setEditOpen(true)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading('')
    }
  }

  async function makeNoteOnly() {
    if (!transcription.trim()) {
      setError('Transkripsi kosong.')
      return
    }
    setLoading('summarize')
    resetMessages()
    try {
      const data = await summarizeText(transcription, { summaryMode, noteTitle: currentTitle, courseName: currentCourse })
      setSummary(data.summary || '')
      setStructuredNote(data.structured_note || null)
      setModes((old) => ({ ...old, summarize: data.mode || '-' }))
      if (data.error) setWarnings([`Ringkasan: ${data.error}`])
      setComposerOpen(false)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading('')
    }
  }

  async function makeAudio() {
    const text = structuredNote?.summary || summary.trim() || transcription.trim()
    if (!text) {
      setError('Catatan kosong.')
      return
    }
    setLoading('tts')
    resetMessages()
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

  async function makeAll() {
    if (!file) {
      setError('Pilih audio dulu.')
      return
    }
    setLoading('all')
    resetMessages()
    try {
      const data = await processAll(file, fallbackText, { summaryMode, noteTitle: currentTitle, courseName: currentCourse })
      setTranscription(data.transcription || '')
      setSummary(data.summary || '')
      setStructuredNote(data.structured_note || null)
      setAudioUrl(data.audio_url || '')
      setModes({
        stt: data.stt_mode || '-',
        summarize: data.summarize_mode || '-',
        tts: data.tts_mode || '-',
      })
      setWarnings(data.warnings || [])
      setComposerOpen(false)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading('')
    }
  }

  const isBusy = Boolean(loading)

  return (
    <main className="app-shell">
      <TopBar
        query={historyQuery}
        onQueryChange={setHistoryQuery}
        health={health}
        onRefresh={refreshHealth}
        onToggleSettings={() => setSettingsOpen(!settingsOpen)}
      />

      {error && <div className="toast error">⚠ {error}</div>}
      {success && <div className="toast success">✓ {success}</div>}
      {warnings.length > 0 && <div className="toast warn">{warnings.map((item, index) => <div key={index}>⚠ {item}</div>)}</div>}

      <section className={`composer-card ${composerOpen ? 'open' : ''}`}>
        <button className="composer-head" onClick={() => setComposerOpen(!composerOpen)} title="Buat catatan">
          <span>＋</span>
          <strong>{composerOpen ? 'Catatan dari audio' : 'Catatan baru'}</strong>
        </button>

        {composerOpen && (
          <div className="composer-body">
            <div className="composer-grid compact">
              <input value={noteTitle} onChange={(e) => setNoteTitle(e.target.value)} placeholder="Judul" title="Judul" />
              <input value={courseName} onChange={(e) => setCourseName(e.target.value)} placeholder="Mata kuliah" title="Mata kuliah" />
              <select value={summaryMode} onChange={(e) => setSummaryMode(e.target.value)} title="Mode">
                <option value="singkat">Singkat</option>
                <option value="detail">Detail</option>
                <option value="ujian">Ujian</option>
              </select>
            </div>

            <input ref={fileInputRef} type="file" accept="audio/*" onChange={(event) => setFile(event.target.files?.[0] || null)} hidden />
            <button className="upload-card" onClick={() => fileInputRef.current?.click()} title="Upload audio">
              <span>🎙</span>
              <strong>{selectedFileName}</strong>
            </button>
            {filePreviewUrl && <audio className="audio-player" controls src={filePreviewUrl} />}

            <div className="composer-actions icon-actions">
              <button disabled={isBusy} className="primary-btn" onClick={makeAll} title="Buat catatan otomatis">✨ Buat</button>
              <button disabled={isBusy} className="icon-action" onClick={transcribeOnly} title="Transkripsi saja">✍</button>
              <button className="icon-action" onClick={() => setSettingsOpen(!settingsOpen)} title="Pengaturan">⚙</button>
            </div>
          </div>
        )}
      </section>

      {settingsOpen && (
        <section className="settings-card">
          <textarea value={fallbackText} onChange={(e) => setFallbackText(e.target.value)} rows={3} placeholder="Fallback STT" />
          <div className="mode-list">
            <span>STT: {modes.stt}</span>
            <span>Gemini: {modes.summarize}</span>
            <span>TTS: {modes.tts}</span>
            <span>API: {API_BASE}</span>
          </div>
        </section>
      )}

      <ProgressDots loading={loading} hasTranscription={Boolean(transcription)} hasSummary={Boolean(summary || structuredNote)} hasAudio={Boolean(audioUrl)} />

      <section className="active-note-card">
        <div className="note-title-row">
          <div>
            <h2>{currentTitle}</h2>
            <p>{currentCourse} • {MODE_LABEL[summaryMode]}</p>
          </div>
          <div className="note-actions icon-actions">
            <button onClick={clearCurrent} title="Baru">＋</button>
            <button onClick={saveCurrentNote} title="Simpan">💾</button>
            <button onClick={() => exportPdf(notePayload)} title="Export PDF">📄</button>
            <button onClick={() => setEditOpen(!editOpen)} title="Edit">✎</button>
          </div>
        </div>

        <NotePreview note={structuredNote} />

        <div className="action-strip minimal">
          <button disabled={!transcription.trim() || isBusy} onClick={makeNoteOnly} title="Buat catatan">✨</button>
          <button disabled={isBusy} onClick={makeAudio} title="Dengarkan">▶</button>
        </div>

        {audioUrl && (
          <div className="audio-note">
            <audio controls src={audioUrl} />
            <a href={audioUrl} download title="Download audio">⬇</a>
          </div>
        )}

        {editOpen && (
          <div className="editor-grid">
            <textarea value={transcription} onChange={(e) => setTranscription(e.target.value)} rows={9} placeholder="Transkripsi" />
            <textarea value={summary} onChange={(e) => setSummary(e.target.value)} rows={9} placeholder="Catatan markdown" />
          </div>
        )}
      </section>

      <section className="history-section">
        <div className="section-head-row">
          <h2>Riwayat</h2>
          <button onClick={() => confirm('Hapus seluruh riwayat?') && saveHistory([])} title="Kosongkan">🗑</button>
        </div>

        {filteredHistory.length === 0 ? (
          <div className="empty-board">Kosong.</div>
        ) : (
          <div className="notes-grid">
            {filteredHistory.map((note) => (
              <HistoryCard
                key={note.id}
                note={note}
                onOpen={openHistory}
                onDelete={deleteHistory}
                onExportPdf={(item) => exportPdf({ ...item, structuredNote: item.structuredNote })}
              />
            ))}
          </div>
        )}
      </section>
    </main>
  )
}

export default App

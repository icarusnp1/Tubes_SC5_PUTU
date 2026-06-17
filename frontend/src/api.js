const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

async function parseResponse(response) {
  let data
  try {
    data = await response.json()
  } catch {
    data = { detail: await response.text() }
  }

  if (!response.ok) {
    const message = data?.detail || data?.message || 'Terjadi kesalahan pada server.'
    throw new Error(typeof message === 'string' ? message : JSON.stringify(message))
  }

  return data
}

export async function getHealth() {
  const response = await fetch(`${API_BASE}/api/health`)
  return parseResponse(response)
}

export async function transcribeAudio(file, fallbackText = '') {
  const formData = new FormData()
  formData.append('file', file)
  if (fallbackText) formData.append('fallback_text', fallbackText)

  const response = await fetch(`${API_BASE}/api/transcribe`, {
    method: 'POST',
    body: formData,
  })

  return parseResponse(response)
}

export async function summarizeText(text, options = {}) {
  const response = await fetch(`${API_BASE}/api/summarize`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      text,
      summary_mode: options.summaryMode || 'singkat',
      note_title: options.noteTitle || '',
      course_name: options.courseName || '',
    }),
  })

  return parseResponse(response)
}

export async function generateTTS(text) {
  const response = await fetch(`${API_BASE}/api/tts`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  })

  return parseResponse(response)
}

export async function processAll(file, fallbackText = '', options = {}) {
  const formData = new FormData()
  formData.append('file', file)
  if (fallbackText) formData.append('fallback_text', fallbackText)
  formData.append('summary_mode', options.summaryMode || 'singkat')
  formData.append('note_title', options.noteTitle || '')
  formData.append('course_name', options.courseName || '')

  const response = await fetch(`${API_BASE}/api/process-all`, {
    method: 'POST',
    body: formData,
  })

  return parseResponse(response)
}

export async function exportDocx(notePayload) {
  const response = await fetch(`${API_BASE}/api/export-docx`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(notePayload),
  })

  if (!response.ok) {
    let message = 'Gagal export DOCX.'
    try {
      const data = await response.json()
      message = data?.detail || message
    } catch {
      message = await response.text()
    }
    throw new Error(typeof message === 'string' ? message : JSON.stringify(message))
  }

  const blob = await response.blob()
  const disposition = response.headers.get('content-disposition') || ''
  const match = disposition.match(/filename="?([^";]+)"?/)
  const filename = match?.[1] || 'catatan_kuliah.docx'
  return { blob, filename }
}

export { API_BASE }

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

export async function summarizeText(text) {
  const response = await fetch(`${API_BASE}/api/summarize`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
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

export async function processAll(file, fallbackText = '') {
  const formData = new FormData()
  formData.append('file', file)
  if (fallbackText) formData.append('fallback_text', fallbackText)

  const response = await fetch(`${API_BASE}/api/process-all`, {
    method: 'POST',
    body: formData,
  })

  return parseResponse(response)
}

export { API_BASE }

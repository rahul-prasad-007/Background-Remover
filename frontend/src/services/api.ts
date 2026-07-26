export type StageKey =
  | 'uploading'
  | 'removing_background'
  | 'detecting_faces'
  | 'restoring_faces'
  | 'enhancing_image'
  | 'finalizing'
  | 'complete'
  | 'error'

export type StageStatus = 'pending' | 'active' | 'done' | 'skipped' | 'error'

export type QualityMode = 'auto' | 'original' | '2' | '4'

export interface ProgressEvent {
  stage: StageKey
  label: string
  status: StageStatus
  progress: number
  message?: string | null
  faces_found?: number | null
  download_url?: string | null
  job_id?: string | null
}

export const PIPELINE_STEPS: { key: StageKey; label: string }[] = [
  { key: 'uploading', label: 'Uploading...' },
  { key: 'removing_background', label: 'Removing Background...' },
  { key: 'detecting_faces', label: 'Detecting Faces...' },
  { key: 'restoring_faces', label: 'Restoring Faces...' },
  { key: 'enhancing_image', label: 'Enhancing Image...' },
  { key: 'finalizing', label: 'Finalizing...' },
]

const API_BASE = import.meta.env.VITE_API_URL ?? ''

function parseSseChunk(chunk: string): ProgressEvent | null {
  const line = chunk
    .split('\n')
    .map((l) => l.trim())
    .find((l) => l.startsWith('data:'))
  if (!line) return null
  try {
    return JSON.parse(line.slice(5).trim()) as ProgressEvent
  } catch {
    return null
  }
}

export async function processImage(
  file: File,
  onProgress: (event: ProgressEvent) => void,
  signal?: AbortSignal,
  quality: QualityMode = 'auto',
): Promise<{ downloadUrl: string; jobId: string }> {
  const form = new FormData()
  form.append('file', file)
  form.append('quality', quality)

  const response = await fetch(`${API_BASE}/api/process`, {
    method: 'POST',
    body: form,
    signal,
  })

  if (!response.ok) {
    let detail = 'Processing failed'
    try {
      const err = await response.json()
      detail = err.detail ?? detail
    } catch {
      /* ignore */
    }
    throw new Error(typeof detail === 'string' ? detail : 'Processing failed')
  }

  if (!response.body) {
    throw new Error('No response stream from server')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let downloadUrl = ''
  let jobId = ''
  let lastStage = ''

  const handleEvent = (payload: ProgressEvent) => {
    onProgress(payload)
    lastStage = payload.stage
    if (payload.stage === 'error') {
      throw new Error(payload.message || 'Pipeline error')
    }
    if (payload.download_url) {
      downloadUrl = `${API_BASE}${payload.download_url}`
    }
    if (payload.job_id) {
      jobId = payload.job_id
    }
  }

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const chunks = buffer.split('\n\n')
    buffer = chunks.pop() ?? ''

    for (const chunk of chunks) {
      const payload = parseSseChunk(chunk)
      if (payload) handleEvent(payload)
    }
  }

  // Flush trailing SSE frame (no final \n\n)
  if (buffer.trim()) {
    const payload = parseSseChunk(buffer)
    if (payload) handleEvent(payload)
  }

  if (!downloadUrl && jobId) {
    // Stream dropped (e.g. host OOM restart) — try download if file was written
    const guess = `${API_BASE}/api/download/${jobId}`
    try {
      const probe = await fetch(guess, { method: 'HEAD', signal })
      if (probe.ok) downloadUrl = guess
    } catch {
      /* ignore */
    }
  }

  if (!downloadUrl) {
    if (lastStage === 'removing_background' || lastStage === 'enhancing_image') {
      throw new Error(
        'Server ran out of memory while processing. Try “Original” quality or a smaller image.',
      )
    }
    throw new Error(
      'Processing finished without a result. Try again with Original quality or a smaller photo.',
    )
  }

  return { downloadUrl, jobId }
}

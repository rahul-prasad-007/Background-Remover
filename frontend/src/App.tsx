import { useEffect, useMemo, useRef, useState } from 'react'
import { SiteHeader } from './components/SiteHeader'
import { Hero } from './components/Hero'
import { UploadZone } from './components/UploadZone'
import { QualitySelector, type QualityMode } from './components/QualitySelector'
import { ProcessButton } from './components/ProcessButton'
import { ProcessingScreen } from './components/ProcessingScreen'
import { ResultSection } from './components/ResultSection'
import {
  processImage,
  type ProgressEvent,
  type StageKey,
} from './services/api'

type AppPhase = 'idle' | 'ready' | 'processing' | 'done' | 'error'

export default function App() {
  const [file, setFile] = useState<File | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [phase, setPhase] = useState<AppPhase>('idle')
  const [error, setError] = useState<string | null>(null)
  const [events, setEvents] = useState<Partial<Record<StageKey, ProgressEvent>>>({})
  const [progress, setProgress] = useState(0)
  const [resultUrl, setResultUrl] = useState<string | null>(null)
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null)
  const [quality, setQuality] = useState<QualityMode>('auto')
  const abortRef = useRef<AbortController | null>(null)

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl)
      if (resultUrl?.startsWith('blob:')) URL.revokeObjectURL(resultUrl)
      abortRef.current?.abort()
    }
  }, [previewUrl, resultUrl])

  const busy = phase === 'processing'

  const onFileAccepted = (next: File) => {
    abortRef.current?.abort()
    if (previewUrl) URL.revokeObjectURL(previewUrl)
    if (resultUrl?.startsWith('blob:')) URL.revokeObjectURL(resultUrl)
    setFile(next)
    setPreviewUrl(URL.createObjectURL(next))
    setPhase('ready')
    setError(null)
    setEvents({})
    setProgress(0)
    setResultUrl(null)
    setDownloadUrl(null)
  }

  const onClear = () => {
    abortRef.current?.abort()
    if (previewUrl) URL.revokeObjectURL(previewUrl)
    if (resultUrl?.startsWith('blob:')) URL.revokeObjectURL(resultUrl)
    setFile(null)
    setPreviewUrl(null)
    setPhase('idle')
    setError(null)
    setEvents({})
    setProgress(0)
    setResultUrl(null)
    setDownloadUrl(null)
  }

  const onProcess = async () => {
    if (!file) return
    const controller = new AbortController()
    abortRef.current = controller
    setPhase('processing')
    setError(null)
    setEvents({})
    setProgress(2)
    setResultUrl(null)
    setDownloadUrl(null)

    try {
      const { downloadUrl: url } = await processImage(
        file,
        (event) => {
          setEvents((prev) => ({ ...prev, [event.stage]: event }))
          setProgress(event.progress)
        },
        controller.signal,
        quality,
      )

      setDownloadUrl(url)

      // Load preview with retries (download can briefly 404 during server reload)
      let preview: string | null = null
      for (let attempt = 0; attempt < 4; attempt++) {
        try {
          if (attempt > 0) {
            await new Promise((r) => setTimeout(r, 400 * attempt))
          }
          const res = await fetch(url, { cache: 'no-store' })
          if (!res.ok) continue
          const blob = await res.blob()
          if (blob.size < 100) continue
          preview = URL.createObjectURL(blob)
          break
        } catch {
          /* retry */
        }
      }

      // Fallback: use the API URL directly in <img> (still downloadable)
      setResultUrl(preview ?? url)
      setProgress(100)
      setPhase('done')
    } catch (err) {
      if ((err as Error).name === 'AbortError') return
      setPhase('error')
      const raw = err instanceof Error ? err.message : 'Something went wrong'
      const friendly =
        /allocate memory|out of memory|oom|not enough ram|safe mode/i.test(raw)
          ? 'PC was low on memory — close Chrome tabs/other apps and try again. The app will auto-shrink large photos.'
          : /api key|REMOVE_BG/i.test(raw)
            ? 'remove.bg API key missing or invalid. Add REMOVE_BG_API_KEY in backend/.env'
            : raw
      setError(friendly)
    }
  }

  const errorText = useMemo(() => error, [error])
  const showControls = phase === 'idle' || phase === 'ready' || phase === 'error'

  return (
    <div className="relative min-h-svh overflow-x-hidden pb-10">
      <SiteHeader />
      <Hero />

      {showControls && (
        <>
          <UploadZone
            disabled={busy}
            file={file}
            previewUrl={previewUrl}
            onFileAccepted={onFileAccepted}
            onClear={onClear}
            onError={(message) => {
              setError(message)
              setPhase('error')
            }}
          />

          <QualitySelector value={quality} onChange={setQuality} disabled={busy} />

          <ProcessButton
            disabled={!file}
            loading={busy}
            onClick={onProcess}
          />

          {errorText && (
            <p className="container-app mt-4 text-center text-sm text-red-400">{errorText}</p>
          )}
        </>
      )}

      <ProcessingScreen
        visible={phase === 'processing'}
        events={events}
        overallProgress={progress}
      />

      {phase === 'done' && previewUrl && resultUrl && downloadUrl && (
        <ResultSection
          originalUrl={previewUrl}
          processedUrl={resultUrl}
          downloadUrl={downloadUrl}
          onReset={onClear}
        />
      )}
    </div>
  )
}

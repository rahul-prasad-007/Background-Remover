import { useCallback, useEffect, useRef, useState, type PointerEvent as ReactPointerEvent } from 'react'
import { motion } from 'framer-motion'
import { Check, Download, RefreshCw, Sparkles } from 'lucide-react'

interface ResultSectionProps {
  originalUrl: string
  processedUrl: string
  downloadUrl: string
  onReset: () => void
}

const CHECKS = [
  'Background Removed',
  'Face Restored (If Detected)',
  'Upscaled to HD',
  'Color & Sharpness Enhanced',
]

export function ResultSection({
  originalUrl,
  processedUrl,
  downloadUrl,
  onReset,
}: ResultSectionProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [position, setPosition] = useState(50)
  const [width, setWidth] = useState(0)
  const dragging = useRef(false)

  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const measure = () => setWidth(el.clientWidth)
    measure()
    const observer = new ResizeObserver(measure)
    observer.observe(el)
    return () => observer.disconnect()
  }, [])

  const updateFromClientX = useCallback((clientX: number) => {
    const el = containerRef.current
    if (!el) return
    const rect = el.getBoundingClientRect()
    const pct = ((clientX - rect.left) / rect.width) * 100
    setPosition(Math.min(98, Math.max(2, pct)))
  }, [])

  const onPointerDown = (e: ReactPointerEvent<HTMLDivElement>) => {
    dragging.current = true
    e.currentTarget.setPointerCapture?.(e.pointerId)
    updateFromClientX(e.clientX)
  }

  const onPointerMove = (e: ReactPointerEvent<HTMLDivElement>) => {
    if (!dragging.current) return
    updateFromClientX(e.clientX)
  }

  const onPointerUp = () => {
    dragging.current = false
  }

  return (
    <motion.section
      initial={{ opacity: 0, y: 22 }}
      animate={{ opacity: 1, y: 0 }}
      className="container-app mt-10 pb-16"
    >
      <div className="mb-5 flex items-center gap-2">
        <Sparkles className="h-5 w-5 text-accent" />
        <h2 className="text-xl font-bold text-white sm:text-2xl">Result</h2>
      </div>

      <div className="grid gap-5 lg:grid-cols-[1.4fr_0.85fr]">
        <div className="glass-panel overflow-hidden rounded-3xl p-3 sm:p-4">
          <div
            ref={containerRef}
            className="relative aspect-[4/3] w-full touch-none overflow-hidden rounded-2xl bg-black select-none"
            onPointerDown={onPointerDown}
            onPointerMove={onPointerMove}
            onPointerUp={onPointerUp}
            onPointerCancel={onPointerUp}
          >
            <img
              src={processedUrl}
              alt="Processed"
              className="absolute inset-0 h-full w-full object-contain"
              draggable={false}
            />
            <div className="absolute inset-0 overflow-hidden" style={{ width: `${position}%` }}>
              <img
                src={originalUrl}
                alt="Original"
                className="absolute inset-0 h-full object-contain"
                style={{ width: width || '100%', maxWidth: 'none' }}
                draggable={false}
              />
            </div>

            <div
              className="absolute inset-y-0 z-10 w-0.5 bg-white"
              style={{ left: `${position}%` }}
            >
              <div className="absolute top-1/2 left-1/2 flex h-10 w-10 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full border border-white/40 bg-accent shadow-lg">
                <span className="text-xs font-bold text-white">⟷</span>
              </div>
            </div>

            <span className="absolute top-3 left-3 rounded-lg bg-black/65 px-2.5 py-1 text-[11px] font-semibold text-white backdrop-blur">
              Original Image
            </span>
            <span className="absolute top-3 right-3 rounded-lg bg-accent px-2.5 py-1 text-[11px] font-semibold text-white">
              Processed Image
            </span>
          </div>
        </div>

        <div className="glass-panel flex flex-col rounded-3xl p-5 sm:p-6">
          <h3 className="text-lg font-bold text-white">Your Image is Ready!</h3>
          <ul className="mt-5 space-y-3">
            {CHECKS.map((item) => (
              <li key={item} className="flex items-center gap-2.5 text-sm text-slate-200">
                <span className="flex h-5 w-5 items-center justify-center rounded-full bg-success-soft text-success">
                  <Check className="h-3.5 w-3.5" strokeWidth={3} />
                </span>
                {item}
              </li>
            ))}
          </ul>

          <a
            href={downloadUrl}
            download="print-ready.png"
            className="mt-7 inline-flex w-full flex-col items-center justify-center rounded-2xl bg-success px-5 py-3.5 text-center font-bold text-white shadow-[0_12px_30px_rgba(34,197,94,0.3)] transition hover:brightness-110"
          >
            <span className="inline-flex items-center gap-2 text-base">
              <Download className="h-4 w-4" />
              Download PNG
            </span>
            <span className="mt-0.5 text-[11px] font-medium text-white/85">
              High Quality • Transparent
            </span>
          </a>

          <button
            type="button"
            onClick={onReset}
            className="mt-3 inline-flex w-full items-center justify-center gap-2 rounded-2xl border border-accent/40 bg-transparent px-5 py-3 text-sm font-semibold text-accent transition hover:bg-accent-soft"
          >
            <RefreshCw className="h-4 w-4" />
            Process Another Image
          </button>
        </div>
      </div>
    </motion.section>
  )
}

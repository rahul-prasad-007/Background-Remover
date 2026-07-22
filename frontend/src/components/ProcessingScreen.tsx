import { AnimatePresence, motion } from 'framer-motion'
import { Check, Circle, Loader2, Minus } from 'lucide-react'
import type { ProgressEvent, StageKey, StageStatus } from '../services/api'

const STEPS: {
  key: StageKey
  title: string
  subtitle: string
  note?: string
}[] = [
  { key: 'uploading', title: 'Uploading', subtitle: 'Preparing your image' },
  { key: 'removing_background', title: 'Removing Background', subtitle: 'Local BiRefNet AI' },
  { key: 'detecting_faces', title: 'Detecting Faces', subtitle: 'Checking face presence' },
  {
    key: 'restoring_faces',
    title: 'Restoring Faces',
    subtitle: 'Using GFPGAN AI',
    note: 'if face detected',
  },
  { key: 'enhancing_image', title: 'Enhancing & Upscaling', subtitle: 'Using Real-ESRGAN' },
  { key: 'finalizing', title: 'Finalizing', subtitle: 'Sharpening & Color Correction' },
]

interface ProcessingScreenProps {
  visible: boolean
  events: Partial<Record<StageKey, ProgressEvent>>
  overallProgress: number
}

function statusOf(
  events: Partial<Record<StageKey, ProgressEvent>>,
  key: StageKey,
): StageStatus {
  return events[key]?.status ?? 'pending'
}

function StepIcon({ status }: { status: StageStatus }) {
  if (status === 'done') return <Check className="h-3.5 w-3.5 text-white" />
  if (status === 'active') return <Loader2 className="h-3.5 w-3.5 animate-spin text-white" />
  if (status === 'skipped') return <Minus className="h-3.5 w-3.5 text-slate-400" />
  return <Circle className="h-3 w-3 text-slate-500" />
}

export function ProcessingScreen({ visible, events, overallProgress }: ProcessingScreenProps) {
  return (
    <AnimatePresence>
      {visible && (
        <motion.section
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          className="container-app mt-10"
        >
          <div className="glass-panel rounded-3xl p-5 sm:p-7">
            <div className="mb-6 flex items-end justify-between gap-3">
              <div>
                <h2 className="text-lg font-bold text-white">Processing Steps</h2>
                <p className="mt-1 text-sm text-muted">Live pipeline progress from the server</p>
              </div>
              <span className="text-xl font-extrabold text-accent tabular-nums">
                {Math.round(overallProgress)}%
              </span>
            </div>

            {/* Desktop horizontal stepper */}
            <ol className="mb-6 hidden gap-2 lg:grid lg:grid-cols-6">
              {STEPS.map((step, index) => {
                const status = statusOf(events, step.key)
                const active = status === 'active'
                const done = status === 'done' || status === 'skipped'
                return (
                  <li key={step.key} className="relative text-center">
                    {index < STEPS.length - 1 && (
                      <span
                        className={[
                          'absolute top-4 left-[58%] h-px w-[84%]',
                          done ? 'bg-accent/70' : 'bg-white/10',
                        ].join(' ')}
                      />
                    )}
                    <div
                      className={[
                        'relative z-10 mx-auto mb-3 flex h-8 w-8 items-center justify-center rounded-full border',
                        active || done
                          ? 'border-accent bg-accent'
                          : 'border-white/15 bg-black/30',
                      ].join(' ')}
                    >
                      <StepIcon status={status} />
                    </div>
                    <p className="text-xs font-semibold text-white">{step.title}</p>
                    <p className="mt-1 text-[10px] leading-snug text-muted">{step.subtitle}</p>
                    {step.note && (
                      <span className="mt-1 inline-block rounded-full bg-white/5 px-1.5 py-0.5 text-[9px] text-slate-400">
                        {step.note}
                      </span>
                    )}
                  </li>
                )
              })}
            </ol>

            {/* Mobile vertical list */}
            <ul className="mb-6 space-y-2.5 lg:hidden">
              {STEPS.map((step) => {
                const status = statusOf(events, step.key)
                const active = status === 'active'
                return (
                  <li
                    key={step.key}
                    className={[
                      'flex items-start gap-3 rounded-2xl border px-3 py-3',
                      active
                        ? 'border-accent/40 bg-accent-soft'
                        : 'border-white/8 bg-black/20',
                    ].join(' ')}
                  >
                    <span
                      className={[
                        'mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full',
                        status === 'done' || status === 'active'
                          ? 'bg-accent'
                          : 'bg-white/10',
                      ].join(' ')}
                    >
                      <StepIcon status={status} />
                    </span>
                    <div className="min-w-0 text-left">
                      <p className="text-sm font-semibold text-white">{step.title}</p>
                      <p className="text-xs text-muted">{events[step.key]?.message || step.subtitle}</p>
                    </div>
                  </li>
                )
              })}
            </ul>

            <div className="h-2 overflow-hidden rounded-full bg-white/8">
              <motion.div
                className="h-full rounded-full bg-linear-to-r from-accent to-[#60a5fa]"
                initial={{ width: 0 }}
                animate={{ width: `${overallProgress}%` }}
                transition={{ type: 'spring', stiffness: 70, damping: 18 }}
              />
            </div>
          </div>
        </motion.section>
      )}
    </AnimatePresence>
  )
}

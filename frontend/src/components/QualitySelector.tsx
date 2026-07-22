import { Info } from 'lucide-react'
import { motion } from 'framer-motion'

export type QualityMode = 'auto' | 'original' | '2' | '4'

const OPTIONS: {
  id: QualityMode
  title: string
  description: string
  recommended?: boolean
}[] = [
  {
    id: 'auto',
    title: 'Auto',
    description: 'Automatically choose best quality',
    recommended: true,
  },
  {
    id: 'original',
    title: 'Original',
    description: 'Keep original size (Background removal only)',
  },
  {
    id: '2',
    title: '2x HD',
    description: 'Increase size 2x (High Quality)',
  },
  {
    id: '4',
    title: '4x Ultra HD',
    description: 'Increase size 4x (Fast AI + sharpen)',
  },
]

interface QualitySelectorProps {
  value: QualityMode
  onChange: (mode: QualityMode) => void
  disabled?: boolean
}

export function QualitySelector({ value, onChange, disabled }: QualitySelectorProps) {
  return (
    <section className="container-app mt-8">
      <div className="mb-4 flex items-center gap-2">
        <h2 className="text-base font-bold text-white sm:text-lg">Output Quality</h2>
        <span className="inline-flex items-center text-muted" title="Choose upscale quality">
          <Info className="h-4 w-4" />
        </span>
      </div>
      <p className="mb-4 text-sm text-muted">Choose the output quality for your image</p>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {OPTIONS.map((opt, index) => {
          const active = value === opt.id
          return (
            <motion.button
              key={opt.id}
              type="button"
              disabled={disabled}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.05 * index }}
              onClick={() => onChange(opt.id)}
              className={[
                'relative rounded-2xl border p-4 text-left transition',
                active
                  ? 'border-accent bg-accent-soft shadow-[0_0_0_1px_rgba(59,130,246,0.35)]'
                  : 'border-white/10 bg-panel/80 hover:border-accent/40 hover:bg-panel-2',
                disabled ? 'cursor-not-allowed opacity-50' : '',
              ].join(' ')}
            >
              {opt.recommended && (
                <span className="absolute -top-2.5 right-3 rounded-full bg-accent px-2 py-0.5 text-[10px] font-bold tracking-wide text-white uppercase">
                  Recommended
                </span>
              )}
              <div className="mb-3 flex items-center justify-between gap-2">
                <span className="text-sm font-bold text-white">{opt.title}</span>
                <span
                  className={[
                    'flex h-4 w-4 items-center justify-center rounded-full border',
                    active ? 'border-accent bg-accent' : 'border-white/25',
                  ].join(' ')}
                >
                  {active && <span className="h-1.5 w-1.5 rounded-full bg-white" />}
                </span>
              </div>
              <p className="text-xs leading-relaxed text-muted">{opt.description}</p>
            </motion.button>
          )
        })}
      </div>
    </section>
  )
}

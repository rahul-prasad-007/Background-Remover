import { motion } from 'framer-motion'
import { Loader2, Lock, Wand2 } from 'lucide-react'

interface ProcessButtonProps {
  disabled?: boolean
  loading?: boolean
  onClick: () => void
}

export function ProcessButton({ disabled, loading, onClick }: ProcessButtonProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="container-app mt-7 flex flex-col items-center"
    >
      <button
        type="button"
        disabled={disabled || loading}
        onClick={onClick}
        className="inline-flex w-full max-w-md items-center justify-center gap-2 rounded-2xl bg-accent px-8 py-4 text-base font-bold text-white shadow-[0_14px_40px_rgba(59,130,246,0.4)] transition enabled:hover:scale-[1.015] enabled:hover:bg-[#2563eb] disabled:cursor-not-allowed disabled:opacity-45"
      >
        {loading ? <Loader2 className="h-5 w-5 animate-spin" /> : <Wand2 className="h-5 w-5" />}
        Process Image
      </button>
      <p className="mt-3 inline-flex items-center gap-1.5 text-center text-xs text-muted">
        <Lock className="h-3.5 w-3.5" />
        Your images are safe and automatically deleted after processing.
      </p>
    </motion.div>
  )
}

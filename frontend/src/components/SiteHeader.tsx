import { Lock, Sparkles } from 'lucide-react'

export function SiteHeader() {
  return (
    <header className="container-app flex items-center justify-between gap-4 pt-6 pb-2 sm:pt-8">
      <div className="flex items-center gap-2.5">
        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-accent/15 ring-1 ring-accent/30">
          <Sparkles className="h-4 w-4 text-accent" strokeWidth={2.25} />
        </div>
        <p className="text-[15px] font-bold tracking-tight text-white sm:text-base">
          AI Image <span className="text-accent">Enhancer</span>
        </p>
      </div>

      <div className="inline-flex items-center gap-1.5 rounded-full border border-success/25 bg-success-soft px-3 py-1.5 text-[11px] font-semibold text-success sm:text-xs">
        <Lock className="h-3 w-3" />
        <span>100% Free • No Sign Up</span>
      </div>
    </header>
  )
}

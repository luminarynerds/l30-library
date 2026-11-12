/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { ArrowLeft, Settings2 } from 'lucide-react'

interface ReaderToolbarProps {
  title: string
  percent: number
  showPercent: boolean
  onBack: () => void
  onOpenSettings: () => void
}

/**
 * Slim, calm top bar for the reader. No countdowns, no urgency — just where you
 * are, a way out, and reading controls.
 */
export default function ReaderToolbar({ title, percent, showPercent, onBack, onOpenSettings }: ReaderToolbarProps) {
  return (
    <header className="flex items-center gap-3 px-3 sm:px-4 h-14 shrink-0 border-b border-black/10 dark:border-white/10 bg-lsc-cream/95 dark:bg-earth-900/95 backdrop-blur">
      <button
        type="button"
        onClick={onBack}
        className="inline-flex items-center justify-center w-11 h-11 -ml-1 rounded-lg text-lsc-dark dark:text-lsc-cream hover:bg-black/5 dark:hover:bg-white/10 focus:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose"
        aria-label="Back to my books"
      >
        <ArrowLeft className="w-5 h-5" aria-hidden="true" />
      </button>

      <h1 className="flex-1 min-w-0 truncate text-sm sm:text-base font-medium text-lsc-dark dark:text-lsc-cream">
        {title}
      </h1>

      {showPercent && (
        <span className="shrink-0 tabular-nums text-xs sm:text-sm text-lsc-dark/70 dark:text-lsc-cream/70" aria-live="polite">
          {percent}%
        </span>
      )}

      <button
        type="button"
        onClick={onOpenSettings}
        className="inline-flex items-center justify-center w-11 h-11 rounded-lg text-lsc-dark dark:text-lsc-cream hover:bg-black/5 dark:hover:bg-white/10 focus:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose"
        aria-label="Reading settings"
      >
        <Settings2 className="w-5 h-5" aria-hidden="true" />
      </button>
    </header>
  )
}

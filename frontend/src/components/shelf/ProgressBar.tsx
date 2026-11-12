/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'

interface ProgressBarProps {
  percent: number
  currentPage?: number | null
  totalPages?: number | null
  onPageSubmit?: (page: number) => void
}

export default function ProgressBar({ percent, currentPage, totalPages, onPageSubmit }: ProgressBarProps) {
  const [editing, setEditing] = useState(false)
  const [pageInput, setPageInput] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const page = parseInt(pageInput, 10)
    if (page > 0 && onPageSubmit) {
      onPageSubmit(page)
      setEditing(false)
      setPageInput('')
    }
  }

  const label =
    currentPage && totalPages
      ? `pg ${currentPage} / ${totalPages} (${percent}%)`
      : percent > 0
        ? `~${percent}%`
        : 'Tap to log your first page'

  if (editing) {
    return (
      <form onSubmit={handleSubmit} className="flex items-center gap-2 mt-2">
        <label htmlFor="page-input" className="sr-only">Current page number</label>
        <input
          id="page-input"
          type="number"
          inputMode="numeric"
          min={1}
          max={totalPages ?? undefined}
          value={pageInput}
          onChange={(e) => setPageInput(e.target.value)}
          placeholder={currentPage ? `After pg ${currentPage}...` : 'Page #'}
          autoFocus
          className="w-24 text-sm rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream px-2.5 py-1.5 focus:outline-none focus:ring-2 focus:ring-lsc-rose/50"
        />
        <button
          type="submit"
          className="text-xs font-medium px-2.5 py-1.5 rounded-lg bg-lsc-rose text-white hover:bg-lsc-rose/90 transition-colors"
        >
          Save
        </button>
        <button
          type="button"
          onClick={() => setEditing(false)}
          className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 hover:text-lsc-dark dark:hover:text-lsc-cream transition-colors"
        >
          Cancel
        </button>
      </form>
    )
  }

  return (
    <button
      onClick={() => onPageSubmit && setEditing(true)}
      className="w-full mt-2 group text-left"
      aria-label={`Reading progress: ${label}. Click to update.`}
    >
      {/* Bar track */}
      <div className="w-full h-2.5 bg-earth-200 dark:bg-earth-700 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full bg-gradient-to-r from-emerald-500 to-teal-500 transition-all duration-500 motion-reduce:transition-none"
          style={{ width: `${Math.min(percent, 100)}%` }}
        />
      </div>
      {/* Label */}
      <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 mt-1 block group-hover:text-lsc-rose dark:group-hover:text-lsc-rose-light transition-colors">
        {label}
      </span>
    </button>
  )
}

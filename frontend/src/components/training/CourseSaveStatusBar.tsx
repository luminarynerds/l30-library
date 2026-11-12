/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useState } from 'react'
import { Loader2, AlertCircle, Check, RotateCcw } from 'lucide-react'

export type CourseSaveStatus =
  | 'idle'
  | 'writing'
  | 'saving'
  | 'saved'
  | 'failed-retry'
  | 'validation-error'

interface Props {
  status: CourseSaveStatus
  lastSavedAt: Date | null
  errorMessage?: string | undefined
  onManualSave: () => void
  paused: boolean
  onTogglePause: () => void
}

function formatRelative(date: Date, now: Date): string {
  const seconds = Math.floor((now.getTime() - date.getTime()) / 1000)
  if (seconds < 10) return 'just now'
  if (seconds < 60) return `${seconds} seconds ago`
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes} minute${minutes === 1 ? '' : 's'} ago`
  const hours = Math.floor(minutes / 60)
  return `${hours} hour${hours === 1 ? '' : 's'} ago`
}

function formatAbsolute(date: Date): string {
  return date.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })
}

export default function CourseSaveStatusBar({
  status,
  lastSavedAt,
  errorMessage,
  onManualSave,
  paused,
  onTogglePause,
}: Props) {
  const [now, setNow] = useState(() => new Date())

  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 30_000)
    return () => clearInterval(id)
  }, [])

  let message: string
  let icon: React.ReactNode = null
  let colorClass: string

  if (status === 'writing') {
    message = 'Writing...'
    colorClass = 'text-lsc-dark/70 dark:text-lsc-cream/70'
    icon = <Loader2 className="w-3.5 h-3.5 motion-safe:animate-spin" aria-hidden="true" />
  } else if (status === 'saving') {
    message = 'Saving…'
    colorClass = 'text-lsc-dark/70 dark:text-lsc-cream/70'
    icon = <Loader2 className="w-3.5 h-3.5 motion-safe:animate-spin" aria-hidden="true" />
  } else if (status === 'failed-retry') {
    message = 'Last save failed – retrying'
    colorClass = 'text-status-warning-700 dark:text-status-warning-300'
    icon = <AlertCircle className="w-3.5 h-3.5" aria-hidden="true" />
  } else if (status === 'validation-error') {
    message = `${errorMessage ?? 'Validation error'} – fix to continue`
    colorClass = 'text-status-danger-700 dark:text-status-danger-300'
    icon = <AlertCircle className="w-3.5 h-3.5" aria-hidden="true" />
  } else if (lastSavedAt) {
    message = `Saved ${formatAbsolute(lastSavedAt)} – ${formatRelative(lastSavedAt, now)}`
    colorClass = 'text-lsc-dark/60 dark:text-lsc-cream/60'
    icon = <Check className="w-3.5 h-3.5" aria-hidden="true" />
  } else {
    message = 'Not saved yet'
    colorClass = 'text-lsc-dark/50 dark:text-lsc-cream/50'
  }

  return (
    <div className="flex items-center gap-2 text-sm">
      <span
        data-testid="course-save-status"
        role="status"
        aria-live="polite"
        className={`inline-flex items-center gap-1.5 ${colorClass}`}
      >
        {icon}
        <span>{message}</span>
      </span>

      {status === 'failed-retry' && (
        <button
          type="button"
          onClick={onManualSave}
          className="
            inline-flex items-center gap-1 text-sm font-medium
            text-status-warning-700 dark:text-status-warning-300
            underline underline-offset-2
            hover:no-underline
            focus:outline-none focus:ring-2 focus:ring-lsc-rose rounded
          "
        >
          <RotateCcw className="w-3 h-3" aria-hidden="true" />
          Retry
        </button>
      )}

      <details className="relative ml-1">
        <summary
          className="
            list-none cursor-pointer select-none
            text-lsc-dark/40 dark:text-lsc-cream/40
            hover:text-lsc-dark/70 dark:hover:text-lsc-cream/70
            focus:outline-none focus:ring-2 focus:ring-lsc-rose rounded
            text-base leading-none
          "
          aria-label="Autosave options"
        >
          &#8943;
        </summary>
        <div className="
          absolute right-0 top-full mt-1 z-10
          bg-lsc-white dark:bg-earth-800
          border border-lsc-border dark:border-earth-700
          rounded shadow-md min-w-[10rem]
          p-1
        ">
          <button
            type="button"
            onClick={onTogglePause}
            aria-pressed={paused}
            className="
              w-full text-left px-3 py-2 text-sm rounded
              text-lsc-dark dark:text-lsc-cream
              hover:bg-lsc-cream dark:hover:bg-earth-700
              focus:outline-none focus:ring-2 focus:ring-lsc-rose
            "
          >
            {paused ? 'Resume autosave' : 'Pause autosave'}
          </button>
        </div>
      </details>
    </div>
  )
}

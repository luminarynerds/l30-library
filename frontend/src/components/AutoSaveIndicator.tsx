/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Check, Save, AlertCircle, Loader2 } from 'lucide-react'
import { AutoSaveStatus } from '../hooks/useAutoSave'

interface AutoSaveIndicatorProps {
  status: AutoSaveStatus
  lastSaved: Date | null
  error?: Error | null
  className?: string
  disabled?: boolean
}

export default function AutoSaveIndicator({
  status,
  lastSaved,
  error,
  className = '',
  disabled = false,
}: AutoSaveIndicatorProps): React.ReactElement {
  const formatTime = (date: Date): string => {
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffSecs = Math.floor(diffMs / 1000)
    const diffMins = Math.floor(diffSecs / 60)

    if (diffSecs < 10) return 'just now'
    if (diffSecs < 60) return `${diffSecs} seconds ago`
    if (diffMins === 1) return '1 minute ago'
    if (diffMins < 60) return `${diffMins} minutes ago`

    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }

  if (disabled) {
    return (
      <div
        className={`flex items-center gap-2 text-sm text-lsc-dark/50 dark:text-lsc-cream/50 ${className}`}
        role="status"
        aria-live="polite"
      >
        <span>Enter a title to save</span>
      </div>
    )
  }

  if (status === 'idle' && !lastSaved) {
    return <div className={`text-sm text-lsc-dark/70 dark:text-lsc-cream/70 ${className}`} />
  }

  return (
    <div className={`flex items-center gap-2 text-sm ${className}`} role="status" aria-live="polite">
      {status === 'saving' && (
        <>
          <Loader2 className="w-4 h-4 motion-safe:animate-spin text-earth-600" aria-hidden="true" />
          <span className="text-lsc-rose dark:text-lsc-rose-light">Saving...</span>
        </>
      )}

      {status === 'saved' && lastSaved && (
        <>
          <Check className="w-4 h-4 text-status-success-600 dark:text-status-success-400" aria-hidden="true" />
          <span className="text-status-success-700 dark:text-status-success-300">
            Saved {formatTime(lastSaved)}
          </span>
        </>
      )}

      {status === 'error' && (
        <>
          <AlertCircle className="w-4 h-4 text-status-danger-500" aria-hidden="true" />
          <span className="text-status-danger-600 dark:text-status-danger-400">
            {error?.message || 'Failed to save'}
          </span>
        </>
      )}

      {status === 'idle' && lastSaved && (
        <>
          <Save className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" aria-hidden="true" />
          <span className="text-lsc-dark/70 dark:text-lsc-cream/70">
            Last saved {formatTime(lastSaved)}
          </span>
        </>
      )}
    </div>
  )
}

/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useState } from 'react'
import type { FloorSocketStatus } from '@/hooks/useFloorViewSocket'
import { UNDO_WINDOW_MS } from './model'

export function SocketIndicator({ status }: { status: FloorSocketStatus }) {
  if (status === 'live') {
    return (
      <span className="flex items-center gap-1.5 text-xs text-status-success-700 dark:text-status-success-400">
        <span className="w-2 h-2 rounded-full bg-status-success-500 motion-safe:animate-pulse" />
        Live
      </span>
    )
  }
  if (status === 'connecting') {
    return (
      <span className="flex items-center gap-1.5 text-xs text-lsc-dark/60 dark:text-lsc-cream/60">
        <span className="w-2 h-2 rounded-full bg-lsc-dark/30 dark:bg-lsc-cream/30" />
        Connecting…
      </span>
    )
  }
  if (status === 'fallback') {
    return (
      <span className="flex items-center gap-1.5 text-xs text-status-warning-700 dark:text-status-warning-400" title="Live updates unavailable; polling every 30s">
        <span className="w-2 h-2 rounded-full bg-status-warning-500" />
        Polling
      </span>
    )
  }
  return null
}

export function UndoEndSessionToast({ toastId, sessionId, patronName, onUndo }: {
  toastId: string
  sessionId: number
  patronName: string | null
  onUndo: (sessionId: number, toastId: string) => void
}) {
  const [secondsLeft, setSecondsLeft] = useState(Math.ceil(UNDO_WINDOW_MS / 1000))
  useEffect(() => {
    if (secondsLeft <= 0) return
    const t = setTimeout(() => setSecondsLeft(s => s - 1), 1000)
    return () => clearTimeout(t)
  }, [secondsLeft])
  return (
    <div className="flex items-center gap-3">
      <div className="text-sm">
        <div className="font-medium text-lsc-dark dark:text-lsc-cream">Session ended</div>
        {patronName && (
          <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{patronName}</div>
        )}
      </div>
      <button
        onClick={() => onUndo(sessionId, toastId)}
        disabled={secondsLeft <= 0}
        className="px-3 py-1 text-xs rounded-lg bg-lsc-rose text-white hover:bg-lsc-rose/90 disabled:opacity-50 whitespace-nowrap"
      >
        Undo ({secondsLeft}s)
      </button>
    </div>
  )
}

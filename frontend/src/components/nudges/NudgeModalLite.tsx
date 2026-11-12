/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect } from 'react'
import { X, ArrowRight } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useNudges } from '@/contexts/NudgeContext'
import type { ActiveNudge } from '@/contexts/NudgeContext'

interface Props {
  nudge: ActiveNudge
}

export function NudgeModalLite({ nudge }: Props) {
  const { dismissNudge, actOnNudge, markShown } = useNudges()
  const navigate = useNavigate()

  useEffect(() => {
    markShown(nudge.id)
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') dismissNudge(nudge.id)
    }
    document.addEventListener('keydown', handleEsc)
    return () => document.removeEventListener('keydown', handleEsc)
  }, [nudge.id, markShown, dismissNudge])

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      onClick={() => dismissNudge(nudge.id)}
      onKeyDown={(e) => { if (e.key === 'Escape') dismissNudge(nudge.id) }}
      role="presentation"
    >
      <div className="absolute inset-0 bg-black/20" />
      {/* eslint-disable-next-line jsx-a11y/click-events-have-key-events */}
      <div
        className="relative bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg p-6 max-w-md w-full"
        onClick={e => e.stopPropagation()}
      >
        <button
          onClick={() => dismissNudge(nudge.id)}
          className="absolute top-3 right-3 p-1 text-earth-600 hover:text-earth-600"
          aria-label="Close"
        >
          <X className="w-5 h-5" />
        </button>
        {nudge.content.title && (
          <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-2">
            {nudge.content.title}
          </h2>
        )}
        <p className="text-sm text-lsc-dark/80 dark:text-lsc-cream/90">{nudge.content.body}</p>
        {nudge.content.cta_label && (
          <button
            onClick={() => {
              actOnNudge(nudge.id)
              if (nudge.content.cta_route) navigate(nudge.content.cta_route)
            }}
            className="mt-4 inline-flex items-center gap-1 px-4 py-2 bg-lsc-rose text-white text-sm font-medium rounded-lg hover:bg-lsc-rose/90 transition-colors"
          >
            {nudge.content.cta_label}
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        )}
      </div>
    </div>
  )
}

/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect } from 'react'
import { X, ArrowRight, Lightbulb } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useNudges } from '@/contexts/NudgeContext'
import type { ActiveNudge } from '@/contexts/NudgeContext'

interface Props {
  nudge: ActiveNudge
}

export function NudgePanel({ nudge }: Props) {
  const { dismissNudge, actOnNudge, markShown } = useNudges()
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)

  useEffect(() => { markShown(nudge.id) }, [nudge.id, markShown])

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="fixed bottom-6 right-6 z-40 w-10 h-10 bg-lsc-rose text-white rounded-full shadow-lg flex items-center justify-center hover:bg-lsc-rose/90 transition-colors"
        aria-label="View tip"
      >
        <Lightbulb className="w-5 h-5" />
      </button>
    )
  }

  return (
    <div className="fixed bottom-0 right-0 z-50 w-80 max-h-[60vh] bg-lsc-white dark:bg-earth-800 shadow-lg border-l border-t border-lsc-border dark:border-earth-700 rounded-tl-xl p-5">
      <div className="flex items-start justify-between mb-3">
        <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
          {nudge.content.title || 'Tip'}
        </h3>
        <button
          onClick={() => dismissNudge(nudge.id)}
          className="p-1 text-earth-600 hover:text-earth-600"
          aria-label="Close"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
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
  )
}

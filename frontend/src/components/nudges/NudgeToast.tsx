/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useState } from 'react'
import { X, ArrowRight } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useNudges } from '@/contexts/NudgeContext'
import type { ActiveNudge } from '@/contexts/NudgeContext'

interface Props {
  nudge: ActiveNudge
}

export function NudgeToast({ nudge }: Props) {
  const { dismissNudge, actOnNudge, markShown } = useNudges()
  const navigate = useNavigate()
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    markShown(nudge.id)
    requestAnimationFrame(() => setVisible(true))
    const timer = setTimeout(() => dismissNudge(nudge.id), 8000)
    return () => clearTimeout(timer)
  }, [nudge.id, markShown, dismissNudge])

  return (
    <div
      className={`fixed bottom-6 right-6 z-50 max-w-sm bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg border border-lsc-border dark:border-earth-700 p-4 transition-all duration-300 motion-reduce:transition-none ${visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'}`}
      role="status"
      aria-live="polite"
    >
      <button
        onClick={() => dismissNudge(nudge.id)}
        className="absolute top-2 right-2 p-1 text-earth-600 hover:text-earth-600 dark:hover:text-earth-300"
        aria-label="Dismiss"
      >
        <X className="w-4 h-4" />
      </button>
      <p className="text-sm text-lsc-dark dark:text-lsc-cream pr-6">{nudge.content.body}</p>
      {nudge.content.cta_label && (
        <button
          onClick={() => {
            actOnNudge(nudge.id)
            if (nudge.content.cta_route) navigate(nudge.content.cta_route)
          }}
          className="mt-2 inline-flex items-center gap-1 text-sm font-medium text-lsc-rose hover:text-lsc-rose/80"
        >
          {nudge.content.cta_label}
          <ArrowRight className="w-3.5 h-3.5" />
        </button>
      )}
    </div>
  )
}

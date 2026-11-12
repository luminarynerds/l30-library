/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Trophy, X } from 'lucide-react'
import type { ReadingMilestone } from '@/api/domains/content/reading-milestones-api'

interface MilestoneCardProps {
  milestone: ReadingMilestone
  onDismiss?: (id: number) => void
}

export default function MilestoneCard({ milestone, onDismiss }: MilestoneCardProps) {
  return (
    <div className="relative bg-gradient-to-r from-status-warning-50 to-orange-50 dark:from-status-warning-900/30 dark:to-orange-950/30 rounded-xl border border-status-warning-200/60 dark:border-status-warning-800/40 p-3">
      <div className="flex items-start gap-2.5">
        <div className="shrink-0 w-8 h-8 rounded-full bg-status-warning-100 dark:bg-status-warning-900/50 flex items-center justify-center">
          <Trophy className="w-4 h-4 text-status-warning-600 dark:text-status-warning-400" aria-hidden="true" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
            {milestone.title}
          </p>
          {milestone.description && (
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 mt-0.5">
              {milestone.description}
            </p>
          )}
          <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 mt-1">
            {new Date(milestone.earned_at).toLocaleDateString()}
          </p>
        </div>
        {onDismiss && (
          <button
            onClick={() => onDismiss(milestone.id)}
            aria-label={`Dismiss milestone: ${milestone.title}`}
            className="shrink-0 text-lsc-dark/30 dark:text-lsc-cream/60 hover:text-lsc-dark/70 dark:hover:text-lsc-cream/60 transition-colors"
          >
            <X className="w-4 h-4" aria-hidden="true" />
          </button>
        )}
      </div>
    </div>
  )
}

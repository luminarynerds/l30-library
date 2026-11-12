/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { ChevronDown, ChevronUp, Activity } from 'lucide-react'
import { useReadingActivity } from '@/hooks/useReadingActivity'
import { useReadingMilestones } from '@/hooks/useReadingMilestones'
import { useShelfPreferences } from '@/hooks/useShelfPreferences'
import MilestoneCard from './MilestoneCard'
import { t } from '@/i18n'

const PAGE_SIZE = 5

export default function ActivityFeed() {
  const [collapsed, setCollapsed] = useState(false)
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE)
  const { activities, total, isLoading } = useReadingActivity(visibleCount)
  const { milestones, handleDismiss } = useReadingMilestones()
  const { preferences } = useShelfPreferences()

  const undismissedMilestones = milestones.filter((m) => !m.dismissed)
  const hasContent = activities.length > 0 || undismissedMilestones.length > 0

  if (!hasContent && !isLoading) {
    return (
      <section aria-label={t('aria.shelf.readingActivity')} className="mb-8">
        <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-3 flex items-center gap-2">
          <Activity className="w-5 h-5" aria-hidden="true" />
          Activity
        </h2>
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border/60 dark:border-earth-700/80 p-6 text-center">
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60">
            Your reading activity will appear here as you track your progress.
          </p>
        </div>
      </section>
    )
  }

  return (
    <section aria-label={t('aria.shelf.readingActivity')} className="mb-8">
      {/* Collapsible header */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="flex items-center gap-2 mb-3 group"
        aria-expanded={!collapsed}
      >
        <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
          <Activity className="w-5 h-5" aria-hidden="true" />
          Activity & Milestones
        </h2>
        {collapsed ? (
          <ChevronDown className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/60 group-hover:text-lsc-dark dark:group-hover:text-lsc-cream transition-colors" aria-hidden="true" />
        ) : (
          <ChevronUp className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/60 group-hover:text-lsc-dark dark:group-hover:text-lsc-cream transition-colors" aria-hidden="true" />
        )}
      </button>

      {!collapsed && (
        <div className="space-y-3">
          {/* Milestones (always shown) */}
          {undismissedMilestones.map((m) => (
            <MilestoneCard key={m.id} milestone={m} onDismiss={handleDismiss} />
          ))}

          {/* Streak display (opt-in) */}
          {preferences.show_reading_activity && activities.length > 0 && (
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border/40 dark:border-earth-700/60 px-3 py-2">
              <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60">
                {activities.length} reading {activities.length === 1 ? 'entry' : 'entries'} logged recently
              </p>
            </div>
          )}

          {/* Activity timeline */}
          {activities.length > 0 && (
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border/60 dark:border-earth-700/80 divide-y divide-lsc-border/30 dark:divide-earth-700/50">
              {activities.map((a) => (
                <div key={a.id} className="px-4 py-2.5 flex items-center justify-between">
                  <p className="text-sm text-lsc-dark/80 dark:text-lsc-cream/80">
                    {a.summary}
                  </p>
                  <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 shrink-0 ml-3">
                    {new Date(a.occurred_at).toLocaleDateString()}
                  </span>
                </div>
              ))}
            </div>
          )}

          {/* Show more */}
          {total > visibleCount && (
            <button
              onClick={() => setVisibleCount((c) => c + PAGE_SIZE)}
              className="text-sm text-lsc-rose dark:text-lsc-rose-light hover:underline"
            >
              Show more
            </button>
          )}
        </div>
      )}
    </section>
  )
}

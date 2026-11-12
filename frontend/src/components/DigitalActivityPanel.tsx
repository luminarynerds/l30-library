/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import {
  ChevronDown, ChevronUp, BookOpen, Music, Clock, Activity,
} from 'lucide-react'
import { clsx } from '@/utils/helpers'
import { useDigitalActivity } from '@/hooks/useDigitalActivity'

function formatDate(iso: string): string {
  const d = new Date(iso + 'T00:00:00')
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

function daysUntil(iso: string): number {
  const now = new Date()
  const due = new Date(iso + 'T00:00:00')
  return Math.max(0, Math.ceil((due.getTime() - now.getTime()) / 86_400_000))
}

export default function DigitalActivityPanel(): React.ReactElement | null {
  const { activity, isLoading, isAuthenticated } = useDigitalActivity()
  const [expanded, setExpanded] = useState(true)

  if (!isAuthenticated) return null
  if (isLoading) {
    return (
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-5 motion-safe:animate-pulse">
        <div className="h-6 w-48 bg-lsc-cream dark:bg-earth-700 rounded" />
      </div>
    )
  }
  if (!activity) return null

  const hasCheckouts = activity.active_checkouts.length > 0
  const hasQuotas = activity.download_quotas.length > 0
  const hasRecent = activity.recent_services.length > 0
  if (!hasCheckouts && !hasQuotas && !hasRecent) return null

  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm">
      <button
        onClick={() => setExpanded(prev => !prev)}
        className="w-full p-5 flex items-center gap-3 text-left"
        aria-expanded={expanded}
        aria-controls="digital-activity-details"
      >
        <div className="w-10 h-10 rounded-xl bg-lsc-cream dark:bg-lsc-brown flex items-center justify-center flex-shrink-0">
          <Activity className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
        </div>
        <div className="flex-1 min-w-0">
          <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
            My Digital Activity
          </h2>
          {!expanded && hasCheckouts && (
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-0.5">
              {activity.active_checkouts.length} active checkout{activity.active_checkouts.length !== 1 ? 's' : ''}
              {hasQuotas && activity.download_quotas.map(q =>
                ` \u00b7 ${q.used}/${q.limit} ${q.service} downloads`
              ).join('')}
            </p>
          )}
        </div>
        <div className="flex-shrink-0 text-lsc-dark/70 dark:text-lsc-cream/70">
          {expanded
            ? <ChevronUp className="w-5 h-5" aria-hidden="true" />
            : <ChevronDown className="w-5 h-5" aria-hidden="true" />}
        </div>
      </button>

      <div id="digital-activity-details" hidden={!expanded}>
        {expanded && (
          <div className="px-5 pb-5 space-y-4 border-t border-lsc-border dark:border-earth-700 pt-4">

            {/* Active Checkouts */}
            {hasCheckouts && (
              <div>
                <h3 className="text-xs font-semibold text-lsc-dark dark:text-lsc-cream/90 uppercase tracking-wide mb-2">
                  Active Checkouts
                </h3>
                <ul className="space-y-2">
                  {activity.active_checkouts.map(co => {
                    const days = daysUntil(co.due_date)
                    const urgent = days <= 2
                    return (
                      <li key={`${co.service}-${co.title}`} className="flex items-start gap-3">
                        <BookOpen className="w-4 h-4 text-lsc-rose dark:text-lsc-rose-light flex-shrink-0 mt-0.5" aria-hidden="true" />
                        <div className="flex-1 min-w-0">
                          <p className="text-sm text-lsc-dark dark:text-lsc-cream truncate">
                            {co.title}
                          </p>
                          <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                            {co.service}
                          </p>
                        </div>
                        <span className={clsx(
                          'text-xs font-medium whitespace-nowrap',
                          urgent
                            ? 'text-status-danger-600 dark:text-status-danger-400'
                            : 'text-lsc-dark/70 dark:text-lsc-cream/70',
                        )}>
                          {days === 0 ? 'Due today' : `Due ${formatDate(co.due_date)}`}
                        </span>
                      </li>
                    )
                  })}
                </ul>
              </div>
            )}

            {/* Download Quotas */}
            {hasQuotas && (
              <div>
                <h3 className="text-xs font-semibold text-lsc-dark dark:text-lsc-cream/90 uppercase tracking-wide mb-2">
                  Download Limits
                </h3>
                {activity.download_quotas.map(q => {
                  const pct = Math.round((q.used / q.limit) * 100)
                  return (
                    <div key={q.service} className="space-y-1.5">
                      <div className="flex items-center gap-2">
                        <Music className="w-4 h-4 text-lsc-rose dark:text-lsc-rose-light flex-shrink-0" aria-hidden="true" />
                        <span className="text-sm text-lsc-dark dark:text-lsc-cream flex-1">
                          {q.service}
                        </span>
                        <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                          {q.used} of {q.limit} this {q.period}
                        </span>
                      </div>
                      <div
                        className="h-2 bg-lsc-cream dark:bg-earth-700 rounded-full overflow-hidden"
                        role="progressbar"
                        aria-valuenow={q.used}
                        aria-valuemin={0}
                        aria-valuemax={q.limit}
                        aria-label={`${q.service}: ${q.used} of ${q.limit} used`}
                      >
                        <div
                          className={clsx(
                            'h-full rounded-full transition-all',
                            pct >= 80 ? 'bg-status-danger-500' : pct >= 60 ? 'bg-lsc-rose' : 'bg-lsc-green',
                          )}
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                    </div>
                  )
                })}
              </div>
            )}

            {/* Recently Used */}
            {hasRecent && (
              <div>
                <h3 className="text-xs font-semibold text-lsc-dark dark:text-lsc-cream/90 uppercase tracking-wide mb-2">
                  Recently Used
                </h3>
                <div className="flex flex-wrap gap-2">
                  {activity.recent_services.map(s => (
                    <span key={s.service} className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium bg-lsc-cream dark:bg-lsc-brown/40 text-lsc-dark/80 dark:text-lsc-cream/80">
                      <Clock className="w-3 h-3" aria-hidden="true" />
                      {s.service} &middot; {formatDate(s.last_used)}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect } from 'react'
import { BookOpen, RotateCcw, Star, Bookmark, Heart, List, ChevronDown, Clock } from 'lucide-react'
import { clsx } from '@/utils/helpers'
import { useAuth } from '@/contexts/AuthContext'
import { fetchApi } from '@/lib/api-client'
import { getCurrentLocale } from '@/i18n'

interface ActivityEvent {
  type: string
  date: string
  detail: string
}

interface MyActivityResponse {
  events: ActivityEvent[]
}

const DEFAULT_EVENT_CONFIG = { icon: BookOpen, color: 'text-status-info-500 dark:text-status-info-400' }
const EVENT_CONFIG: Record<string, { icon: typeof BookOpen; color: string }> = {
  checkout: { icon: BookOpen, color: 'text-status-info-500 dark:text-status-info-400' },
  return: { icon: RotateCcw, color: 'text-status-success-600 dark:text-status-success-400' },
  rated: { icon: Star, color: 'text-lsc-rose dark:text-lsc-rose-light' },
  shelf: { icon: Bookmark, color: 'text-category-500 dark:text-category-400' },
  favorite: { icon: Heart, color: 'text-status-danger-500 dark:text-status-danger-400' },
  list: { icon: List, color: 'text-teal-500 dark:text-teal-400' },
}

interface ReadingTimelineProps {
  itemId: number
}

export function ReadingTimeline({ itemId }: ReadingTimelineProps): React.ReactElement | null {
  const { user } = useAuth()
  const [events, setEvents] = useState<ActivityEvent[]>([])
  const [isOpen, setIsOpen] = useState(false)
  const [isLoading, setIsLoading] = useState(false)

  useEffect(() => {
    if (!user || !itemId) {
      setEvents([])
      return
    }
    let cancelled = false
    setIsLoading(true)
    fetchApi<MyActivityResponse>(`/catalog/items/${itemId}/my-activity`)
      .then(data => {
        if (!cancelled) setEvents(data.events)
      })
      .catch(() => {
        if (!cancelled) setEvents([])
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false)
      })
    return () => { cancelled = true }
  }, [user, itemId])

  if (!user || isLoading || events.length === 0) return null

  return (
    <div className="px-6 md:px-8 pb-4">
      <details
        className="group"
        open={isOpen}
        onToggle={(e) => setIsOpen((e.target as HTMLDetailsElement).open)}
      >
        <summary className="flex items-center gap-2 cursor-pointer text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream select-none">
          <Clock className="w-4 h-4 text-lsc-rose" aria-hidden="true" />
          Your history with this title
          <span className="text-xs text-lsc-dark/50 dark:text-lsc-cream/50">({events.length})</span>
          <ChevronDown className="w-3 h-3 transition-transform group-open:rotate-180" aria-hidden="true" />
        </summary>
        <ul className="mt-3 space-y-3 pl-2" role="list">
          {events.map((event, idx) => {
            const config = EVENT_CONFIG[event.type] ?? DEFAULT_EVENT_CONFIG
            const Icon = config.icon
            return (
              <li key={idx} className="flex items-start gap-3 relative">
                {idx < events.length - 1 && (
                  <div
                    className="absolute left-[11px] top-6 bottom-0 w-px bg-lsc-border dark:bg-earth-700"
                    aria-hidden="true"
                  />
                )}
                <div className={clsx('flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center bg-lsc-cream dark:bg-earth-800 border border-lsc-border dark:border-earth-700 z-10')}>
                  <Icon className={clsx('w-3.5 h-3.5', config.color)} aria-hidden="true" />
                </div>
                <div className="flex-1 min-w-0 pt-0.5">
                  <p className="text-sm text-lsc-dark dark:text-lsc-cream">{event.detail}</p>
                  {event.date && (
                    <p className="text-xs text-lsc-dark/50 dark:text-lsc-cream/50 mt-0.5">
                      {new Date(event.date + 'T00:00:00').toLocaleDateString(getCurrentLocale(), { month: 'short', day: 'numeric', year: 'numeric' })}
                    </p>
                  )}
                </div>
              </li>
            )
          })}
        </ul>
      </details>
    </div>
  )
}

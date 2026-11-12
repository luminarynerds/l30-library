/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Upcoming Author Events Rail (indie landing)
 * Aggregate upcoming events across all indie authors.
 */

import { Link } from 'react-router-dom'
import { Calendar, ChevronRight } from 'lucide-react'
import type { UpcomingIndieEvent } from '@/api/indie-catalog-api'
import { getCurrentLocale } from '@/i18n'

function formatEventDate(iso: string): string {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleDateString(getCurrentLocale(), {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

export default function UpcomingEventsRail({
  events,
}: {
  events: UpcomingIndieEvent[]
}): React.ReactElement | null {
  if (!events || events.length === 0) return null

  return (
    <section aria-label="Upcoming indie author events">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-serif font-bold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
          <Calendar className="w-5 h-5 text-lsc-rose" aria-hidden="true" />
          Upcoming author events
        </h2>
        <Link
          to="/events"
          className="flex items-center gap-1 text-sm text-lsc-rose hover:underline"
        >
          All events <ChevronRight className="w-4 h-4" aria-hidden="true" />
        </Link>
      </div>
      <ul className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3" role="list">
        {events.map((event) => (
          <li key={event.id}>
            <Link
              to={`/events/${event.id}`}
              className="block bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-4 hover:shadow-md transition-shadow"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <h3 className="font-medium text-lsc-dark dark:text-lsc-cream line-clamp-2">
                    {event.title}
                  </h3>
                  {event.author_pen_name && (
                    <p className="text-xs text-lsc-rose mt-0.5">
                      with {event.author_pen_name}
                    </p>
                  )}
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                    {formatEventDate(event.start_time)}
                  </p>
                </div>
                {event.category && (
                  <span className="text-xs px-2 py-1 bg-lsc-cream dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 rounded shrink-0">
                    {event.category}
                  </span>
                )}
              </div>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  )
}

/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React from 'react'
import { Clock } from 'lucide-react'
import type { Event } from '@/api/api'

interface EventCardProps {
  event: Event
  onClick: () => void
  compact?: boolean
  locale: string
}

const EventCard = React.memo(function EventCard({ event, onClick, compact = false, locale }: EventCardProps) {
  const time = new Date(event.start_time).toLocaleTimeString(locale, {
    hour: 'numeric',
    minute: '2-digit',
  })

  if (compact) {
    return (
      <button
        onClick={onClick}
        className="w-full text-left p-1.5 rounded text-xs bg-lsc-cream dark:bg-lsc-dark hover:bg-lsc-border dark:hover:bg-lsc-rose border border-lsc-border dark:border-earth-700 transition-colors focus:outline-none focus:ring-2 focus:ring-lsc-rose"
        aria-label={`View event: ${event.title} at ${time}`}
      >
        <div className="font-semibold text-lsc-dark dark:text-lsc-cream truncate" title={event.title}>
          {event.title}
        </div>
        <div className="text-lsc-dark/70 dark:text-lsc-cream/70 flex items-center gap-1">
          <Clock className="w-3 h-3" aria-hidden="true" />
          {time}
        </div>
      </button>
    )
  }

  return (
    <button
      onClick={onClick}
      className="w-full text-left p-2 rounded-lg bg-lsc-cream dark:bg-lsc-dark hover:bg-lsc-border dark:hover:bg-lsc-rose/80 border border-lsc-border dark:border-earth-700 transition-colors focus:outline-none focus:ring-2 focus:ring-lsc-rose"
      aria-label={`View event: ${event.title} at ${time}`}
    >
      <div className="font-semibold text-sm text-lsc-dark dark:text-lsc-cream truncate" title={event.title}>
        {event.title}
      </div>
      <div className="text-lsc-dark/70 dark:text-lsc-cream/70 flex items-center gap-1 text-xs mt-1">
        <Clock className="w-3 h-3" aria-hidden="true" />
        {time}
      </div>
      {event.location && (
        <div className="text-lsc-dark/70 dark:text-lsc-cream/70 text-xs truncate mt-0.5" title={event.location}>
          {event.location}
        </div>
      )}
    </button>
  )
})

export default EventCard

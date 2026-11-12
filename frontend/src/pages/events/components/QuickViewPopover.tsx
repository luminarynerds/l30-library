/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Calendar, Clock, MapPin, Users } from 'lucide-react'
import { useTranslation } from '@/i18n/I18nContext'
import { formatTime, formatFullDate } from '@/pages/events/utils/formatters'
import type { Event } from '@/api/api'

export default function QuickViewPopover({ event, isVisible }: { event: Event; isVisible: boolean }): React.ReactElement {
  const { t } = useTranslation()

  return (
    <div
      role="tooltip"
      className={`absolute left-full top-0 ml-4 z-50 w-80 bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg border border-lsc-border dark:border-earth-700 p-4 hidden lg:block pointer-events-none transition-opacity duration-150 ${isVisible ? 'opacity-100' : 'opacity-0'}`}
    >
      {/* Event Image in Popover */}
      {event.image_url && (
        <div className="mb-3 rounded-lg overflow-hidden">
          <img
            src={event.image_url}
            alt={event.title}
            className="w-full h-32 object-cover"
          />
        </div>
      )}

      {/*
        Title is rendered as a non-heading element here: the EventCard already
        renders the same title as <h3>. Two headings (h3 + h4) with the same
        text in the same accessible region trips WCAG 1.3.1 (Info &
        Relationships). The popover is a tooltip preview, not a content
        section, so a styled <p> is the correct semantic.
      */}
      <p className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-2">
        {event.title}
      </p>

      <div className="space-y-1.5 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
        <p className="flex items-center gap-2">
          <Calendar aria-hidden="true" className="w-4 h-4 flex-shrink-0" />
          {formatFullDate(event.start_time)}
        </p>
        <p className="flex items-center gap-2">
          <Clock aria-hidden="true" className="w-4 h-4 flex-shrink-0" />
          {formatTime(event.start_time)}
          {event.end_time && ` - ${formatTime(event.end_time)}`}
        </p>
        {event.location && (
          <p className="flex items-center gap-2">
            <MapPin aria-hidden="true" className="w-4 h-4 flex-shrink-0" />
            {event.location}
          </p>
        )}
        {event.max_attendees !== null && (
          <p className="flex items-center gap-2">
            <Users aria-hidden="true" className="w-4 h-4 flex-shrink-0" />
            {event.spots_remaining === 0
              ? t('events.eventIsFull')
              : t('events.spotsOfTotal', { remaining: event.spots_remaining, total: event.max_attendees })}
          </p>
        )}
      </div>

      {event.description && (
        <p className="mt-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 line-clamp-3" title={event.description}>
          {event.description}
        </p>
      )}

      <p className="mt-3 text-xs text-lsc-rose dark:text-lsc-rose-light font-medium">
        {t('events.clickToViewDetails')}
      </p>
    </div>
  )
}

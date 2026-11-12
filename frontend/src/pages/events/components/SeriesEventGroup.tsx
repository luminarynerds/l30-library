/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { CalendarPlus, Clock, MapPin, Repeat } from 'lucide-react'
import { useTranslation } from '@/i18n/I18nContext'
import { formatTime, getDateLocale } from '@/pages/events/utils/formatters'
import type { Event } from '@/api/api'
import type { SeriesGroup } from '@/pages/events/utils/eventsPageUtils'

export default function SeriesEventGroup({
  group,
  onEventClick,
  onRegister,
  onRegisterSeries,
}: {
  group: SeriesGroup
  onEventClick: (event: Event) => void
  onRegister: (event: Event) => void
  onRegisterSeries: (group: SeriesGroup) => void
}): React.ReactElement {
  const { t } = useTranslation()
  const [isExpanded, setIsExpanded] = useState(false)
  const displayedEvents = isExpanded ? group.events : group.events.slice(0, 2)
  // Show "register for all" only when at least one occurrence actually takes
  // registrations — an all-drop-in series has nothing to register for.
  const canRegisterSeries = group.events.some((e) => e.registration_required)

  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border-2 border-dashed border-lsc-rose/30 dark:border-lsc-rose/40 overflow-hidden">
      {/* Series Header */}
      <div className="bg-gradient-to-r from-lsc-rose/5 to-status-warning-50/50 dark:from-lsc-rose/10 dark:to-earth-700/50 px-5 py-3 border-b border-lsc-border dark:border-earth-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Repeat className="w-5 h-5 text-lsc-rose" aria-hidden="true" />
            <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
              {group.series_name}
            </h3>
            <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-lsc-rose/20 text-lsc-rose dark:bg-lsc-rose/30 dark:text-lsc-rose-light">
              {t('events.eventsInSeries', { count: group.events.length })}
            </span>
          </div>
          <div className="flex items-center gap-3">
            {canRegisterSeries && (
              <button
                type="button"
                onClick={() => onRegisterSeries(group)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-lsc-rose text-white hover:bg-lsc-rose-dark focus:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose"
              >
                <CalendarPlus aria-hidden="true" className="w-3.5 h-3.5" />
                {t('events.registerForSeries', 'Register for all sessions')}
              </button>
            )}
            {group.events.length > 2 && (
              <button
                onClick={() => setIsExpanded(!isExpanded)}
                className="text-sm text-lsc-rose hover:text-lsc-rose/80 font-medium"
              >
                {isExpanded ? t('events.showLess') : t('events.showAll', { count: group.events.length })}
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Series Events */}
      <div className="divide-y divide-lsc-border/50 dark:divide-earth-600/50">
        {displayedEvents.map((event) => (
          <article
            key={event.id}
            className="flex items-center gap-4 p-4 hover:bg-lsc-cream/50 dark:hover:bg-earth-700/30 transition-colors"
          >
            <div className="w-12 h-12 flex-shrink-0 bg-lsc-cream dark:bg-earth-700 rounded-lg flex flex-col items-center justify-center">
              <span className="text-xs text-lsc-rose dark:text-lsc-rose-light font-medium">
                {new Date(event.start_time).toLocaleDateString(getDateLocale(), { month: 'short' })}
              </span>
              <span className="text-lg font-bold text-lsc-dark dark:text-lsc-cream">
                {new Date(event.start_time).getDate()}
              </span>
            </div>
            <div className="flex-1 min-w-0">
              <h4 className="font-medium text-lsc-dark dark:text-lsc-cream" title={event.title}>
                <button
                  type="button"
                  onClick={() => onEventClick(event)}
                  className="w-full text-left line-clamp-1 hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose rounded-sm"
                >
                  {event.title}
                </button>
              </h4>
              <div className="flex items-center gap-3 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                <span className="flex items-center gap-1">
                  <Clock aria-hidden="true" className="w-3 h-3" />
                  {formatTime(event.start_time)}
                </span>
                {event.location && (
                  <span className="flex items-center gap-1">
                    <MapPin aria-hidden="true" className="w-3 h-3" />
                    {event.location}
                  </span>
                )}
              </div>
            </div>
            {event.registration_required && (
              <button
                onClick={() => onRegister(event)}
                className="flex-shrink-0 px-3 py-1.5 rounded-lg text-xs font-medium bg-lsc-rose text-white hover:bg-lsc-rose/90"
              >
                {event.spots_remaining === 0 ? t('events.waitlist') : t('events.register')}
              </button>
            )}
          </article>
        ))}
      </div>
    </div>
  )
}

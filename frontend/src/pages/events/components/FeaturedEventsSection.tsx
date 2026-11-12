/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Calendar, Clock, Star, UserPlus } from 'lucide-react'
import { useTranslation } from '@/i18n/I18nContext'
import { getCategoryColorClasses, getCategoryDisplayName } from '@/pages/events/utils/eventCategoryColors'
import { formatTime, getDateLocale } from '@/pages/events/utils/formatters'
import type { Event } from '@/api/api'
import { useAccessibility } from '@/features/accessibility/hooks/useAccessibility'

export default function FeaturedEventsSection({
  events,
  onEventClick,
  onRegister,
}: {
  events: Event[]
  onEventClick: (event: Event) => void
  onRegister: (event: Event) => void
}): React.ReactElement | null {
  const { t } = useTranslation()
  const { settings } = useAccessibility()
  const featuredEvents = events.filter((e) => e.is_featured)

  if (featuredEvents.length === 0) return null

  return (
    <section className="mb-8" aria-label={t('events.featuredEvents')}>
      <div className="bg-gradient-to-r from-status-warning-50 via-status-warning-50/50 to-status-warning-50 dark:from-status-warning-900/20 dark:via-earth-800 dark:to-status-warning-900/20 rounded-xl p-6 border-2 border-status-warning-300/50 dark:border-status-warning-700/40">
        <div className="flex items-center gap-2 mb-4">
          <Star className="w-6 h-6 text-status-warning-500 fill-status-warning-500" aria-hidden="true" />
          <h2 className="text-xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
            {t('events.featuredEvents')}
          </h2>
        </div>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {featuredEvents.map((event) => (
            <article
              key={event.id}
              className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-md hover:shadow-lg transition-all border-l-4 border-status-warning-400"
              aria-label={t('events.featuredEventLabel', { title: event.title })}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-2">
                    {!settings.quietMode && (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-bold bg-status-warning-800 text-white">
                        <Star className="w-3 h-3" aria-hidden="true" />
                        {t('events.featured')}
                      </span>
                    )}
                    {!settings.quietMode && event.category && (
                      <span className={`text-xs px-2 py-0.5 rounded ${getCategoryColorClasses(event.category)}`}>
                        {getCategoryDisplayName(event.category)}
                      </span>
                    )}
                  </div>
                  <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-2" title={event.title}>
                    <button
                      type="button"
                      onClick={() => onEventClick(event)}
                      className="w-full text-left line-clamp-2 hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose rounded-sm"
                    >
                      {event.title}
                    </button>
                  </h3>
                  <div className="flex flex-wrap gap-2 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                    <span className="flex items-center gap-1">
                      <Calendar aria-hidden="true" className="w-3.5 h-3.5" />
                      {new Date(event.start_time).toLocaleDateString(getDateLocale(), { month: 'short', day: 'numeric' })}
                    </span>
                    <span className="flex items-center gap-1">
                      <Clock aria-hidden="true" className="w-3.5 h-3.5" />
                      {formatTime(event.start_time)}
                    </span>
                  </div>
                  {event.description && (
                    <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-2 line-clamp-2" title={event.description}>
                      {event.description}
                    </p>
                  )}
                </div>
              </div>
              {event.registration_required && (
                <button
                  onClick={() => onRegister(event)}
                  className="mt-3 w-full flex items-center justify-center gap-2 px-3 py-2 rounded-xl text-sm font-semibold bg-forest-800 hover:bg-forest-900 text-white transition-colors"
                >
                  <UserPlus aria-hidden="true" className="w-4 h-4" />
                  {event.spots_remaining === 0 ? t('events.waitlist') : t('events.register')}
                </button>
              )}
            </article>
          ))}
        </div>
      </div>
    </section>
  )
}

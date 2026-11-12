/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Zap } from 'lucide-react'
import { useTranslation } from '@/i18n/I18nContext'
import { isToday } from '@/pages/events/utils/eventsPageUtils'
import { formatTime } from '@/pages/events/utils/formatters'
import type { Event } from '@/api/api'
import { useAccessibility } from '@/features/accessibility/hooks/useAccessibility'

export default function HappeningNowSection({
  events,
  onEventClick,
  onRegister,
  embedded = false,
}: {
  events: Event[]
  onEventClick: (event: Event) => void
  onRegister: (event: Event) => void
  /** Rendered inside the merged "Today & this week" band: no own <section>, demoted heading. */
  embedded?: boolean
}): React.ReactElement | null {
  const { t } = useTranslation()
  const { settings } = useAccessibility()
  const todayEvents = events.filter((e) => isToday(e.start_time)).sort((a, b) => new Date(a.start_time).getTime() - new Date(b.start_time).getTime())

  if (todayEvents.length === 0) return null

  const HeadingTag = embedded ? 'h3' : 'h2'

  const body = (
    <>
      {/* Today's Events */}
      {todayEvents.length > 0 && (
        <div className={`rounded-xl p-4 border ${settings.quietMode ? "bg-lsc-cream dark:bg-earth-800 border-lsc-border dark:border-earth-700" : "bg-gradient-to-r from-red-50 via-orange-50 to-status-warning-50 dark:from-red-900/20 dark:via-orange-900/20 dark:to-status-warning-900/20 border-status-danger-200 dark:border-status-danger-800/50"}`}>
          <div className="flex items-center gap-2 mb-3">
            <Zap className="w-5 h-5 text-status-danger-500 dark:text-status-danger-400" aria-hidden="true" />
            <HeadingTag className={`font-serif font-bold text-lsc-dark dark:text-lsc-cream ${embedded ? 'text-base' : 'text-lg'}`}>
              {t('events.happeningToday')}
            </HeadingTag>
            {!settings.noFOMO && (
              <span className="px-2 py-0.5 rounded-full text-xs font-bold bg-status-danger-700 text-white">
                {t('events.eventCount', { count: todayEvents.length })}
              </span>
            )}
          </div>
          <div className="flex flex-wrap gap-3">
            {todayEvents.map((event) => (
              <article
                key={event.id}
                className="flex-1 min-w-[250px] max-w-md bg-lsc-white dark:bg-earth-800 rounded-xl p-3 shadow-sm hover:shadow-md transition-all"
                aria-label={t('events.eventLabel', { title: event.title })}
              >
                <div className="flex items-start gap-3">
                  <div className="w-14 h-12 flex-shrink-0 bg-status-danger-100 dark:bg-status-danger-900/40 rounded-lg flex items-center justify-center">
                    <span className="text-xs font-bold text-status-danger-800 dark:text-status-danger-400 text-center leading-tight">
                      {formatTime(event.start_time)}
                    </span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="font-medium text-sm text-lsc-dark dark:text-lsc-cream" title={event.title}>
                      <button
                        type="button"
                        onClick={() => onEventClick(event)}
                        className="w-full text-left line-clamp-1 hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose rounded-sm"
                      >
                        {event.title}
                      </button>
                    </h3>
                    <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                      {formatTime(event.start_time)} {event.location && `at ${event.location}`}
                    </p>
                    {event.registration_required && event.spots_remaining !== null && (
                      <span className={`text-xs ${settings.noUrgentLanguage ? 'text-lsc-dark/70 dark:text-lsc-cream/70' : event.spots_remaining === 0 ? 'text-status-danger-500' : 'text-status-success-600 dark:text-status-success-400'}`}>
                        {event.spots_remaining === 0 ? t('events.waitlistAvailable') : t('events.spotsLeft', { count: event.spots_remaining })}
                      </span>
                    )}
                  </div>
                  {event.registration_required && (
                    <button
                      onClick={() => onRegister(event)}
                      className="flex-shrink-0 px-2 py-1 rounded-lg text-xs font-medium bg-lsc-rose text-white hover:bg-lsc-rose/90"
                    >
                      {t('events.register')}
                    </button>
                  )}
                </div>
              </article>
            ))}
          </div>
        </div>
      )}
    </>
  )

  if (embedded) return body

  return (
    <section className="mb-8 space-y-4" aria-label={t('events.upcomingEvents')}>
      {body}
    </section>
  )
}

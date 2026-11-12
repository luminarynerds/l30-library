/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Link } from 'react-router-dom'
import { ArrowRight, Calendar, MapPin, Users } from 'lucide-react'
import type { Event } from '@/api/events-api'
import { useTranslation } from '@/i18n/I18nContext'

interface UpcomingProgramsStripProps {
  events: Event[] | null
}

function formatProgramDate(iso: string): { day: string; date: string; time: string } {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return { day: '', date: '', time: '' }
  return {
    day: d.toLocaleDateString(undefined, { weekday: 'short' }),
    date: d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' }),
    time: d.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' }),
  }
}

export default function UpcomingProgramsStrip({
  events,
}: UpcomingProgramsStripProps): React.ReactElement | null {
  const { t } = useTranslation()
  if (!events || events.length === 0) return null
  const top3 = events.slice(0, 3)

  return (
    <section
      aria-label={t('home.whatsHappening.title', "What's happening this week")}
      className="max-w-6xl mx-auto px-6 space-y-6 motion-safe:animate-hero-fade-up-3"
    >
      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
        <h2 className="font-serif text-2xl md:text-3xl text-lsc-dark dark:text-lsc-cream">
          {t('home.whatsHappening.title', "What's happening this week")}
        </h2>
        <Link
          to="/events"
          className="group inline-flex items-center gap-2 text-sm font-bold text-sage-700 dark:text-lsc-rose hover:text-sage-800 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2 rounded-sm"
        >
          {t('home.whatsHappening.viewAll', 'See all events')}
          <ArrowRight className="w-4 h-4 motion-safe:group-hover:translate-x-1 motion-safe:transition-transform" />
        </Link>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 md:gap-6">
        {top3.map((event) => {
          const { day, date, time } = formatProgramDate(event.start_time)
          const audienceLabel = event.audience ?? t('events.card.allAges', 'All ages')
          const locationLabel =
            event.location ?? event.branch_name ?? t('events.card.mainLibrary', 'Main Library')

          let regStatus: string
          if (!event.registration_required) {
            regStatus = t('events.card.dropIn', 'Drop in, no registration')
          } else if (event.spots_remaining !== null && event.spots_remaining <= 0) {
            regStatus = t('events.card.full', 'Full')
          } else if (event.spots_remaining !== null && event.spots_remaining > 0) {
            regStatus = t('home.whatsHappening.spotsLeft', { count: String(event.spots_remaining) })
          } else {
            regStatus = t('events.card.registrationRequired', 'Registration required')
          }

          return (
            <article
              key={event.id}
              className="group rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800/40 hover:border-lsc-rose/40 motion-safe:hover:scale-[1.01] motion-safe:transition-transform transition-colors overflow-hidden"
            >
              <Link
                to={`/events/${event.id}`}
                className="flex flex-col p-5 gap-3 min-h-[13rem] h-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2 rounded-xl"
              >
                {/* Slot 1: date + time */}
                <div className="flex items-baseline gap-2 font-mono text-xs uppercase tracking-[0.2em] text-lsc-rose">
                  <Calendar className="w-3.5 h-3.5 flex-shrink-0" aria-hidden="true" />
                  <time dateTime={event.start_time}>
                    {day} {date}
                    <span className="text-earth-600 dark:text-earth-500 mx-1.5" aria-hidden="true">
                      &middot;
                    </span>
                    {time}
                  </time>
                </div>

                {/* Slot 2: title heading */}
                <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream leading-snug line-clamp-2 flex-1">
                  {event.title}
                </h3>

                {/* Slot 3: audience tag */}
                <div>
                  <span className="px-2 py-0.5 rounded-full bg-sage-50 dark:bg-sage-900/30 text-sage-800 dark:text-sage-200 text-xs font-medium">
                    {audienceLabel}
                  </span>
                </div>

                {/* Slot 4: location */}
                <div className="flex items-center gap-1 text-xs text-earth-700 dark:text-earth-400">
                  <MapPin className="w-3 h-3 flex-shrink-0" aria-hidden="true" />
                  <span className="line-clamp-1">{locationLabel}</span>
                </div>

                {/* Slot 5: registration status */}
                <div className="flex items-center gap-1.5 text-xs text-earth-700 dark:text-earth-400">
                  <Users className="w-3 h-3 flex-shrink-0" aria-hidden="true" />
                  <span>{regStatus}</span>
                </div>
              </Link>
            </article>
          )
        })}
      </div>
    </section>
  )
}

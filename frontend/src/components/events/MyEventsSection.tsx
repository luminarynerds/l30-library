/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * MyEventsSection - Shows user's registered events dashboard
 * Displays upcoming events the user has registered for with quick access to details and cancellation
 */
import { Calendar, MapPin, Clock, X, ChevronRight, CalendarCheck, CalendarClock } from 'lucide-react'
import type { StoredRegistration } from '@/hooks/useEventPersonalization'
import type { Event } from '@/api/api'
import { downloadICalEvent } from '@/utils/calendarExport'
import { getCurrentLocale } from '@/i18n'

interface MyEventsSectionProps {
  registrations: StoredRegistration[]
  events: Event[]
  onCancelRegistration: (eventId: number, registrationId: number) => void
  onViewEvent: (event: Event) => void
  userEmail: string | null
}

function formatTime(dateStr: string): string {
  const date = new Date(dateStr)
  return date.toLocaleTimeString(getCurrentLocale(), {
    hour: 'numeric',
    minute: '2-digit',
  })
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr)
  return date.toLocaleDateString(getCurrentLocale(), {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
  })
}

function getRelativeDate(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const diffTime = date.getTime() - now.getTime()
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24))

  if (diffDays === 0) return 'Today'
  if (diffDays === 1) return 'Tomorrow'
  if (diffDays < 7) return `In ${diffDays} days`
  if (diffDays < 14) return 'Next week'
  return formatDate(dateStr)
}

export default function MyEventsSection({
  registrations,
  events,
  onCancelRegistration,
  onViewEvent,
  userEmail,
}: MyEventsSectionProps): React.ReactElement | null {
  // Filter to only upcoming registrations that aren't cancelled
  const upcomingRegistrations = registrations.filter(reg => {
    const eventDate = new Date(reg.eventStartTime)
    return eventDate > new Date() && reg.status !== 'cancelled'
  }).sort((a, b) => new Date(a.eventStartTime).getTime() - new Date(b.eventStartTime).getTime())

  if (upcomingRegistrations.length === 0) {
    return null
  }

  // Create a map of events for quick lookup
  const eventMap = new Map(events.map(e => [e.id, e]))

  return (
    <section
      aria-labelledby="my-events-heading"
      className="bg-gradient-to-r from-lsc-rose/10 to-lsc-cream dark:from-lsc-rose/20 dark:to-earth-800 rounded-xl p-4 sm:p-6"
    >
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-lsc-rose/20 dark:bg-lsc-rose/30 rounded-xl">
            <CalendarCheck
              aria-hidden="true"
              className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light"
            />
          </div>
          <div>
            <h2
              id="my-events-heading"
              className="text-lg font-serif font-semibold text-lsc-dark dark:text-lsc-cream"
            >
              My Upcoming Events
            </h2>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
              {upcomingRegistrations.length} event{upcomingRegistrations.length !== 1 ? 's' : ''} you're registered for
            </p>
          </div>
        </div>
      </div>

      <div className="space-y-3">
        {upcomingRegistrations.slice(0, 5).map((registration) => {
          const event = eventMap.get(registration.eventId)
          const relativeDate = getRelativeDate(registration.eventStartTime)
          const isToday = relativeDate === 'Today'
          const isTomorrow = relativeDate === 'Tomorrow'

          return (
            <div
              key={registration.registrationId}
              className={`group bg-lsc-white dark:bg-earth-800 rounded-xl p-3 sm:p-4 shadow-sm hover:shadow-md transition-all ${
                isToday ? 'ring-2 ring-lsc-rose' : ''
              }`}
            >
              <div className="flex items-start gap-3 sm:gap-4">
                {/* Date badge */}
                <div className={`text-center flex-shrink-0 ${
                  isToday ? 'bg-lsc-rose text-white' :
                  isTomorrow ? 'bg-lsc-rose/20 dark:bg-lsc-rose/30' :
                  'bg-lsc-cream dark:bg-earth-700'
                } rounded-xl p-2 min-w-[48px]`}>
                  <span className={`text-xs font-medium ${
                    isToday ? 'text-white/90' : 'text-lsc-rose dark:text-lsc-rose-light'
                  }`}>
                    {new Date(registration.eventStartTime).toLocaleDateString(getCurrentLocale(), { month: 'short' })}
                  </span>
                  <span className={`block text-lg font-bold ${
                    isToday ? 'text-white' : 'text-lsc-dark dark:text-lsc-cream'
                  }`}>
                    {new Date(registration.eventStartTime).getDate()}
                  </span>
                </div>

                {/* Event details */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <button
                        onClick={() => event && onViewEvent(event)}
                        className="text-left font-medium text-lsc-dark dark:text-lsc-cream hover:text-lsc-rose dark:hover:text-lsc-rose-light transition-colors line-clamp-1"
                        title={registration.eventTitle}
                      >
                        {registration.eventTitle}
                      </button>

                      <div className="flex flex-wrap items-center gap-2 mt-1 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full font-medium ${
                          isToday ? 'bg-lsc-rose/20 text-lsc-rose dark:text-lsc-rose-light' :
                          isTomorrow ? 'bg-lsc-cream dark:bg-earth-700 text-lsc-dark/80 dark:text-lsc-cream/80' :
                          'bg-lsc-cream/50 dark:bg-earth-700/50'
                        }`}>
                          <Calendar aria-hidden="true" className="w-3 h-3" />
                          {relativeDate}
                        </span>
                        <span className="flex items-center gap-1">
                          <Clock aria-hidden="true" className="w-3 h-3" />
                          {formatTime(registration.eventStartTime)}
                        </span>
                        {registration.eventLocation && (
                          <span className="flex items-center gap-1 truncate max-w-[150px]">
                            <MapPin aria-hidden="true" className="w-3 h-3 flex-shrink-0" />
                            <span className="truncate" title={registration.eventLocation}>{registration.eventLocation}</span>
                          </span>
                        )}
                      </div>

                      {/* Status badges */}
                      <div className="flex flex-wrap items-center gap-2 mt-2">
                        {registration.status === 'waitlisted' && (
                          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-700 dark:text-status-warning-300">
                            Waitlisted
                          </span>
                        )}
                        {registration.status === 'confirmed' && (
                          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-300">
                            Confirmed
                          </span>
                        )}
                        {registration.reminderRequested && (
                          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-earth-100 dark:bg-earth-800/30 text-lsc-rose dark:text-lsc-rose-light">
                            Reminder set
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-1 flex-shrink-0">
                      <button
                        onClick={() => event && onViewEvent(event)}
                        className="p-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose dark:hover:text-lsc-rose-light hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-lg transition-colors"
                        aria-label={`View details for ${registration.eventTitle}`}
                      >
                        <ChevronRight aria-hidden="true" className="w-4 h-4" />
                      </button>
                      {/* Remind me: downloads an .ics with 1-day / 1-hour VALARMs.
                          Opt-in — the patron's calendar app fires the reminders
                          offline. */}
                      {event && (
                        <button
                          onClick={() => downloadICalEvent(event, { alarms: true })}
                          className="p-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose dark:hover:text-lsc-rose-light hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-lg transition-colors"
                          aria-label={`Download a calendar reminder for ${registration.eventTitle}`}
                          title="Remind me — calendar file with 1-day and 1-hour alerts"
                        >
                          <CalendarClock aria-hidden="true" className="w-4 h-4" />
                        </button>
                      )}
                      <button
                        onClick={() => {
                          if (userEmail && confirm('Are you sure you want to cancel this registration?')) {
                            onCancelRegistration(registration.eventId, registration.registrationId)
                          }
                        }}
                        className="p-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-status-danger-600 dark:hover:text-status-danger-400 hover:bg-status-danger-50 dark:bg-status-danger-900/20 dark:hover:bg-status-danger-900/20 rounded-lg transition-colors"
                        aria-label={`Cancel registration for ${registration.eventTitle}`}
                      >
                        <X aria-hidden="true" className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {upcomingRegistrations.length > 5 && (
        <p className="text-sm text-center text-lsc-dark/70 dark:text-lsc-cream/70 mt-4">
          And {upcomingRegistrations.length - 5} more event{upcomingRegistrations.length - 5 !== 1 ? 's' : ''}...
        </p>
      )}
    </section>
  )
}

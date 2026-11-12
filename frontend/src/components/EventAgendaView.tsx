/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React, { useMemo, useState } from 'react'
import {
  Clock,
  MapPin,
  Users,
  UserPlus,
  ChevronDown,
  ChevronUp,
  Calendar,
  Download,
  ExternalLink,
} from 'lucide-react'
import type { Event } from '@/api/api'
import { clsx } from '@/utils/helpers'
import {
  downloadICalEvent,
  generateGoogleCalendarUrl,
  generateOutlookCalendarUrl,
} from '@/utils/calendarExport'
import { useTranslation, getCurrentLocale } from '@/i18n'
import { t } from '@/i18n'

interface EventAgendaViewProps {
  events: Event[]
  onEventClick: (event: Event) => void
  onRegister: (event: Event) => void
  daysToShow?: number
  showPastEvents?: boolean
}

interface DayGroup {
  date: Date
  dateKey: string
  events: Event[]
  isToday: boolean
  isPast: boolean
}

// Utility to format date for grouping
const formatDateKey = (date: Date): string =>
  `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`

const isSameDay = (date1: Date, date2: Date): boolean =>
  date1.getFullYear() === date2.getFullYear() &&
  date1.getMonth() === date2.getMonth() &&
  date1.getDate() === date2.getDate()

// Single Agenda Event Card
interface AgendaEventCardProps {
  event: Event
  onClick: () => void
  onRegister: () => void
}

const AgendaEventCard = React.memo(function AgendaEventCard({
  event,
  onClick,
  onRegister,
}: AgendaEventCardProps) {
  const [showCalendarMenu, setShowCalendarMenu] = useState(false)
  const calendarMenuRef = React.useRef<HTMLDivElement>(null)
  const calendarButtonRef = React.useRef<HTMLButtonElement>(null)

  const handleCalendarMenuKeyDown = (e: React.KeyboardEvent) => {
    const items = calendarMenuRef.current?.querySelectorAll('[role="menuitem"]') as NodeListOf<HTMLElement> | undefined
    if (!items?.length) return

    const currentIndex = Array.from(items).indexOf(document.activeElement as HTMLElement)

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault()
        items[(currentIndex + 1) % items.length]!.focus()
        break
      case 'ArrowUp':
        e.preventDefault()
        items[(currentIndex - 1 + items.length) % items.length]!.focus()
        break
      case 'Home':
        e.preventDefault()
        items[0]!.focus()
        break
      case 'End':
        e.preventDefault()
        items[items.length - 1]!.focus()
        break
      case 'Escape':
        e.preventDefault()
        setShowCalendarMenu(false)
        calendarButtonRef.current?.focus()
        break
    }
  }

  const startTime = new Date(event.start_time).toLocaleTimeString(getCurrentLocale(), {
    hour: 'numeric',
    minute: '2-digit',
  })

  const endTime = event.end_time
    ? new Date(event.end_time).toLocaleTimeString(getCurrentLocale(), {
        hour: 'numeric',
        minute: '2-digit',
      })
    : null

  const spotsInfo =
    event.max_attendees !== null
      ? event.spots_remaining === 0
        ? 'Full (waitlist available)'
        : `${event.spots_remaining} spots left`
      : null

  const handleAddToCalendar = (service: 'google' | 'outlook' | 'ical') => {
    switch (service) {
      case 'google':
        window.open(generateGoogleCalendarUrl(event), '_blank', 'noopener,noreferrer')
        break
      case 'outlook':
        window.open(generateOutlookCalendarUrl(event), '_blank', 'noopener,noreferrer')
        break
      case 'ical':
        downloadICalEvent(event)
        break
    }
    setShowCalendarMenu(false)
  }

  return (
    <div
      className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-4 hover:shadow-md transition-shadow"
      role="article"
      aria-label={`Event: ${event.title}`}
    >
      <div className="flex flex-col sm:flex-row gap-4">
        {/* Time column */}
        <div className="flex-shrink-0 sm:w-24">
          <div className="flex sm:flex-col items-center sm:items-start gap-2 sm:gap-0">
            <div className="flex items-center gap-1 text-lsc-rose dark:text-lsc-rose-light">
              <Clock className="w-4 h-4" aria-hidden="true" />
              <span className="font-semibold">{startTime}</span>
            </div>
            {endTime && (
              <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                - {endTime}
              </span>
            )}
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <button
            onClick={onClick}
            className="text-left w-full focus:outline-none focus:ring-2 focus:ring-lsc-rose rounded"
          >
            <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream hover:text-lsc-rose dark:hover:text-lsc-rose-light transition-colors">
              {event.title}
            </h3>
          </button>

          {/* Meta info */}
          <div className="flex flex-wrap gap-x-4 gap-y-1 mt-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
            {event.location && (
              <span className="flex items-center gap-1">
                <MapPin className="w-3.5 h-3.5" aria-hidden="true" />
                <span className="truncate max-w-[9.375rem]" title={event.location}>{event.location}</span>
              </span>
            )}
            {event.audience && (
              <span className="flex items-center gap-1">
                <Users className="w-3.5 h-3.5" aria-hidden="true" />
                {event.audience}
              </span>
            )}
          </div>

          {/* Description preview */}
          {event.description && (
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-2 line-clamp-2" title={event.description}>
              {event.description}
            </p>
          )}

          {/* Tags and capacity */}
          <div className="flex flex-wrap items-center gap-2 mt-3">
            {event.category && (
              <span className="text-xs px-2 py-1 bg-lsc-cream dark:bg-lsc-dark text-lsc-rose dark:text-lsc-rose-light rounded font-medium">
                {event.category}
              </span>
            )}
            {spotsInfo && (
              <span
                className={clsx(
                  'text-xs px-2 py-1 rounded',
                  event.spots_remaining === 0
                    ? 'bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-700 dark:text-status-warning-300'
                    : 'bg-sage-100 dark:bg-sage-900/30 text-sage-700 dark:text-sage-300'
                )}
              >
                {spotsInfo}
              </span>
            )}
            {event.is_virtual && (
              <span className="text-xs px-2 py-1 bg-earth-100 dark:bg-earth-800/30 text-lsc-rose dark:text-lsc-rose-light rounded">
                Virtual
              </span>
            )}
          </div>
        </div>

        {/* Actions */}
        <div className="flex sm:flex-col gap-2 flex-shrink-0 sm:items-end">
          {event.registration_required && (
            <button
              onClick={(e) => {
                e.stopPropagation()
                onRegister()
              }}
              className={clsx(
                'flex items-center gap-2 px-3 py-2 min-h-[40px] rounded-xl text-sm font-semibold transition-all focus:outline-none focus:ring-2 focus:ring-lsc-rose touch-manipulation',
                event.spots_remaining === 0
                  ? 'bg-lsc-cream dark:bg-lsc-dark/30 text-lsc-rose dark:text-lsc-rose-light border border-lsc-rose'
                  : 'bg-lsc-rose text-white hover:bg-lsc-rose/90'
              )}
              aria-label={event.spots_remaining === 0 ? 'Join waitlist' : 'Register for event'}
            >
              <UserPlus className="w-4 h-4" aria-hidden="true" />
              {event.spots_remaining === 0 ? 'Waitlist' : 'Register'}
            </button>
          )}

          {/* Add to calendar dropdown */}
          <div className="relative">
            <button
              ref={calendarButtonRef}
              onClick={() => setShowCalendarMenu(!showCalendarMenu)}
              className="flex items-center gap-1.5 px-3 py-2 min-h-[40px] rounded-xl text-sm font-medium bg-lsc-cream dark:bg-lsc-brown hover:bg-lsc-border dark:hover:bg-lsc-brown/80 text-lsc-dark dark:text-lsc-cream transition-colors focus:outline-none focus:ring-2 focus:ring-lsc-rose"
              aria-expanded={showCalendarMenu}
              aria-haspopup="menu"
              aria-label={t('aria.eventAgendaView.addToCalendar')}
            >
              <Calendar className="w-4 h-4" aria-hidden="true" />
              <span className="hidden sm:inline">Add to Cal</span>
              {showCalendarMenu ? (
                <ChevronUp className="w-3 h-3" aria-hidden="true" />
              ) : (
                <ChevronDown className="w-3 h-3" aria-hidden="true" />
              )}
            </button>

            {showCalendarMenu && (
              <>
                <div
                  className="fixed inset-0 z-10"
                  onClick={() => setShowCalendarMenu(false)}
                  aria-hidden="true"
                />
                <div
                  ref={calendarMenuRef}
                  className="absolute right-0 top-full mt-1 bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg border border-lsc-border dark:border-earth-700 p-1 z-20 min-w-[180px]"
                  role="menu"
                  aria-label={t('aria.eventAgendaView.calendarOptions')}
                  onKeyDown={handleCalendarMenuKeyDown}
                >
                  <button
                    onClick={() => handleAddToCalendar('google')}
                    className="w-full text-left px-3 py-2 text-sm text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-lsc-brown rounded-lg transition-colors flex items-center gap-2 focus-visible:outline-none focus-visible:bg-lsc-rose/10"
                    role="menuitem"
                    tabIndex={-1}
                  >
                    <ExternalLink className="w-4 h-4" aria-hidden="true" />
                    Google Calendar
                  </button>
                  <button
                    onClick={() => handleAddToCalendar('outlook')}
                    className="w-full text-left px-3 py-2 text-sm text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-lsc-brown rounded-lg transition-colors flex items-center gap-2 focus-visible:outline-none focus-visible:bg-lsc-rose/10"
                    role="menuitem"
                    tabIndex={-1}
                  >
                    <ExternalLink className="w-4 h-4" aria-hidden="true" />
                    Outlook Calendar
                  </button>
                  <button
                    onClick={() => handleAddToCalendar('ical')}
                    className="w-full text-left px-3 py-2 text-sm text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-lsc-brown rounded-lg transition-colors flex items-center gap-2 focus-visible:outline-none focus-visible:bg-lsc-rose/10"
                    role="menuitem"
                    tabIndex={-1}
                  >
                    <Download className="w-4 h-4" aria-hidden="true" />
                    Download .ics
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  )
})

// Day Header Component
interface DayHeaderProps {
  date: Date
  eventCount: number
  isToday: boolean
  isPast: boolean
  isExpanded: boolean
  onToggle: () => void
}

const DayHeader = React.memo(function DayHeader({
  date,
  eventCount,
  isToday,
  isPast,
  isExpanded,
  onToggle,
}: DayHeaderProps) {
  const dayName = date.toLocaleDateString(getCurrentLocale(), { weekday: 'long' })
  const dateStr = date.toLocaleDateString(getCurrentLocale(), { month: 'long', day: 'numeric' })

  return (
    <button
      onClick={onToggle}
      className={clsx(
        'w-full flex items-center justify-between p-3 rounded-xl transition-colors focus:outline-none focus:ring-2 focus:ring-lsc-rose',
        isToday
          ? 'bg-lsc-rose/10 dark:bg-lsc-rose/20 border-l-4 border-lsc-rose'
          : isPast
            ? 'bg-lsc-cream/50 dark:bg-lsc-brown/30'
            : 'bg-lsc-cream dark:bg-lsc-brown hover:bg-lsc-border dark:hover:bg-lsc-brown/80'
      )}
      aria-expanded={isExpanded}
      aria-label={`${dayName}, ${dateStr}, ${eventCount} events. ${isExpanded ? 'Collapse' : 'Expand'} to see events.`}
    >
      <div className="flex items-center gap-3">
        <div
          className={clsx(
            'w-12 h-12 rounded-xl flex flex-col items-center justify-center',
            isToday
              ? 'bg-lsc-rose text-white'
              : 'bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream'
          )}
        >
          <span className="text-xs font-medium">
            {date.toLocaleDateString(getCurrentLocale(), { weekday: 'short' })}
          </span>
          <span className="text-lg font-bold leading-none">{date.getDate()}</span>
        </div>
        <div className="text-left">
          <div
            className={clsx(
              'font-semibold',
              isToday
                ? 'text-lsc-rose dark:text-lsc-rose-light'
                : isPast
                  ? 'text-lsc-dark/70 dark:text-lsc-cream/70'
                  : 'text-lsc-dark dark:text-lsc-cream'
            )}
          >
            {isToday ? 'Today' : dayName}
          </div>
          <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{dateStr}</div>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <span
          className={clsx(
            'text-sm font-medium px-2 py-1 rounded-full',
            eventCount > 0
              ? 'bg-lsc-rose/10 dark:bg-lsc-rose/20 text-lsc-rose dark:text-lsc-rose-light'
              : 'bg-lsc-cream dark:bg-lsc-brown text-lsc-dark/70 dark:text-lsc-cream/70'
          )}
        >
          {eventCount} {eventCount === 1 ? 'event' : 'events'}
        </span>
        {isExpanded ? (
          <ChevronUp className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" aria-hidden="true" />
        ) : (
          <ChevronDown
            className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70"
            aria-hidden="true"
          />
        )}
      </div>
    </button>
  )
})

// Main Agenda View Component
const EventAgendaView = React.memo(function EventAgendaView({
  events,
  onEventClick,
  onRegister,
  daysToShow = 30,
  showPastEvents = false,
}: EventAgendaViewProps) {
  const { t } = useTranslation()
  const [collapsedDays, setCollapsedDays] = useState<Set<string>>(new Set())

  // Group events by day
  const dayGroups = useMemo(() => {
    const today = new Date()
    today.setHours(0, 0, 0, 0)

    const groups: Map<string, DayGroup> = new Map()
    const endDate = new Date(today)
    endDate.setDate(today.getDate() + daysToShow)

    // Sort events by start time
    const sortedEvents = [...events].sort(
      (a, b) => new Date(a.start_time).getTime() - new Date(b.start_time).getTime()
    )

    sortedEvents.forEach((event) => {
      const eventDate = new Date(event.start_time)
      eventDate.setHours(0, 0, 0, 0)

      const isPast = eventDate < today
      if (isPast && !showPastEvents) return
      if (eventDate > endDate) return

      const dateKey = formatDateKey(eventDate)

      if (!groups.has(dateKey)) {
        groups.set(dateKey, {
          date: eventDate,
          dateKey,
          events: [],
          isToday: isSameDay(eventDate, today),
          isPast,
        })
      }

      groups.get(dateKey)!.events.push(event)
    })

    return Array.from(groups.values()).sort(
      (a, b) => a.date.getTime() - b.date.getTime()
    )
  }, [events, daysToShow, showPastEvents])

  const toggleDay = (dateKey: string) => {
    setCollapsedDays((prev) => {
      const next = new Set(prev)
      if (next.has(dateKey)) {
        next.delete(dateKey)
      } else {
        next.add(dateKey)
      }
      return next
    })
  }

  const totalEvents = dayGroups.reduce((sum, group) => sum + group.events.length, 0)

  if (dayGroups.length === 0) {
    return (
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm p-8 text-center">
        <Calendar className="w-16 h-16 mx-auto mb-4 text-lsc-dark/30 dark:text-lsc-cream/60" />
        <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-2">
          No upcoming events
        </h3>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
          Check back later for new events and programs.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Summary header */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-serif font-bold text-lsc-dark dark:text-lsc-cream">
            Upcoming Events
          </h2>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
            {totalEvents} events across {dayGroups.length} days
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setCollapsedDays(new Set())}
            className="px-3 py-1.5 text-xs font-medium text-lsc-rose dark:text-lsc-rose-light hover:bg-lsc-cream dark:hover:bg-lsc-brown rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-lsc-rose"
          >
            Expand All
          </button>
          <button
            onClick={() => setCollapsedDays(new Set(dayGroups.map((g) => g.dateKey)))}
            className="px-3 py-1.5 text-xs font-medium text-lsc-rose dark:text-lsc-rose-light hover:bg-lsc-cream dark:hover:bg-lsc-brown rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-lsc-rose"
          >
            Collapse All
          </button>
        </div>
      </div>

      {/* Day groups */}
      <div className="space-y-3" role="list" aria-label={t('components.eventAgendaView.eventsGroupedByDay')}>
        {dayGroups.map((group) => {
          const isExpanded = !collapsedDays.has(group.dateKey)

          return (
            <div
              key={group.dateKey}
              className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm overflow-hidden"
              role="listitem"
            >
              <DayHeader
                date={group.date}
                eventCount={group.events.length}
                isToday={group.isToday}
                isPast={group.isPast}
                isExpanded={isExpanded}
                onToggle={() => toggleDay(group.dateKey)}
              />

              {isExpanded && group.events.length > 0 && (
                <div
                  className="p-3 pt-0 space-y-3 motion-safe:animate-in motion-safe:fade-in motion-safe:duration-200"
                  role="list"
                  aria-label={`Events for ${group.date.toLocaleDateString(getCurrentLocale(), { month: 'long', day: 'numeric' })}`}
                >
                  {group.events.map((event) => (
                    <AgendaEventCard
                      key={event.id}
                      event={event}
                      onClick={() => onEventClick(event)}
                      onRegister={() => onRegister(event)}
                    />
                  ))}
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Load more hint */}
      {dayGroups.length > 0 && (
        <p className="text-center text-sm text-lsc-dark/70 dark:text-lsc-cream/70 py-4">
          Showing events for the next {daysToShow} days
        </p>
      )}
    </div>
  )
})

export default EventAgendaView

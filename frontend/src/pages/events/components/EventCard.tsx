/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useRef, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { MapPin, Users, Clock, UserPlus, History, Image, Sparkles, Tag, AlertTriangle, Bookmark, Accessibility, Hand, Captions, Ear, Smile, Type, Info, Languages, CalendarPlus } from 'lucide-react'
import { useTranslation } from '@/i18n/I18nContext'
import { useCountdown } from '@/pages/events/hooks/useCountdown'
import { getCategoryColorClasses, getCategoryBorderClasses, getCategoryDisplayName, getCategoryAccentClasses } from '@/pages/events/utils/eventCategoryColors'
import { formatEventDateTimeRange, formatCalmStartLabel, formatLanguageName, getDateLocale } from '@/pages/events/utils/formatters'
import { downloadEventIcs } from '@/utils/ics'
import { getCapacityUrgency, isNewThisWeek } from '@/pages/events/utils/eventsPageUtils'
import { useAccessibility } from '@/features/accessibility/hooks/useAccessibility'
import ShareButton from '@/components/ShareButton'
import QuickViewPopover from './QuickViewPopover'
import type { Event } from '@/api/api'

/**
 * Typographic date plate shown in the thumbnail slot when an event has no
 * image. The date is the strongest scannable element on the card; the thin
 * top rule carries the category hue. Multi-day events show the start date.
 */
function EventDatePlate({ startTime, category }: { startTime: string; category: string | null }): React.ReactElement {
  const date = new Date(startTime)
  return (
    <div className="relative w-full h-full flex items-center justify-center bg-lsc-cream dark:bg-lsc-dark px-3 py-4">
      <span className={`absolute inset-x-0 top-0 h-1 ${getCategoryAccentClasses(category)}`} aria-hidden="true" />
      <time dateTime={startTime} className="flex flex-col items-center leading-none">
        <span className="text-[11px] font-semibold uppercase tracking-[0.2em] text-lsc-dark/70 dark:text-lsc-cream/70">
          {date.toLocaleDateString(getDateLocale(), { month: 'short' })}
        </span>
        <span className="font-serif text-5xl text-lsc-dark dark:text-lsc-cream mt-1">
          {date.getDate()}
        </span>
        <span className="text-[11px] uppercase tracking-[0.15em] text-lsc-dark/60 dark:text-lsc-cream/60 mt-1.5">
          {date.toLocaleDateString(getDateLocale(), { weekday: 'short' })}
        </span>
      </time>
    </div>
  )
}

export interface EventCardProps {
  event: Event
  onRegister: (event: Event) => void
  /**
   * @deprecated The card now navigates via its inner title <Link>; the outer
   * container no longer fires `onClick`. Kept as an optional prop for back-compat
   * with callers that have not yet been updated.
   */
  onClick?: () => void
  isPast?: boolean
  isBookmarked?: boolean
  onToggleBookmark?: (eventId: number) => void
  isRegistered?: boolean
  onTagClick?: (tag: string) => void
}

// eslint-disable-next-line complexity
export default function EventCard({ event, onRegister, isPast = false, isBookmarked = false, onToggleBookmark, isRegistered = false, onTagClick }: EventCardProps): React.ReactElement {
  const { t } = useTranslation()
  const { settings } = useAccessibility()
  const [showQuickView, setShowQuickView] = useState(false)
  const [imageError, setImageError] = useState(false)
  const hoverTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const cardRef = useRef<HTMLDivElement>(null)

  // Calm "when does this start" signal: "Starting soon" pill only within the
  // final hour; relative-day phrasing ("Today, 4 PM") inside 24h. No
  // hour-scale countdown, no alarm.
  const { upcomingStart } = useCountdown(event.start_time)

  // Check if event is new (created within last 7 days)
  const isNew = event.created_at && isNewThisWeek(event.created_at)

  // Get capacity urgency info (pass noUrgentLanguage to suppress urgency framing)
  const capacityInfo = getCapacityUrgency(event.spots_remaining, event.max_attendees, t, settings.noUrgentLanguage)
  const isFull = capacityInfo.level === 'full'

  const handleMouseEnter = useCallback(() => {
    // Only show quick view on desktop (lg and above)
    if (window.matchMedia('(min-width: 1024px)').matches) {
      hoverTimeoutRef.current = setTimeout(() => {
        setShowQuickView(true)
      }, 300) // Small delay to prevent accidental triggers
    }
  }, [])

  const handleMouseLeave = useCallback(() => {
    if (hoverTimeoutRef.current) {
      clearTimeout(hoverTimeoutRef.current)
    }
    setShowQuickView(false)
  }, [])

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (hoverTimeoutRef.current) {
        clearTimeout(hoverTimeoutRef.current)
      }
    }
  }, [])

  // Compute registration pill state: registered > drop-in > full > open.
  // The title <Link> handles keyboard/screen-reader navigation; the card's
  // hover/focus listeners only drive QuickViewPopover for sighted users.
  const registrationPill = (() => {
    if (isRegistered) {
      return {
        label: t('events.registered'),
        ariaLabel: t('events.registered'),
        classes: 'bg-status-success-100 dark:bg-status-success-900/40 text-status-success-800 dark:text-status-success-200',
      }
    }
    if (!event.registration_required) {
      return {
        label: t('events.dropIn'),
        ariaLabel: t('events.dropInAria', 'Drop-in event, no registration required'),
        classes: 'bg-lsc-cream dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream',
      }
    }
    if (event.spots_remaining === 0) {
      return {
        label: t('events.fullJoinWaitlist', 'Full — join waitlist'),
        ariaLabel: t('events.fullJoinWaitlistAria', 'This event is full. Join the waitlist.'),
        classes: 'bg-status-warning-100 dark:bg-status-warning-900/40 text-status-warning-800 dark:text-status-warning-200',
      }
    }
    return {
      label: t('events.registrationOpen', 'Open'),
      ariaLabel: t('events.registrationOpenAria', 'Registration open'),
      classes: 'bg-forest-100 dark:bg-forest-900/40 text-forest-800 dark:text-forest-200',
    }
  })()

  // Age range: prefer min/max over audience string.
  const ageRangeText = (() => {
    const hasMin = typeof event.min_age === 'number' && event.min_age !== null
    const hasMax = typeof event.max_age === 'number' && event.max_age !== null
    if (hasMin && hasMax) return t('events.agesRange', { min: event.min_age, max: event.max_age })
    if (hasMin) return t('events.agesMin', { min: event.min_age })
    if (hasMax) return t('events.agesMax', { max: event.max_age })
    return null
  })()

  // Accessibility affordances. Render only the ones that are true. Each carries
  // a visible short label (`short`) plus a full label for screen readers — bare
  // glyphs exclude the patrons they advertise to.
  const affordances: { key: string; Icon: typeof Accessibility; label: string; short: string }[] = []
  if (event.wheelchair_accessible) affordances.push({ key: 'wheelchair', Icon: Accessibility, label: t('events.affordances.wheelchair', 'Wheelchair accessible'), short: t('events.affordances.wheelchairShort', 'Step-free') })
  if (event.asl_provided) affordances.push({ key: 'asl', Icon: Hand, label: t('events.affordances.asl', 'ASL provided'), short: t('events.affordances.aslShort', 'ASL') })
  if (event.captioning_provided) affordances.push({ key: 'captions', Icon: Captions, label: t('events.affordances.captioning', 'Captioning provided'), short: t('events.affordances.captioningShort', 'Captioned') })
  if (event.assistive_listening) affordances.push({ key: 'assistive', Icon: Ear, label: t('events.affordances.assistiveListening', 'Assistive listening'), short: t('events.affordances.assistiveListeningShort', 'Hearing loop') })
  if (event.sensory_friendly) affordances.push({ key: 'sensory', Icon: Smile, label: t('events.affordances.sensory', 'Sensory-friendly'), short: t('events.affordances.sensoryShort', 'Sensory-friendly') })
  if (event.large_print_available) affordances.push({ key: 'largeprint', Icon: Type, label: t('events.affordances.largePrint', 'Large print available'), short: t('events.affordances.largePrintShort', 'Large print') })

  // "What to expect" — structured sensory descriptors. Surfaced as a native
  // <details> so sensory-sensitive patrons can pre-assess an event. Rendered
  // only when staff filled something in.
  const sensoryRows: { key: string; label: string; value: string }[] = []
  if (event.lighting) sensoryRows.push({ key: 'lighting', label: t('events.sensory.lighting.label', 'Lighting'), value: t(`events.sensory.lighting.${event.lighting}`, event.lighting) })
  if (event.noise_level) sensoryRows.push({ key: 'noise', label: t('events.sensory.noise.label', 'Noise level'), value: t(`events.sensory.noise.${event.noise_level}`, event.noise_level) })
  if (event.crowd_size) sensoryRows.push({ key: 'crowd', label: t('events.sensory.crowd.label', 'Expected crowd'), value: t(`events.sensory.crowd.${event.crowd_size}`, event.crowd_size) })
  const hasSensoryInfo = Boolean(event.accessibility_notes) || sensoryRows.length > 0 || event.quiet_space_available === true

  return (
    <div
      ref={cardRef}
      className={`group relative bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm hover:shadow-md transition-shadow overflow-hidden border-l-4 ${getCategoryBorderClasses(event.category)}`}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      onFocus={handleMouseEnter}
      onBlur={(e) => { if (!cardRef.current?.contains(e.relatedTarget as Node)) handleMouseLeave() }}
    >
      {/* Registration status pill (top-right). One pill, four states. */}
      <span
        className={`absolute top-2 right-2 z-10 inline-flex items-center text-xs font-semibold px-2 py-0.5 rounded-full shadow-sm ${registrationPill.classes}`}
        role="status"
        aria-label={registrationPill.ariaLabel}
        data-testid="event-registration-pill"
      >
        {registrationPill.label}
      </span>

      <div className="flex flex-col sm:flex-row">
        {/* Event Image Thumbnail */}
        <div className="sm:w-32 md:w-40 h-32 sm:h-auto flex-shrink-0">
          {event.image_url && !imageError ? (
            <img
              src={event.image_url}
              alt=""
              className="w-full h-full object-cover"
              onError={() => setImageError(true)}
              loading="lazy"
            />
          ) : (
            <EventDatePlate startTime={event.start_time} category={event.category} />
          )}
        </div>

        {/* Content Area */}
        <div className="flex-1 p-4 sm:p-5">
          <div className="flex flex-col sm:flex-row gap-4">
            {/* Date badge + Content */}
            <div className="flex gap-4 flex-1 min-w-0">
              {/* Small date badge only when a real image fills the thumbnail
                  slot; otherwise the date plate already owns the date. */}
              {event.image_url && !imageError && (
                <div className="text-center flex-shrink-0">
                  <time
                    dateTime={event.start_time}
                    className="w-14 h-14 sm:w-16 sm:h-16 bg-lsc-cream dark:bg-earth-700 rounded-xl flex flex-col items-center justify-center"
                  >
                    <span className="text-xs text-lsc-rose dark:text-lsc-rose-light font-medium">
                      {new Date(event.start_time).toLocaleDateString(getDateLocale(), { month: 'short' })}
                    </span>
                    <span className="text-lg sm:text-xl font-bold text-lsc-rose dark:text-lsc-cream">
                      {new Date(event.start_time).getDate()}
                    </span>
                  </time>
                </div>
              )}
              <div className="flex-1 min-w-0">
                <div className="flex items-start gap-2">
                  <h3 className="font-serif font-semibold text-base sm:text-lg text-lsc-dark dark:text-lsc-cream line-clamp-2 min-w-0" title={event.title}>
                    <Link
                      to={`/events/detail/${event.id}`}
                      className="hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose rounded-sm"
                    >
                      {event.title}
                    </Link>
                  </h3>
                  {/* New This Week Badge */}
                  {isNew && !isPast && (
                    <span
                      className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-bold bg-status-warning-700 text-white shadow-sm motion-safe:animate-none"
                      role="status"
                      aria-label={t('events.newEventLabel')}
                    >
                      <Sparkles className="w-3 h-3" aria-hidden="true" />
                      {t('events.new')}
                    </span>
                  )}
                </div>

                {/* Series link — single line "Part of: <series>" routes to the series enroll page. */}
                {event.series_id && event.series_name && (
                  <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                    {t('events.partOf', 'Part of:')}{' '}
                    <Link
                      to={`/events/series/${encodeURIComponent(event.series_id)}`}
                      className="underline hover:no-underline"
                      onClick={(e) => e.stopPropagation()}
                    >
                      {event.series_name}
                    </Link>
                  </p>
                )}

                {/* When it starts — calm relative/absolute phrasing. No
                    countdown clock, no alarm icon. A soft "Starting soon"
                    pill appears only within the final hour (and only for
                    upcoming events). */}
                {!isPast && (
                  <p className="mt-1.5 text-xs sm:text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                    {formatCalmStartLabel(event.start_time)}
                    {upcomingStart?.kind === 'soon' && (
                      <span className="ml-2 inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-lsc-cream dark:bg-earth-700 text-lsc-dark/80 dark:text-lsc-cream/80">
                        {t('events.startingSoon', 'Starting soon')}
                      </span>
                    )}
                  </p>
                )}

                <div className="flex flex-wrap gap-2 sm:gap-3 mt-2 text-xs sm:text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                  <span className="flex items-center gap-1">
                    <Clock aria-hidden="true" className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
                    <time dateTime={event.start_time}>{formatEventDateTimeRange(event.start_time, event.end_time)}</time>
                  </span>
                  {/* One place, one pin. Combine room/location and branch into
                      a single statement: branch carries the room when both are
                      present and distinct; otherwise whichever exists. */}
                  {(() => {
                    const room = event.location?.trim() || null
                    const branch = event.branch_name?.trim() || null
                    let place: string | null
                    if (room && branch && room !== branch) place = `${branch} — ${room}`
                    else place = branch || room
                    if (!place) return null
                    return (
                      <span className="flex items-center gap-1" data-testid="event-location">
                        <MapPin aria-hidden="true" className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
                        <span className="truncate max-w-[220px] sm:max-w-none" title={place}>{place}</span>
                      </span>
                    )
                  })()}
                  {(ageRangeText || event.audience) && (
                    <span className="flex items-center gap-1">
                      <Users aria-hidden="true" className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
                      {ageRangeText || event.audience}
                    </span>
                  )}
                  {affordances.length > 0 && (
                    <ul className="flex flex-wrap items-center gap-1.5" aria-label={t('events.affordances.label', 'Accessibility features')}>
                      {affordances.map(({ key, Icon, label, short }) => (
                        <li
                          key={key}
                          aria-label={label}
                          className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full bg-forest-100 dark:bg-forest-900/40 text-forest-800 dark:text-forest-200"
                        >
                          <Icon aria-hidden="true" className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
                          <span aria-hidden="true" className="text-xs font-medium">{short}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                  {event.event_language && (
                    <span className="flex items-center gap-1" data-testid="event-language-chip">
                      <Languages aria-hidden="true" className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-forest-700 dark:text-forest-300" />
                      <span lang={event.event_language}>
                        {t('events.inLanguage', { language: formatLanguageName(event.event_language) })}
                      </span>
                    </span>
                  )}
                </div>
                {event.description && (
                  <p className="text-xs sm:text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-2 line-clamp-2" title={event.description}>
                    {event.description}
                  </p>
                )}
                {hasSensoryInfo && (
                  <details className="mt-2">
                    <summary className="inline-flex items-center gap-1.5 cursor-pointer text-xs sm:text-sm font-medium text-forest-800 dark:text-forest-300 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose rounded-sm">
                      <Info aria-hidden="true" className="w-3.5 h-3.5" />
                      {t('events.whatToExpect.summary', 'What to expect')}
                    </summary>
                    <div className="mt-1.5 space-y-1.5 text-xs sm:text-sm text-lsc-dark/80 dark:text-lsc-cream/80">
                      {sensoryRows.length > 0 && (
                        <dl className="flex flex-wrap gap-x-4 gap-y-1">
                          {sensoryRows.map(({ key, label, value }) => (
                            <div key={key} className="flex items-center gap-1">
                              <dt className="font-medium">{label}:</dt>
                              <dd>{value}</dd>
                            </div>
                          ))}
                        </dl>
                      )}
                      {event.quiet_space_available && (
                        <p className="flex items-center gap-1">
                          <Smile aria-hidden="true" className="w-3.5 h-3.5 text-forest-700 dark:text-forest-300" />
                          {t('events.sensory.quietSpace', 'A quiet space is available')}
                        </p>
                      )}
                      {event.accessibility_notes && (
                        <p className="whitespace-pre-line">{event.accessibility_notes}</p>
                      )}
                    </div>
                  </details>
                )}
                <div className="flex flex-wrap items-center gap-2 mt-3">
                  {/* Past event badge */}
                  {isPast && (
                    <span className="text-xs px-2 py-1 rounded font-semibold bg-earth-200 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 flex items-center gap-1">
                      <History aria-hidden="true" className="w-3 h-3" />
                      {t('events.pastEvent')}
                    </span>
                  )}
                  {/* Color-coded category badge */}
                  {event.category && (
                    <span className={`text-xs px-2 py-1 rounded font-medium ${getCategoryColorClasses(event.category)}`}>
                      {getCategoryDisplayName(event.category)}
                    </span>
                  )}

                  {/* Event Tags Pills */}
                  {!settings.quietMode && event.tags && event.tags.length > 0 && (
                    <div className="flex flex-wrap gap-1" role="group" aria-label={t('aria.eventCard.eventTags')}>
                      {event.tags.slice(0, 3).map((tag) => (
                        <button
                          key={tag}
                          onClick={(e) => { e.stopPropagation(); onTagClick?.(tag) }}
                          className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-forest-800 dark:bg-forest-700 text-white border border-forest-700 dark:border-forest-600 hover:bg-forest-900 dark:hover:bg-forest-600 transition-colors cursor-pointer"
                        >
                          <Tag className="w-2.5 h-2.5" aria-hidden="true" />
                          {tag}
                        </button>
                      ))}
                      {event.tags.length > 3 && (
                        <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                          +{event.tags.length - 3} more
                        </span>
                      )}
                    </div>
                  )}

                  {/* Add to my calendar — one-tap client-side .ics download.
                      Available on every upcoming event regardless of the
                      register/save layout split. */}
                  {!isPast && (
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation()
                        downloadEventIcs(event)
                      }}
                      className="inline-flex items-center gap-1.5 px-2.5 py-1.5 min-h-[36px] rounded-full text-xs font-medium bg-lsc-cream dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream border border-lsc-border dark:border-earth-600 hover:bg-lsc-border/50 dark:hover:bg-earth-600 transition-colors focus:outline-none focus:ring-2 focus:ring-lsc-rose touch-manipulation"
                      aria-label={t('events.addToCalendarFor', { title: event.title })}
                    >
                      <CalendarPlus aria-hidden="true" className="w-3.5 h-3.5" />
                      <span>{t('events.addToCalendar', 'Add to calendar')}</span>
                    </button>
                  )}

                  {/* Save & Share - inline with tags (hide when register button would overlap) */}
                  {!isPast && !(event.registration_required && !isRegistered) && (
                    <div className="flex items-center gap-1">
                      {onToggleBookmark && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            onToggleBookmark(event.id)
                          }}
                          className={`p-1.5 rounded-full transition-all focus:outline-none focus:ring-2 focus:ring-lsc-rose ${
                            isBookmarked
                              ? 'bg-lsc-rose/20 text-lsc-rose hover:bg-lsc-rose/30'
                              : 'text-lsc-dark/40 dark:text-lsc-cream/40 hover:text-lsc-dark/70 dark:hover:text-lsc-cream/70'
                          }`}
                          aria-label={isBookmarked ? t('events.removeFromSaved', { title: event.title }) : t('events.saveForLater', { title: event.title })}
                          aria-pressed={isBookmarked}
                        >
                          <Bookmark
                            aria-hidden="true"
                            className={`w-3.5 h-3.5 ${isBookmarked ? 'fill-current' : ''}`}
                          />
                        </button>
                      )}
                      <ShareButton
                        resourceType="event"
                        resourceId={event.id}
                        title={event.title}
                        {...(event.description ? { description: event.description } : {})}
                        date={event.start_time}
                        {...(event.image_url ? { imageUrl: event.image_url } : {})}
                        variant="compact"
                        platforms={['copy_link', 'email', 'whatsapp']}
                      />
                    </div>
                  )}

                  {/* Enhanced Capacity Urgency Messaging */}
                  {!isPast && capacityInfo.message && (
                    <span
                      className={`text-xs px-2 py-1 rounded font-medium flex items-center gap-1 ${
                        capacityInfo.level === 'critical'
                          ? 'bg-status-danger-100 dark:bg-status-danger-900/40 text-status-danger-700 dark:text-status-danger-300 font-bold motion-safe:animate-pulse'
                          : capacityInfo.level === 'urgent'
                          ? 'bg-status-warning-100 dark:bg-status-warning-900/40 text-status-warning-700 dark:text-status-warning-300 font-semibold'
                          : capacityInfo.level === 'full'
                          ? 'bg-earth-200 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 font-semibold'
                          : 'bg-lsc-cream dark:bg-earth-700/50 text-lsc-dark/70 dark:text-lsc-cream/70'
                      }`}
                    >
                      {(capacityInfo.level === 'critical' || capacityInfo.level === 'urgent') && (
                        <AlertTriangle className="w-3 h-3" aria-hidden="true" />
                      )}
                      {capacityInfo.message}
                    </span>
                  )}

                  {!settings.noFOMO && event.registration_count > 0 && (
                    <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                      {t('events.registeredCount', { count: event.registration_count })}
                    </span>
                  )}
                </div>
              </div>
            </div>
            {/* Register / Waitlist button - full width on mobile, inline on desktop (only for upcoming events) */}
            {!isPast && event.registration_required && !isRegistered && (
              <div className="flex-shrink-0 sm:self-center">
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    onRegister(event)
                  }}
                  aria-label={isFull ? t('events.waitlistFor', { title: event.title }) : t('events.registerFor', { title: event.title })}
                  className={`flex items-center justify-center gap-2 w-full sm:w-auto px-4 py-2.5 sm:py-2 min-h-[44px] rounded-xl text-sm font-semibold shadow-md hover:shadow-lg active:shadow-sm transition-all touch-manipulation ${
                    isFull
                      ? 'bg-lsc-cream hover:bg-lsc-border dark:bg-lsc-dark/30 dark:hover:bg-lsc-dark/50 text-forest-800 dark:text-forest-500 border-2 border-forest-800'
                      : 'bg-lsc-rose hover:bg-lsc-rose-dark text-white'
                  }`}
                >
                  <UserPlus aria-hidden="true" className="w-4 h-4" />
                  {isFull ? t('events.waitlist') : t('events.register')}
                </button>
              </div>
            )}
            {/* Photos/recap indicator for past events */}
            {isPast && event.image_url && (
              <div className="flex-shrink-0 sm:self-center">
                <div className="flex items-center gap-2 px-3 py-2 bg-lsc-cream dark:bg-earth-700 rounded-xl text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                  <Image aria-hidden="true" className="w-4 h-4" />
                  {t('events.photosAvailable')}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Quick View Popover */}
      <QuickViewPopover event={event} isVisible={showQuickView} />
    </div>
  )
}

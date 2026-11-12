/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useId, useState, useEffect, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import FocusTrap from 'focus-trap-react'
import { X, Calendar, MapPin, Users, Download, UserPlus, Star, Sparkles, Tag, AlertTriangle, MessageSquare, Clock, ArrowRight, ExternalLink, ChevronDown, CheckCircle, Accessibility } from 'lucide-react'
import { getRelatedEvents, type Event } from '@/api/api'
import { getCategoryColorClasses, getCategoryHeaderGradient, getCategoryDisplayName } from '@/pages/events/utils/eventCategoryColors'
import { getCapacityUrgency as getCapacityUrgencyShared } from '@/pages/events/utils/eventsPageUtils'
import { useTranslation } from '@/i18n/I18nContext'
import { useCountdown } from '@/pages/events/hooks/useCountdown'
import EventReviewForm from './EventReviewForm'
import ShareButton from './ShareButton'
import { generateGoogleCalendarUrl, generateOutlookCalendarUrl } from '@/utils/calendarExport'
import { useAccessibility } from '@/features/accessibility/hooks/useAccessibility'
import RelatedTitlesRail from './events/RelatedTitlesRail'
import { getCurrentLocale } from '@/i18n'

// Helper to check if event is new (created within last 7 days)
function isNewThisWeek(createdAt: string): boolean {
  const created = new Date(createdAt)
  const now = new Date()
  const sevenDaysAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000)
  return created >= sevenDaysAgo
}

function WhatToExpectSection({ event }: { event: Event }): React.ReactElement | null {
  const { t } = useTranslation()

  const provisions: string[] = []
  if (event.wheelchair_accessible) provisions.push(t('events.affordances.wheelchair', 'Wheelchair accessible'))
  if (event.asl_provided) provisions.push(t('events.affordances.asl', 'ASL provided'))
  if (event.captioning_provided) provisions.push(t('events.affordances.captioning', 'Captioning provided'))
  if (event.assistive_listening) provisions.push(t('events.affordances.assistiveListening', 'Assistive listening'))
  if (event.sensory_friendly) provisions.push(t('events.affordances.sensory', 'Sensory-friendly'))
  if (event.large_print_available) provisions.push(t('events.affordances.largePrint', 'Large print available'))

  const sensory: { key: string; label: string; value: string }[] = []
  if (event.lighting) sensory.push({ key: 'lighting', label: t('events.sensory.lighting.label', 'Lighting'), value: t(`events.sensory.lighting.${event.lighting}`, event.lighting) })
  if (event.noise_level) sensory.push({ key: 'noise', label: t('events.sensory.noise.label', 'Noise level'), value: t(`events.sensory.noise.${event.noise_level}`, event.noise_level) })
  if (event.crowd_size) sensory.push({ key: 'crowd', label: t('events.sensory.crowd.label', 'Expected crowd'), value: t(`events.sensory.crowd.${event.crowd_size}`, event.crowd_size) })

  const hasInfo =
    provisions.length > 0 ||
    sensory.length > 0 ||
    event.quiet_space_available === true ||
    Boolean(event.accessibility_notes)
  if (!hasInfo) return null

  return (
    <div className="border-t border-lsc-border dark:border-earth-700 pt-6">
      <h3 className="flex items-center gap-2 font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-3">
        <Accessibility className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
        {t('events.whatToExpect.title', 'Accessibility & what to expect')}
      </h3>
      {provisions.length > 0 && (
        <ul className="flex flex-wrap gap-2 mb-3">
          {provisions.map((label) => (
            <li
              key={label}
              className="inline-flex items-center gap-1 text-sm px-2 py-1 rounded-full bg-forest-100 dark:bg-forest-900/40 text-forest-800 dark:text-forest-200"
            >
              <CheckCircle className="w-3.5 h-3.5" aria-hidden="true" />
              {label}
            </li>
          ))}
        </ul>
      )}
      {sensory.length > 0 && (
        <dl className="flex flex-wrap gap-x-6 gap-y-1 text-sm text-lsc-dark/80 dark:text-lsc-cream/80 mb-2">
          {sensory.map(({ key, label, value }) => (
            <div key={key} className="flex items-center gap-1.5">
              <dt className="font-medium">{label}:</dt>
              <dd>{value}</dd>
            </div>
          ))}
        </dl>
      )}
      {event.quiet_space_available && (
        <p className="text-sm text-lsc-dark/80 dark:text-lsc-cream/80 mb-2">
          {t('events.sensory.quietSpace', 'A quiet space is available')}
        </p>
      )}
      {event.accessibility_notes && (
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 whitespace-pre-wrap">
          {event.accessibility_notes}
        </p>
      )}
    </div>
  )
}


interface EventDetailModalProps {
  event: Event
  onClose: () => void
  onRegister: (event: Event) => void
  onEventClick?: (event: Event) => void
}


function formatDate(dateStr: string): string {
  const date = new Date(dateStr)
  return date.toLocaleDateString(getCurrentLocale(), {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })
}

function formatTime(dateStr: string): string {
  const date = new Date(dateStr)
  return date.toLocaleTimeString(getCurrentLocale(), {
    hour: 'numeric',
    minute: '2-digit',
  })
}

// Get friendly "Who's Going" message
function getWhosGoingMessage(count: number, t: (key: string, params?: Record<string, unknown>) => string): string {
  if (count === 0) return t('events.whosGoing.beFirst')
  if (count === 1) return t('events.whosGoing.oneGoing')
  if (count < 5) return t('events.whosGoing.fewGoing', { count })
  if (count < 10) return t('events.whosGoing.manyGoing', { count })
  return t('events.whosGoing.popular', { count })
}

// Avatar placeholder colors
const avatarColors = [
  'bg-earth-500',
  'bg-status-success-500',
  'bg-category-500',
  'bg-pink-500',
  'bg-status-warning-500',
  'bg-teal-500',
  'bg-lsc-rose',
  'bg-status-danger-500',
]

// Share button component
function ShareButtons({ event }: { event: Event }) {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const { t: _t } = useTranslation()
  const eventUrl = `${window.location.origin}/events/detail/${event.id}`
  const startDate = new Date(event.start_time)
  const formattedDate = startDate.toLocaleDateString(getCurrentLocale(), {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })

  return (
    <ShareButton
      resourceType="event"
      resourceId={event.id}
      title={event.title}
      {...(event.description ? { description: event.description } : {})}
      date={formattedDate}
      {...(event.image_url ? { imageUrl: event.image_url } : {})}
      customUrl={eventUrl}
      variant="default"
      showCount={true}
      platforms={['copy_link', 'bluesky', 'mastodon', 'email']}
    />
  )
}

// Who's Going component with avatar placeholders
function WhosGoing({ count }: { count: number }) {
  const { t } = useTranslation()
  const displayCount = Math.min(count, 5)
  const remaining = count - displayCount

  return (
    <div className="flex items-center gap-3">
      {/* Avatar stack */}
      {count > 0 && (
        <div className="flex -space-x-2" aria-hidden="true">
          {Array.from({ length: displayCount }).map((_, i) => (
            <div
              key={i}
              className={`w-8 h-8 rounded-full ${avatarColors[i % avatarColors.length]} border-2 border-lsc-cream dark:border-lsc-dark flex items-center justify-center`}
            >
              <Users className="w-4 h-4 text-white" />
            </div>
          ))}
          {remaining > 0 && (
            <div className="w-8 h-8 rounded-full bg-lsc-dark dark:bg-lsc-cream border-2 border-lsc-cream dark:border-lsc-dark flex items-center justify-center">
              <span className="text-xs font-medium text-lsc-cream dark:text-lsc-dark">+{remaining}</span>
            </div>
          )}
        </div>
      )}
      {/* Message */}
      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
        {getWhosGoingMessage(count, t)}
      </p>
    </div>
  )
}

// Star rating display
function StarRating({ rating, reviewCount, hideCount = false }: { rating: number | null; reviewCount: number; hideCount?: boolean }) {
  const { t } = useTranslation()
  if (rating === null || reviewCount === 0) return null

  return (
    <div className="flex items-center gap-2">
      <div className="flex items-center gap-0.5" aria-label={t('events.rating.outOf', { rating })}>
        {[1, 2, 3, 4, 5].map((star) => (
          <Star
            key={star}
            className={`w-4 h-4 ${
              star <= Math.round(rating)
                ? 'text-status-warning-400 fill-status-warning-400'
                : 'text-earth-300 dark:text-earth-300'
            }`}
            aria-hidden="true"
          />
        ))}
      </div>
      <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
        {rating.toFixed(1)}{!hideCount && <> ({t("events.rating.reviewCount", { count: reviewCount })})</>}
      </span>
    </div>
  )
}

// Related Events Section - shows similar events based on category/audience
function RelatedEventsSection({
  eventId,
  onEventClick,
}: {
  eventId: number
  onEventClick: (event: Event) => void
}): React.ReactElement | null {
  const { t } = useTranslation()
  const { data, isLoading } = useQuery({
    queryKey: ['related-events', eventId],
    queryFn: () => getRelatedEvents(eventId, 3),
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
  })

  if (isLoading) {
    return (
      <div className="border-t border-lsc-border dark:border-earth-700 pt-6" role="status" aria-live="polite" aria-label={t('events.detail.loadingRelatedEvents')}>
        <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4">{t('events.detail.youMayAlsoLike')}</h3>
        <div className="space-y-3" aria-hidden="true">
          {[1, 2, 3].map((i) => (
            <div key={i} className="motion-safe:animate-pulse motion-reduce:animate-none flex gap-3 p-3 bg-lsc-cream/50 dark:bg-earth-800/50 rounded-xl">
              <div className="w-12 h-12 bg-lsc-border dark:bg-earth-700 rounded-lg" />
              <div className="flex-1 space-y-2">
                <div className="h-4 bg-lsc-border dark:bg-earth-700 rounded w-3/4" />
                <div className="h-3 bg-lsc-border dark:bg-earth-700 rounded w-1/2" />
              </div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  if (!data || data.items.length === 0) return null

  const formatRelatedTime = (dateStr: string): string => {
    const date = new Date(dateStr)
    return date.toLocaleTimeString(getCurrentLocale(), { hour: 'numeric', minute: '2-digit' })
  }

  return (
    <section className="border-t border-lsc-border dark:border-earth-700 pt-6" aria-label={t('aria.eventDetailModal.relatedEvents')}>
      <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
        <Star className="w-5 h-5 text-lsc-rose" aria-hidden="true" />
        {t('events.detail.youMayAlsoLike')}
      </h3>
      <div className="space-y-3">
        {data.items.map((relatedEvent) => (
          <div
            key={relatedEvent.id}
            className="flex items-center gap-3 p-3 bg-lsc-cream/50 dark:bg-earth-800/50 rounded-xl hover:bg-lsc-cream dark:hover:bg-earth-800 cursor-pointer transition-colors group"
            onClick={() => onEventClick(relatedEvent)}
            tabIndex={0}
            onKeyDown={(e: React.KeyboardEvent) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onEventClick(relatedEvent); } }}
            role="article"
            aria-label={t('events.detail.relatedEventLabel', { title: relatedEvent.title })}
          >
            {/* Date badge */}
            <div className="w-12 h-12 flex-shrink-0 bg-lsc-white dark:bg-earth-700 rounded-lg flex flex-col items-center justify-center">
              <span className="text-xs text-lsc-rose dark:text-lsc-rose-light font-medium leading-none">
                {new Date(relatedEvent.start_time).toLocaleDateString(getCurrentLocale(), { month: 'short' })}
              </span>
              <span className="text-lg font-bold text-lsc-dark dark:text-lsc-cream leading-none">
                {new Date(relatedEvent.start_time).getDate()}
              </span>
            </div>

            {/* Event info */}
            <div className="flex-1 min-w-0">
              <h4 className="font-medium text-sm text-lsc-dark dark:text-lsc-cream line-clamp-1 group-hover:text-lsc-rose dark:group-hover:text-lsc-rose-light transition-colors" title={relatedEvent.title}>
                {relatedEvent.title}
              </h4>
              <div className="flex items-center gap-2 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                <span className="flex items-center gap-1">
                  <Clock aria-hidden="true" className="w-3 h-3" />
                  {formatRelatedTime(relatedEvent.start_time)}
                </span>
                {relatedEvent.category && (
                  <span className={`px-1.5 py-0.5 rounded text-xs ${getCategoryColorClasses(relatedEvent.category)}`}>
                    {getCategoryDisplayName(relatedEvent.category)}
                  </span>
                )}
              </div>
            </div>

            {/* Arrow indicator */}
            <ArrowRight className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70 group-hover:text-lsc-rose dark:group-hover:text-lsc-rose-light transition-colors" aria-hidden="true" />
          </div>
        ))}
      </div>
    </section>
  )
}

// eslint-disable-next-line complexity
export default function EventDetailModal({ event, onClose, onRegister, onEventClick }: EventDetailModalProps): React.ReactElement {
  const { t } = useTranslation()
  const titleId = useId()
  const [imageError, setImageError] = useState(false)
  const [showReviewForm, setShowReviewForm] = useState(false)
  const [showCalendarMenu, setShowCalendarMenu] = useState(false)
  const calendarMenuRef = useRef<HTMLDivElement>(null)
  const calendarButtonRef = useRef<HTMLButtonElement>(null)
  const { upcomingStart } = useCountdown(event.start_time)
  const { settings } = useAccessibility()

  // Close modal on Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !showCalendarMenu && !showReviewForm) {
        onClose()
      }
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [onClose, showCalendarMenu, showReviewForm])

  // Handle keyboard navigation for calendar dropdown menu
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

  // Handle related event click
  const handleRelatedEventClick = (relatedEvent: Event) => {
    if (onEventClick) {
      onEventClick(relatedEvent)
    }
  }

  // Handle add to calendar
  const handleAddToCalendar = (service: 'google' | 'outlook' | 'ical') => {
    switch (service) {
      case 'google':
        window.open(generateGoogleCalendarUrl(event), '_blank', 'noopener,noreferrer')
        break
      case 'outlook':
        window.open(generateOutlookCalendarUrl(event), '_blank', 'noopener,noreferrer')
        break
      case 'ical':
        // PR #999: hit backend endpoint for consistency with the feed.
        {
          const a = document.createElement('a')
          a.href = `/api/v1/events/${event.id}/calendar.ics`
          a.download = `event-${event.id}.ics`
          a.rel = 'noopener'
          document.body.appendChild(a)
          a.click()
          document.body.removeChild(a)
        }
        break
    }
    setShowCalendarMenu(false)
  }

  const isPastEvent = new Date(event.start_time) < new Date()
  const isNew = event.created_at && isNewThisWeek(event.created_at) && !isPastEvent
  const capacityInfo = getCapacityUrgencyShared(event.spots_remaining, event.max_attendees, t, settings.noUrgentLanguage)
  const isFull = capacityInfo.level === 'full'

  const spotsInfo = event.max_attendees !== null
    ? capacityInfo.message || t('events.unlimitedCapacity')
    : t('events.unlimitedCapacity')

  const canRegister = event.registration_required

  const handleBackdropClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.target === e.currentTarget) {
      onClose()
    }
  }

  const headerGradient = getCategoryHeaderGradient(event.category)

  return (
    <>
    <FocusTrap focusTrapOptions={{ allowOutsideClick: true }}>
      {/* eslint-disable-next-line jsx-a11y/click-events-have-key-events */}
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
        onClick={handleBackdropClick}
      >
        {/* eslint-disable-next-line jsx-a11y/click-events-have-key-events */}
        <div className="bg-lsc-cream dark:bg-lsc-dark rounded-xl shadow-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
          {/* Event Image Banner */}
          {event.image_url && !imageError ? (
            <div className="relative h-48 sm:h-64 rounded-t-xl overflow-hidden">
              <img
                src={event.image_url}
                alt={`Image for ${event.title}`}
                className="w-full h-full object-cover"
                onError={() => setImageError(true)}
              />
              {/* Gradient overlay for text readability */}
              <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-black/20 to-transparent" />
              {/* Close button on image */}
              <button
                onClick={onClose}
                className="absolute top-4 right-4 z-10 p-2 bg-black/30 hover:bg-black/50 rounded-full transition-colors"
                aria-label={t('events.detail.close')}
              >
                <X className="w-6 h-6 text-white" />
              </button>
              {/* Title overlay on image */}
              <div className="absolute bottom-0 left-0 right-0 p-6">
                <div className="flex items-start gap-2 mb-2">
                  <h2 id={titleId} className="text-2xl font-serif font-bold text-white">
                    {event.title}
                  </h2>
                  {/* New This Week Badge */}
                  {isNew && (
                    <span
                      className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-bold bg-gradient-to-r from-status-warning-400 to-orange-500 text-white shadow-sm motion-safe:animate-pulse"
                      role="status"
                      aria-label={t('events.newEventLabel')}
                    >
                      <Sparkles className="w-3 h-3" aria-hidden="true" />
                      {t('events.new')}
                    </span>
                  )}
                </div>
                <div className="flex flex-wrap gap-2">
                  {event.category && (
                    <span className="text-xs px-3 py-1 rounded-full font-medium bg-lsc-white/90 dark:bg-earth-800/70 text-lsc-dark dark:text-lsc-cream backdrop-blur-sm">
                      {getCategoryDisplayName(event.category)}
                    </span>
                  )}
                  {event.audience && (
                    <span className="text-xs px-3 py-1 bg-lsc-white/90 dark:bg-earth-800/70 text-lsc-dark dark:text-lsc-cream rounded-full backdrop-blur-sm font-medium">
                      {event.audience}
                    </span>
                  )}
                  {isPastEvent && (
                    <span className="text-xs px-3 py-1 bg-lsc-white/90 dark:bg-earth-800/70 text-lsc-dark dark:text-lsc-cream rounded-full backdrop-blur-sm font-medium">
                      {t('events.pastEvent')}
                    </span>
                  )}
                  {/* Event Tags */}
                  {event.tags && event.tags.length > 0 && event.tags.slice(0, 3).map((tag) => (
                    <span
                      key={tag}
                      className="inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-full bg-lsc-dark/60 dark:bg-earth-800/70 text-white dark:text-lsc-cream backdrop-blur-sm font-medium"
                    >
                      <Tag className="w-2.5 h-2.5" aria-hidden="true" />
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            /* Header without image */
            <div className={`sticky top-0 bg-gradient-to-r ${headerGradient} p-6 rounded-t-xl`}>
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-start gap-2 mb-2">
                    <h2 id={titleId} className="text-2xl font-serif font-bold text-white">
                      {event.title}
                    </h2>
                    {/* New This Week Badge */}
                    {isNew && (
                      <span
                        className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-bold bg-gradient-to-r from-status-warning-400 to-orange-500 text-white shadow-sm motion-safe:animate-pulse"
                        role="status"
                        aria-label={t('events.newEventLabel')}
                      >
                        <Sparkles className="w-3 h-3" aria-hidden="true" />
                        {t('events.new')}
                      </span>
                    )}
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {event.category && (
                      <span className="text-xs px-3 py-1 bg-lsc-white/90 dark:bg-earth-800/70 text-lsc-dark dark:text-lsc-cream rounded-full font-medium">
                        {getCategoryDisplayName(event.category)}
                      </span>
                    )}
                    {event.audience && (
                      <span className="text-xs px-3 py-1 bg-lsc-white/90 dark:bg-earth-800/70 text-lsc-dark dark:text-lsc-cream rounded-full font-medium">
                        {event.audience}
                      </span>
                    )}
                    {isPastEvent && (
                      <span className="text-xs px-3 py-1 bg-lsc-white/90 dark:bg-earth-800/70 text-lsc-dark dark:text-lsc-cream rounded-full font-medium">
                        {t('events.pastEvent')}
                      </span>
                    )}
                    {/* Event Tags */}
                    {event.tags && event.tags.length > 0 && event.tags.slice(0, 3).map((tag) => (
                      <span
                        key={tag}
                        className="inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-full bg-lsc-dark/60 dark:bg-earth-800/70 text-white dark:text-lsc-cream font-medium"
                      >
                        <Tag className="w-2.5 h-2.5" aria-hidden="true" />
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
                <button
                  onClick={onClose}
                  className="p-2 hover:bg-lsc-white/20 dark:bg-earth-800/10 rounded-full transition-colors"
                  aria-label={t('events.detail.close')}
                >
                  <X className="w-6 h-6 text-white" />
                </button>
              </div>
            </div>
          )}

          {/* Content */}
          <div className="p-6 space-y-6">
            {/* Rating for past events */}
            {isPastEvent && event.average_rating !== undefined && (
              <StarRating rating={event.average_rating} reviewCount={event.review_count || 0} hideCount={settings.noFOMO} />
            )}

            {/* Who's Going section for upcoming events */}
            {!isPastEvent && !settings.noFOMO && event.registration_count > 0 && (
              <div className="p-4 bg-lsc-cream/50 dark:bg-earth-800/50 rounded-xl">
                <WhosGoing count={event.registration_count} />
              </div>
            )}

            {/* Calm "when it starts" heads-up. No countdown clock, no alarm,
                no pulse: a running timer reads as pressure. "Starting soon"
                only within the final hour; otherwise a quiet relative-day
                note for events inside 24h. */}
            {upcomingStart && (
              <div
                className="flex items-center justify-center gap-2 px-4 py-3 rounded-xl font-medium bg-sage-500/15 text-sage-800 dark:bg-sage-500/20 dark:text-sage-300"
                aria-live="polite"
              >
                <Clock aria-hidden="true" className="w-5 h-5" />
                <span>
                  {upcomingStart.kind === 'soon'
                    ? t('events.startingSoon')
                    : upcomingStart.kind === 'today'
                    ? t('events.startsToday', { time: upcomingStart.time })
                    : t('events.startsTomorrow', { time: upcomingStart.time })}
                </span>
              </div>
            )}

            {/* Enhanced Capacity Urgency Alert */}
            {!isPastEvent && (capacityInfo.level === 'critical' || capacityInfo.level === 'urgent') && (
              <div
                className={`flex items-center justify-center gap-2 px-4 py-3 rounded-xl font-semibold ${
                  capacityInfo.level === 'critical'
                    ? 'bg-status-danger-100 dark:bg-status-danger-900/40 text-status-danger-700 dark:text-status-danger-300 motion-safe:animate-pulse'
                    : 'bg-status-warning-100 dark:bg-status-warning-900/40 text-status-warning-700 dark:text-status-warning-300'
                }`}
                role="status"
                aria-live="polite"
                aria-label={capacityInfo.ariaLabel || undefined}
              >
                <AlertTriangle aria-hidden="true" className="w-5 h-5" />
                <span>{capacityInfo.message}</span>
              </div>
            )}

            {/* Date & Time */}
            <div className="space-y-3">
              <div className="flex items-start gap-3">
                <Calendar className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light mt-0.5" aria-hidden="true" />
                <div>
                  <p className="font-semibold text-lsc-dark dark:text-lsc-cream">
                    {formatDate(event.start_time)}
                  </p>
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                    {formatTime(event.start_time)}
                    {event.end_time && ` - ${formatTime(event.end_time)}`}
                  </p>
                </div>
              </div>

              {/* Location */}
              {(event.location || event.branch_name) && (
                <div className="flex items-start gap-3">
                  <MapPin className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light mt-0.5" aria-hidden="true" />
                  <div>
                    <p className="font-semibold text-lsc-dark dark:text-lsc-cream">{t('events.detail.location')}</p>
                    {event.location && (
                      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{event.location}</p>
                    )}
                    {event.branch_name && event.branch_name !== event.location && (
                      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{event.branch_name}</p>
                    )}
                    {event.is_virtual && (
                      <span className="inline-block mt-1 text-xs px-2 py-1 bg-earth-100 dark:bg-earth-800/30 text-lsc-rose dark:text-lsc-rose-light rounded">
                        {t('events.detail.virtualEvent')}
                      </span>
                    )}
                  </div>
                </div>
              )}

              {/* Capacity */}
              {event.max_attendees !== null && (
                <div className="flex items-start gap-3">
                  <Users className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light mt-0.5" aria-hidden="true" />
                  <div>
                    <p className="font-semibold text-lsc-dark dark:text-lsc-cream">{t('events.detail.capacity')}</p>
                    <p className={`text-sm ${
                      !isPastEvent && (capacityInfo.level === 'critical' || capacityInfo.level === 'urgent')
                        ? capacityInfo.level === 'critical'
                          ? 'text-status-danger-600 dark:text-status-danger-400 font-semibold'
                          : 'text-status-warning-600 dark:text-status-warning-400 font-medium'
                        : capacityInfo.level === 'full'
                        ? 'text-lsc-dark/70 dark:text-lsc-cream/70 font-medium'
                        : 'text-lsc-dark/70 dark:text-lsc-cream/70'
                    }`}>
                      {spotsInfo}
                    </p>
                  </div>
                </div>
              )}
            </div>

            {/* Drop-in indicator for events without registration */}
            {!canRegister && !isPastEvent && (
              <div className="flex items-center gap-2 px-4 py-3 bg-status-success-50 dark:bg-status-success-900/20 rounded-xl text-status-success-700 dark:text-status-success-300">
                <CheckCircle className="w-5 h-5 flex-shrink-0" aria-hidden="true" />
                <span className="text-sm font-medium">{t('events.dropInEvent')}</span>
              </div>
            )}

            {/* Description */}
            {event.description && (
              <div className="border-t border-lsc-border dark:border-earth-700 pt-6">
                <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-2">{t('events.detail.aboutThisEvent')}</h3>
                <p className="text-lsc-dark/70 dark:text-lsc-cream/70 whitespace-pre-wrap">
                  {event.description}
                </p>
              </div>
            )}

            {/* Accessibility & what to expect */}
            <WhatToExpectSection event={event} />

            {/* Bring the book — catalog cross-pollination rail */}
            <RelatedTitlesRail event={event} />

            {/* Related Events Section */}
            {!isPastEvent && (
              <RelatedEventsSection
                eventId={event.id}
                onEventClick={handleRelatedEventClick}
              />
            )}

            {/* Action Buttons */}
            <div className="flex flex-wrap gap-3 border-t border-lsc-border dark:border-earth-700 pt-6">
              {canRegister && !isPastEvent && (
                <button
                  onClick={() => onRegister(event)}
                  aria-label={isFull ? t('events.detail.joinEventWaitlist') : t('events.detail.registerForThisEvent')}
                  className={`flex items-center gap-2 px-6 py-3 rounded-xl font-medium transition-colors ${
                    isFull
                      ? 'bg-lsc-cream hover:bg-lsc-cream/90 dark:bg-lsc-dark/30 dark:hover:bg-lsc-dark/50 text-lsc-rose dark:text-lsc-rose-light border-2 border-lsc-rose'
                      : 'bg-lsc-rose hover:bg-lsc-rose/90 text-white'
                  }`}
                >
                  <UserPlus className="w-5 h-5" aria-hidden="true" />
                  {isFull ? t('events.waitlist') : t('events.registerForEvent')}
                </button>
              )}

              {!isPastEvent && (
                <div className="relative">
                  <button
                    ref={calendarButtonRef}
                    onClick={() => setShowCalendarMenu(!showCalendarMenu)}
                    className="flex items-center gap-2 px-6 py-3 rounded-xl font-medium bg-lsc-cream hover:bg-lsc-border dark:bg-lsc-brown dark:hover:bg-lsc-brown/90 text-lsc-dark dark:text-lsc-cream transition-colors"
                    aria-expanded={showCalendarMenu}
                    aria-haspopup="menu"
                    aria-label={t('events.detail.addToCalendarAriaLabel')}
                  >
                    <Calendar className="w-5 h-5" aria-hidden="true" />
                    {t('events.detail.addToCalendar')}
                    <ChevronDown className="w-4 h-4" aria-hidden="true" />
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
                        className="absolute left-0 bottom-full mb-2 bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg border border-lsc-border dark:border-earth-700 p-1 z-20 min-w-[200px]"
                        role="menu"
                        aria-label={t('events.agenda.calendarOptions')}
                        onKeyDown={handleCalendarMenuKeyDown}
                      >
                        <button
                          onClick={() => handleAddToCalendar('google')}
                          className="w-full text-left px-3 py-2 text-sm text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-lsc-brown rounded-lg transition-colors flex items-center gap-2 focus-visible:outline-none focus-visible:bg-lsc-rose/10"
                          role="menuitem"
                          tabIndex={-1}
                          aria-label={t('events.detail.addToGoogleCalendar')}
                        >
                          <ExternalLink className="w-4 h-4" aria-hidden="true" />
                          {t('events.agenda.googleCalendar')}
                        </button>
                        <button
                          onClick={() => handleAddToCalendar('outlook')}
                          className="w-full text-left px-3 py-2 text-sm text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-lsc-brown rounded-lg transition-colors flex items-center gap-2 focus-visible:outline-none focus-visible:bg-lsc-rose/10"
                          role="menuitem"
                          tabIndex={-1}
                          aria-label={t('events.detail.addToOutlookCalendar')}
                        >
                          <ExternalLink className="w-4 h-4" aria-hidden="true" />
                          {t('events.agenda.outlookCalendar')}
                        </button>
                        <button
                          onClick={() => handleAddToCalendar('ical')}
                          className="w-full text-left px-3 py-2 text-sm text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-lsc-brown rounded-lg transition-colors flex items-center gap-2 focus-visible:outline-none focus-visible:bg-lsc-rose/10"
                          role="menuitem"
                          tabIndex={-1}
                          aria-label={t('events.detail.downloadICalFile')}
                        >
                          <Download className="w-4 h-4" aria-hidden="true" />
                          {t('events.detail.downloadIcsFile')}
                        </button>
                      </div>
                    </>
                  )}
                </div>
              )}

              {/* Leave a Review button for past events */}
              {isPastEvent && (
                <button
                  onClick={() => setShowReviewForm(true)}
                  className="flex items-center gap-2 px-6 py-3 rounded-xl font-medium bg-lsc-rose hover:bg-lsc-rose/90 text-white transition-colors"
                  aria-label={t('events.detail.leaveReviewForEvent')}
                >
                  <MessageSquare className="w-5 h-5" aria-hidden="true" />
                  {t('events.detail.leaveReview')}
                </button>
              )}

              <ShareButtons event={event} />
            </div>
          </div>
        </div>
      </div>
    </FocusTrap>

    {/* Review Form Modal (outside FocusTrap to avoid multiple children error) */}
    {showReviewForm && (
      <EventReviewForm
        event={event}
        onClose={() => setShowReviewForm(false)}
      />
    )}
    </>
  )
}

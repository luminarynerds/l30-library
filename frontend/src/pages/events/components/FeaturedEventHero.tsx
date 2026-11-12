/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useMemo } from 'react'
import { Calendar, MapPin, Star, UserPlus } from 'lucide-react'
import type { Event } from '@/api/api'
import { useTranslation } from '@/i18n/I18nContext'
import { useNeurodivergentUX } from '@/hooks/useNeurodivergentUX'
import { useAccessibility } from '@/features/accessibility/hooks/useAccessibility'
import { formatTime, getDateLocale } from '@/pages/events/utils/formatters'
import { getCategoryColorClasses, getCategoryDisplayName } from '@/pages/events/utils/eventCategoryColors'
import ShareButton from '@/components/ShareButton'

interface FeaturedEventHeroProps {
  event: Event
  onEventClick: (event: Event) => void
  onRegister: (event: Event) => void
  isRegistered?: boolean
}

function getTimeUntilLabel(startTime: string): string | null {
  const now = new Date()
  const start = new Date(startTime)
  const diffMs = start.getTime() - now.getTime()
  if (diffMs <= 0) return null

  const diffMinutes = Math.floor(diffMs / (1000 * 60))
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))

  if (diffMinutes < 60) return `In ${diffMinutes} minute${diffMinutes === 1 ? '' : 's'}`
  if (diffHours < 24) return `In ${diffHours} hour${diffHours === 1 ? '' : 's'}`
  if (diffDays === 1) return 'Tomorrow'
  if (diffDays < 7) return `In ${diffDays} days`
  if (diffDays < 14) return 'Next week'
  return `In ${diffDays} days`
}

export default function FeaturedEventHero({
  event,
  onEventClick,
  onRegister,
  isRegistered = false,
}: FeaturedEventHeroProps): React.ReactElement {
  const { t } = useTranslation()
  const { shouldHideFOMO } = useNeurodivergentUX()
  const { settings } = useAccessibility()

  const timeUntil = useMemo(() => getTimeUntilLabel(event.start_time), [event.start_time])

  const formattedDate = useMemo(() => {
    const date = new Date(event.start_time)
    return date.toLocaleDateString(getDateLocale(), {
      weekday: 'long',
      month: 'long',
      day: 'numeric',
      year: 'numeric',
    })
  }, [event.start_time])

  const isFull = event.spots_remaining === 0

  // With an image: dark photo-overlay treatment. Without: a typographic
  // poster on cream (dark mode: plum) — no gradient, type does the work.
  const hasImage = Boolean(event.image_url)
  const tone = hasImage
    ? {
        section: 'bg-earth-800 dark:bg-earth-900',
        title: 'text-cream-50',
        meta: 'text-cream-200',
        metaIcon: 'text-cream-300',
        body: 'text-cream-300',
        learnMore: 'border-cream-300/30 text-cream-200 hover:bg-cream-50/10 dark:hover:bg-earth-700/50 focus:ring-cream-300/50',
        ringOffset: 'focus:ring-offset-earth-800',
      }
    : {
        section: 'bg-lsc-cream dark:bg-lsc-dark border-2 border-lsc-border dark:border-earth-700',
        title: 'text-lsc-dark dark:text-lsc-cream',
        meta: 'text-lsc-dark/80 dark:text-lsc-cream/80',
        metaIcon: 'text-lsc-rose dark:text-lsc-rose-light',
        body: 'text-lsc-dark/70 dark:text-lsc-cream/70',
        learnMore: 'border-lsc-dark/30 dark:border-lsc-cream/30 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-dark/5 dark:hover:bg-lsc-cream/10 focus:ring-lsc-rose',
        ringOffset: 'focus:ring-offset-lsc-cream dark:focus:ring-offset-lsc-dark',
      }

  return (
    <section
      aria-label={t('events.featuredEventLabel', { title: event.title })}
      className={`relative mb-8 overflow-hidden rounded-xl ${tone.section}`}
    >
      {/* Background image with low opacity + gradient overlay */}
      {event.image_url && (
        <div className="absolute inset-0" aria-hidden="true">
          <img
            src={event.image_url}
            alt=""
            className="h-full w-full object-cover opacity-30"
          />
          <div className="absolute inset-0 bg-gradient-to-r from-earth-900/95 via-earth-900/80 to-earth-900/60" />
        </div>
      )}

      {/* Content */}
      <div className="relative z-10 flex flex-col gap-4 p-6 md:p-8 lg:p-10">
        {/* Top row: badges + time-until */}
        <div className="flex flex-wrap items-center gap-3">
          {/* Featured badge (hidden in quiet mode) */}
          {!settings.quietMode && (
            <span className="inline-flex items-center gap-1.5 rounded-full bg-lsc-rose px-3 py-1 text-xs font-bold text-white">
              <Star className="h-3.5 w-3.5" aria-hidden="true" />
              {t('events.featured')}
            </span>
          )}

          {/* Category badge */}
          {event.category && (
            <span className={`rounded-full px-3 py-1 text-xs font-medium ${getCategoryColorClasses(event.category)}`}>
              {getCategoryDisplayName(event.category)}
            </span>
          )}

          {/* Time-until label (hidden when noFOMO) */}
          {!shouldHideFOMO && timeUntil && (
            <span className={`text-sm font-medium ${tone.meta}`}>
              {timeUntil}
            </span>
          )}
        </div>

        {/* Title — a plain heading. The "Learn more" button below is the
            event's action; the heading must not double as a control.
            No image: oversized poster type with a rose rule beneath. */}
        <h2 className={`max-w-2xl font-serif font-bold ${tone.title} ${hasImage ? 'text-2xl md:text-3xl' : 'text-3xl md:text-5xl leading-tight'}`}>
          {event.title}
        </h2>
        {!hasImage && <div className="h-1 w-16 bg-lsc-rose dark:bg-lsc-rose-light rounded-full" aria-hidden="true" />}

        {/* Date / Time / Location */}
        <div className={`flex flex-wrap items-center gap-4 ${tone.meta} ${hasImage ? 'text-sm' : 'text-base font-medium'}`}>
          <span className="flex items-center gap-1.5">
            <Calendar className={`h-4 w-4 ${tone.metaIcon}`} aria-hidden="true" />
            {formattedDate} at {formatTime(event.start_time)}
          </span>
          {event.location && (
            <span className="flex items-center gap-1.5">
              <MapPin className={`h-4 w-4 ${tone.metaIcon}`} aria-hidden="true" />
              {event.location}
            </span>
          )}
        </div>

        {/* Description */}
        {event.description && (
          <p className={`max-w-2xl text-sm leading-relaxed line-clamp-2 ${tone.body}`} title={event.description}>
            {event.description}
          </p>
        )}

        {/* Capacity info (hidden when noFOMO) */}
        {!shouldHideFOMO && event.spots_remaining !== null && event.registration_required && (
          <p className={`text-sm font-medium ${tone.meta}`}>
            {isFull
              ? t('events.waitlistAvailable')
              : t('events.spotsLeft', { count: event.spots_remaining })}
          </p>
        )}

        {/* Actions row */}
        <div className="flex flex-wrap items-center gap-3 pt-1">
          {/* Register / Waitlist CTA */}
          {event.registration_required && !isRegistered && (
            <button
              onClick={() => onRegister(event)}
              aria-label={isFull ? t('events.waitlistFor', { title: event.title }) : t('events.registerFor', { title: event.title })}
              className={`inline-flex items-center gap-2 rounded-xl px-5 py-2.5 text-sm font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 ${tone.ringOffset} ${
                isFull
                  ? hasImage
                    ? 'bg-cream-50/10 hover:bg-cream-50/20 text-cream-100 border-2 border-lsc-rose focus:ring-lsc-rose'
                    : 'bg-transparent hover:bg-lsc-rose/10 text-lsc-dark dark:text-lsc-cream border-2 border-lsc-rose focus:ring-lsc-rose'
                  : 'bg-lsc-rose hover:bg-lsc-rose/90 text-white focus:ring-lsc-rose'
              }`}
            >
              <UserPlus className="h-4 w-4" aria-hidden="true" />
              {isFull ? t('events.waitlist') : t('events.registerNow')}
            </button>
          )}

          {/* Already registered indicator (hidden when noFOMO) */}
          {!settings.noFOMO && isRegistered && (
            <span className={`inline-flex items-center gap-2 rounded-xl border px-5 py-2.5 text-sm font-semibold ${hasImage ? 'bg-status-success-700/30 border-status-success-500/40 text-status-success-300' : 'bg-status-success-100 dark:bg-status-success-900/40 border-status-success-300 dark:border-status-success-700 text-status-success-800 dark:text-status-success-200'}`}>
              {t('events.registered')}
            </span>
          )}

          {/* Learn more button */}
          <button
            onClick={() => onEventClick(event)}
            className={`inline-flex items-center gap-2 rounded-xl border px-5 py-2.5 text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 ${tone.learnMore} ${tone.ringOffset}`}
          >
            {t('events.learnMore')}
          </button>

          {/* Share button */}
          <ShareButton
            resourceType="event"
            resourceId={event.id}
            title={event.title}
            {...(event.description ? { description: event.description } : {})}
            {...(event.image_url ? { imageUrl: event.image_url } : {})}
            date={event.start_time}
            variant="compact"
          />
        </div>
      </div>
    </section>
  )
}

/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * HorizontalEventCarousel - Scrollable row of compact event cards
 * Used in the "For You" recommended events section
 */
import { useRef, useState, useCallback } from 'react'
import { ChevronLeft, ChevronRight, Clock, MapPin, Bookmark } from 'lucide-react'
import type { Event } from '@/api/api'
import { formatTime } from '@/pages/events/utils/formatters'
import { getCategoryColorClasses, getCategoryDisplayName } from '@/pages/events/utils/eventCategoryColors'
import { useAccessibility } from '@/features/accessibility/hooks/useAccessibility'
import { ShareButton } from '@/components/ShareButton'
import EventImagePlaceholder from '@/pages/events/components/EventImagePlaceholder'
import { t, getCurrentLocale } from '@/i18n'

interface HorizontalEventCarouselProps {
  events: Event[]
  onEventClick: (event: Event) => void
  onRegister?: (event: Event) => void
  onToggleBookmark: (eventId: number) => void
  isBookmarked: (eventId: number) => boolean
  isRegistered: (eventId: number) => boolean
}

interface CarouselCardProps {
  event: Event
  onEventClick: (event: Event) => void
  onToggleBookmark: (eventId: number) => void
  bookmarked: boolean
  registered: boolean
}

const CARD_WIDTH = 280
const GAP = 16
const SCROLL_AMOUNT = (CARD_WIDTH + GAP) * 2

function CarouselCard({ event, onEventClick, onToggleBookmark, bookmarked, registered }: CarouselCardProps): React.ReactElement {
  const [imageError, setImageError] = useState(false)

  return (
    <div
      className="flex-shrink-0 w-[85vw] sm:w-[280px] bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm hover:shadow-md transition-shadow cursor-pointer overflow-hidden group"
      role="listitem"
      tabIndex={0}
      aria-label={`View details for ${event.title}`}
      onClick={() => onEventClick(event)}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          onEventClick(event)
        }
      }}
    >
      {/* Event image */}
      <div className="h-36 relative">
        {event.image_url && !imageError ? (
          <img
            src={event.image_url}
            alt={event.title}
            className="w-full h-full object-cover"
            onError={() => setImageError(true)}
            loading="lazy"
          />
        ) : (
          <EventImagePlaceholder category={event.category} />
        )}

        {/* Date badge overlay */}
        <div className="absolute top-2 left-2 w-12 h-12 bg-lsc-white dark:bg-earth-800 rounded-lg flex flex-col items-center justify-center shadow-sm">
          <span className="text-xs text-lsc-rose dark:text-lsc-rose-light font-medium leading-none">
            {new Date(event.start_time).toLocaleDateString(getCurrentLocale(), { month: 'short' })}
          </span>
          <span className="text-base font-bold text-lsc-rose dark:text-lsc-cream leading-none mt-0.5">
            {new Date(event.start_time).getDate()}
          </span>
        </div>

        {/* Bookmark + Share buttons overlay */}
        <div className="absolute top-2 right-2 flex items-center gap-1">
          <button
            onClick={(e) => {
              e.stopPropagation()
              onToggleBookmark(event.id)
            }}
            className={`p-1.5 rounded-full transition-all focus:outline-none focus:ring-2 focus:ring-lsc-rose ${
              bookmarked
                ? 'bg-lsc-rose/20 text-lsc-rose hover:bg-lsc-rose/30'
                : 'bg-lsc-white/80 dark:bg-earth-800/80 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose opacity-0 group-hover:opacity-100 focus:opacity-100'
            }`}
            aria-label={bookmarked ? `Remove ${event.title} from saved events` : `Save ${event.title} for later`}
            aria-pressed={bookmarked}
          >
            <Bookmark
              aria-hidden="true"
              className={`w-3.5 h-3.5 ${bookmarked ? 'fill-current' : ''}`}
            />
          </button>
          {/* eslint-disable-next-line jsx-a11y/click-events-have-key-events */}
          <div onClick={(e) => e.stopPropagation()}>
            <ShareButton
              resourceType="event"
              resourceId={event.id}
              title={event.title}
              {...(event.description ? { description: event.description } : {})}
              date={event.start_time}
              {...(event.image_url ? { imageUrl: event.image_url } : {})}
              variant="compact"
              platforms={['copy_link', 'email']}
            />
          </div>
        </div>
      </div>

      {/* Card content */}
      <div className="p-3">
        {/* Time */}
        <div className="flex items-center gap-1 text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mb-1.5">
          <Clock aria-hidden="true" className="w-3.5 h-3.5" />
          {formatTime(event.start_time)}
        </div>

        {/* Title */}
        <h3 className="font-serif font-semibold text-sm text-lsc-dark dark:text-lsc-cream line-clamp-2 leading-snug mb-1.5" title={event.title}>
          {event.title}
        </h3>

        {/* Location */}
        {event.location && (
          <div className="flex items-center gap-1 text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
            <MapPin aria-hidden="true" className="w-3 h-3 flex-shrink-0" />
            <span className="truncate" title={event.location}>{event.location}</span>
          </div>
        )}

        {/* Bottom row: category pill + registered badge */}
        <div className="flex items-center gap-2 flex-wrap">
          {event.category && (
            <span className={`text-xs px-2 py-0.5 rounded font-medium ${getCategoryColorClasses(event.category)}`}>
              {getCategoryDisplayName(event.category)}
            </span>
          )}
          {registered && (
            <span className="text-xs px-2 py-0.5 rounded font-semibold bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-300">
              Registered
            </span>
          )}
        </div>
      </div>
    </div>
  )
}

export default function HorizontalEventCarousel({
  events,
  onEventClick,
  onToggleBookmark,
  isBookmarked,
  isRegistered,
}: HorizontalEventCarouselProps): React.ReactElement | null {
  const scrollRef = useRef<HTMLDivElement>(null)
  const [canScrollLeft, setCanScrollLeft] = useState(false)
  const [canScrollRight, setCanScrollRight] = useState(true)
  const { settings } = useAccessibility()

  const updateScrollButtons = useCallback(() => {
    const el = scrollRef.current
    if (!el) return
    setCanScrollLeft(el.scrollLeft > 0)
    setCanScrollRight(el.scrollLeft + el.clientWidth < el.scrollWidth - 1)
  }, [])

  const scroll = useCallback((direction: 'left' | 'right') => {
    const el = scrollRef.current
    if (!el) return
    const offset = direction === 'left' ? -SCROLL_AMOUNT : SCROLL_AMOUNT
    el.scrollBy({
      left: offset,
      behavior: settings.reduceMotion ? 'auto' : 'smooth',
    })
  }, [settings.reduceMotion])

  if (events.length === 0) return null

  return (
    <div className="relative" role="region" aria-roledescription="carousel" aria-label={t('aria.events.recommendedEventsCarousel')}>
      {/* Left arrow */}
      {canScrollLeft && (
        <button
          onClick={() => scroll('left')}
          className="absolute left-0 top-1/2 -translate-y-1/2 z-10 w-9 h-9 flex items-center justify-center rounded-full bg-lsc-white dark:bg-earth-700 shadow-md text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-600 transition-colors -ml-3"
          aria-label={t('aria.events.scrollLeft')}
        >
          <ChevronLeft className="w-5 h-5" aria-hidden="true" />
        </button>
      )}

      {/* Right arrow */}
      {canScrollRight && (
        <button
          onClick={() => scroll('right')}
          className="absolute right-0 top-1/2 -translate-y-1/2 z-10 w-9 h-9 flex items-center justify-center rounded-full bg-lsc-white dark:bg-earth-700 shadow-md text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-600 transition-colors -mr-3"
          aria-label={t('aria.events.scrollRight')}
        >
          <ChevronRight className="w-5 h-5" aria-hidden="true" />
        </button>
      )}

      {/* Scrollable container */}
      <div
        ref={scrollRef}
        onScroll={updateScrollButtons}
        className="flex gap-4 overflow-x-auto scrollbar-hide scroll-smooth px-1 py-2"
        role="list"
      >
        {events.map(event => (
          <CarouselCard
            key={event.id}
            event={event}
            onEventClick={onEventClick}
            onToggleBookmark={onToggleBookmark}
            bookmarked={isBookmarked(event.id)}
            registered={isRegistered(event.id)}
          />
        ))}
      </div>
    </div>
  )
}

/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * EventCard - Displays a single event with bookmark functionality
 * Used in the main events list and personalized sections
 */
import { Clock, MapPin, Users, UserPlus, Bookmark } from 'lucide-react'
import type { Event } from '@/api/api'
import { getCurrentLocale } from '@/i18n'

interface EventCardProps {
  event: Event
  onRegister: (event: Event) => void
  onClick: () => void
  isBookmarked?: boolean
  onToggleBookmark?: (eventId: number) => void
  isRegistered?: boolean
  showBookmark?: boolean
}

function formatTime(dateStr: string): string {
  const date = new Date(dateStr)
  return date.toLocaleTimeString(getCurrentLocale(), {
    hour: 'numeric',
    minute: '2-digit',
  })
}

export default function EventCard({
  event,
  onRegister,
  onClick,
  isBookmarked = false,
  onToggleBookmark,
  isRegistered = false,
  showBookmark = true,
}: EventCardProps): React.ReactElement {
  const spotsInfo = event.max_attendees !== null
    ? event.spots_remaining === 0
      ? 'Full (you can join the waitlist)'
      : `${event.spots_remaining} of ${event.max_attendees} spots available`
    : null

  const handleBookmarkClick = (e: React.MouseEvent) => {
    e.stopPropagation()
    onToggleBookmark?.(event.id)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      onClick()
    }
  }

  return (
    <div
      className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm p-5 hover:shadow-md transition-shadow cursor-pointer relative group focus-within:ring-2 focus-within:ring-lsc-rose"
      onClick={onClick}
      onKeyDown={handleKeyDown}
      role="button"
      tabIndex={0}
      aria-label={`View details for ${event.title}`}
    >
      {/* Bookmark button */}
      {showBookmark && onToggleBookmark && !(event.registration_required && !isRegistered) && (
        <button
          onClick={handleBookmarkClick}
          className={`absolute top-3 right-3 p-2 rounded-full transition-all focus:outline-none focus:ring-2 focus:ring-lsc-rose ${
            isBookmarked
              ? 'bg-lsc-rose/20 text-lsc-rose hover:bg-lsc-rose/30'
              : 'bg-lsc-cream/80 dark:bg-earth-700/80 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose hover:bg-lsc-cream dark:hover:bg-earth-700'
          }`}
          aria-label={isBookmarked ? `Remove ${event.title} from saved events` : `Save ${event.title} for later`}
          aria-pressed={isBookmarked}
        >
          <Bookmark
            aria-hidden="true"
            className={`w-4 h-4 ${isBookmarked ? 'fill-current' : ''}`}
          />
        </button>
      )}

      <div className="flex flex-col sm:flex-row gap-4">
        {/* Top row: Date badge + Content */}
        <div className="flex gap-4 flex-1 min-w-0">
          <div className="text-center flex-shrink-0">
            <div className="w-14 h-14 sm:w-16 sm:h-16 bg-lsc-cream dark:bg-earth-800 rounded-xl flex flex-col items-center justify-center">
              <span className="text-xs text-lsc-rose dark:text-lsc-rose-light font-medium">
                {new Date(event.start_time).toLocaleDateString(getCurrentLocale(), { month: 'short' })}
              </span>
              <span className="text-lg sm:text-xl font-bold text-lsc-rose dark:text-lsc-cream">
                {new Date(event.start_time).getDate()}
              </span>
            </div>
          </div>
          <div className="flex-1 min-w-0 pr-8">
            <h3 className="font-serif font-semibold text-base sm:text-lg text-lsc-dark dark:text-lsc-cream line-clamp-2" title={event.title}>
              {event.title}
            </h3>
            <div className="flex flex-wrap gap-2 sm:gap-3 mt-2 text-xs sm:text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
              <span className="flex items-center gap-1">
                <Clock aria-hidden="true" className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
                {formatTime(event.start_time)}
              </span>
              {event.location && (
                <span className="flex items-center gap-1">
                  <MapPin aria-hidden="true" className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
                  <span className="truncate max-w-[120px] sm:max-w-none">{event.location}</span>
                </span>
              )}
              {event.audience && (
                <span className="flex items-center gap-1">
                  <Users aria-hidden="true" className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
                  {event.audience}
                </span>
              )}
            </div>
            {event.description && (
              <p className="text-xs sm:text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-2 line-clamp-2" title={event.description}>
                {event.description}
              </p>
            )}
            <div className="flex flex-wrap items-center gap-2 mt-3">
              {event.category && (
                <span className="text-xs px-2 py-1 bg-lsc-cream dark:bg-lsc-dark text-lsc-rose dark:text-earth-300 rounded">
                  {event.category}
                </span>
              )}
              {spotsInfo && (
                <span className={`text-xs px-2 py-1 rounded ${
                  event.spots_remaining === 0
                    ? 'bg-lsc-cream dark:bg-lsc-dark/30 text-lsc-rose dark:text-lsc-rose-light'
                    : 'bg-lsc-cream dark:bg-earth-800/30 text-lsc-rose dark:text-lsc-rose-light'
                }`}>
                  {spotsInfo}
                </span>
              )}
              {event.registration_count > 0 && (
                <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                  {event.registration_count} registered
                </span>
              )}
              {isRegistered && (
                <span className="text-xs px-2 py-1 rounded bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-300 font-medium">
                  You're registered
                </span>
              )}
            </div>
          </div>
        </div>
        {/* Register button - full width on mobile, inline on desktop */}
        {event.registration_required && !isRegistered && (
          <div className="flex-shrink-0 sm:self-start">
            <button
              onClick={(e) => {
                e.stopPropagation()
                onRegister(event)
              }}
              className={`flex items-center justify-center gap-2 w-full sm:w-auto px-4 py-2.5 sm:py-2 min-h-[44px] rounded-xl text-sm font-semibold shadow-md hover:shadow-lg active:shadow-sm transition-all touch-manipulation ${
                event.spots_remaining === 0
                  ? 'bg-lsc-cream hover:bg-lsc-border dark:bg-lsc-dark/30 dark:hover:bg-lsc-dark/50 text-lsc-rose dark:text-lsc-rose-light border-2 border-lsc-rose'
                  : 'bg-lsc-rose hover:bg-lsc-rose/90 text-white'
              }`}
            >
              <UserPlus aria-hidden="true" className="w-4 h-4" />
              {event.spots_remaining === 0 ? 'Waitlist' : 'Register'}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

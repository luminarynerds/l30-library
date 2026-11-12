/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * SavedEventsSection - Shows user's bookmarked/saved events
 *
 * Fetches each bookmarked event by id independently of the active
 * filter/pagination so saved items never silently disappear when the
 * user scrolls the page list or changes filters. Bookmarks that 404
 * (event deleted server-side) are silently dropped from local
 * personalization storage.
 */
import { Bookmark, ChevronRight, ChevronDown, Trash2 } from "lucide-react"
import { useEffect, useMemo, useState } from "react"
import { useQueries } from "@tanstack/react-query"
import { getEventById, type Event } from "@/api/events-api"
import { isApiError } from "@/lib/api-client"
import { t, getCurrentLocale } from "@/i18n"
import EventCard from "./EventCard"

interface SavedEventsSectionProps {
  bookmarkedEventIds: number[]
  onToggleBookmark: (eventId: number) => void
  onRemoveBookmark: (eventId: number) => void
  onViewEvent: (event: Event) => void
  onRegister: (event: Event) => void
  isRegistered: (eventId: number) => boolean
}

export default function SavedEventsSection({
  bookmarkedEventIds,
  onToggleBookmark,
  onRemoveBookmark,
  onViewEvent,
  onRegister,
  isRegistered,
}: SavedEventsSectionProps): React.ReactElement | null {
  const [isExpanded, setIsExpanded] = useState(true)

  // Stable, sorted id list -> stable React Query keys (avoids needless
  // re-renders when the bookmarks array reference changes but ids don't).
  const sortedIds = useMemo(
    () => [...bookmarkedEventIds].sort((a, b) => a - b),
    [bookmarkedEventIds]
  )

  const queries = useQueries({
    queries: sortedIds.map(id => ({
      queryKey: ["event", "byId", id] as const,
      queryFn: () => getEventById(id),
      staleTime: 5 * 60 * 1000,
      retry: (failureCount: number, error: unknown) => {
        // Don't retry 404s — the event is gone.
        if (isApiError(error) && error.status === 404) return false
        return failureCount < 2
      },
    })),
  })

  // Silently drop bookmarks that 404 on the server.
  useEffect(() => {
    queries.forEach((q, idx) => {
      const id = sortedIds[idx]
      if (id === undefined) return
      if (q.error && isApiError(q.error) && q.error.status === 404) {
        onRemoveBookmark(id)
      }
    })
  }, [queries, sortedIds, onRemoveBookmark])

  const savedEvents: Event[] = queries
    .map(q => q.data)
    .filter((e): e is Event => Boolean(e))

  // Sort by date, putting upcoming events first
  const sortedEvents = [...savedEvents].sort((a, b) =>
    new Date(a.start_time).getTime() - new Date(b.start_time).getTime()
  )

  // Separate past and upcoming
  const now = new Date()
  const upcomingEvents = sortedEvents.filter(e => new Date(e.start_time) > now)
  const pastEvents = sortedEvents.filter(e => new Date(e.start_time) <= now)

  // Empty state: no bookmarked ids at all.
  if (bookmarkedEventIds.length === 0) {
    return (
      <section
        aria-labelledby="saved-events-heading"
        className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm p-4 sm:p-5"
      >
        <div className="flex items-center gap-3 mb-2">
          <div className="p-2 bg-lsc-rose/10 dark:bg-lsc-rose/20 rounded-xl">
            <Bookmark
              aria-hidden="true"
              className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light"
            />
          </div>
          <h2
            id="saved-events-heading"
            className="text-lg font-serif font-semibold text-lsc-dark dark:text-lsc-cream"
          >
            {t("events.savedSection.title")}
          </h2>
        </div>
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
          {t("events.savedSection.emptyState")}
        </p>
      </section>
    )
  }

  // We have bookmarked ids but none resolved yet (all loading, or all 404'd).
  if (savedEvents.length === 0) {
    return null
  }

  return (
    <section
      aria-labelledby="saved-events-heading"
      className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm overflow-hidden"
    >
      {/* Header - clickable to expand/collapse */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between p-4 sm:p-5 hover:bg-lsc-cream/50 dark:hover:bg-earth-700/50 transition-colors"
        aria-expanded={isExpanded}
        aria-controls="saved-events-content"
      >
        <div className="flex items-center gap-3">
          <div className="p-2 bg-lsc-rose/10 dark:bg-lsc-rose/20 rounded-xl">
            <Bookmark
              aria-hidden="true"
              className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light"
            />
          </div>
          <div className="text-left">
            <h2
              id="saved-events-heading"
              className="text-lg font-serif font-semibold text-lsc-dark dark:text-lsc-cream"
            >
              {t("events.savedSection.title")}
            </h2>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
              {savedEvents.length} event{savedEvents.length !== 1 ? "s" : ""} saved for later
            </p>
          </div>
        </div>
        {isExpanded ? (
          <ChevronDown aria-hidden="true" className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
        ) : (
          <ChevronRight aria-hidden="true" className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
        )}
      </button>

      {/* Content */}
      {isExpanded && (
        <div
          id="saved-events-content"
          className="px-4 sm:px-5 pb-4 sm:pb-5 space-y-4"
        >
          {/* Upcoming saved events */}
          {upcomingEvents.length > 0 && (
            <div className="space-y-3">
              {upcomingEvents.map(event => (
                <EventCard
                  key={event.id}
                  event={event}
                  onRegister={onRegister}
                  onClick={() => onViewEvent(event)}
                  isBookmarked={true}
                  onToggleBookmark={onToggleBookmark}
                  isRegistered={isRegistered(event.id)}
                />
              ))}
            </div>
          )}

          {/* Past saved events */}
          {pastEvents.length > 0 && (
            <div className="pt-2">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">
                  Past Events ({pastEvents.length})
                </h3>
                <button
                  onClick={() => pastEvents.forEach(e => onToggleBookmark(e.id))}
                  className="flex items-center gap-1 text-xs text-status-danger-600 dark:text-status-danger-400 hover:text-status-danger-700 dark:hover:text-status-danger-300"
                >
                  <Trash2 aria-hidden="true" className="w-3 h-3" />
                  Clear past
                </button>
              </div>
              <div className="space-y-2 opacity-60">
                {pastEvents.slice(0, 3).map(event => (
                  <div
                    key={event.id}
                    className="flex items-center justify-between p-3 bg-lsc-cream/50 dark:bg-earth-700/50 rounded-xl"
                  >
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream truncate" title={event.title}>
                        {event.title}
                      </p>
                      <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                        {new Date(event.start_time).toLocaleDateString(getCurrentLocale(), {
                          month: "short",
                          day: "numeric",
                          year: "numeric",
                        })}
                      </p>
                    </div>
                    <button
                      onClick={() => onToggleBookmark(event.id)}
                      className="p-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-status-danger-600 dark:hover:text-status-danger-400 transition-colors"
                      aria-label={`Remove ${event.title} from saved`}
                    >
                      <Trash2 aria-hidden="true" className="w-4 h-4" />
                    </button>
                  </div>
                ))}
                {pastEvents.length > 3 && (
                  <p className="text-xs text-center text-lsc-dark/70 dark:text-lsc-cream/70">
                    And {pastEvents.length - 3} more...
                  </p>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </section>
  )
}

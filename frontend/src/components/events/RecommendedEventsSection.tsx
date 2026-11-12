/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * RecommendedEventsSection - Shows personalized event recommendations
 *
 * Fetches its own upcoming-events page independently of the active
 * filter/pagination so recommended events never silently disappear
 * when the user filters the main list. Filters client-side by the
 * user's preferences.
 */
import { Sparkles, Settings } from "lucide-react"
import { useQuery } from "@tanstack/react-query"
import { getEvents, type Event } from "@/api/events-api"
import type { EventPreferences } from "@/hooks/useEventPersonalization"
import HorizontalEventCarousel from "./HorizontalEventCarousel"
import { t } from "@/i18n"

interface RecommendedEventsSectionProps {
  preferences: EventPreferences
  matchesPreferences: (category: string | null, audience: string | null) => boolean
  onToggleBookmark: (eventId: number) => void
  isBookmarked: (eventId: number) => boolean
  onViewEvent: (event: Event) => void
  onRegister: (event: Event) => void
  isRegistered: (eventId: number) => boolean
  onOpenPreferences: () => void
}

const RECOMMENDED_FETCH_LIMIT = 50
const RECOMMENDED_DISPLAY_LIMIT = 6

export default function RecommendedEventsSection({
  preferences,
  matchesPreferences,
  onToggleBookmark,
  isBookmarked,
  onViewEvent,
  onRegister,
  isRegistered,
  onOpenPreferences,
}: RecommendedEventsSectionProps): React.ReactElement | null {
  // Check if user has any preferences set
  const hasPreferences = preferences.categories.length > 0 || preferences.audiences.length > 0

  // Fetch upcoming events independently of the page's active filters.
  // staleTime keeps the query warm across filter/pagination changes.
  const { data } = useQuery({
    queryKey: ["events", "recommended", "upcoming"],
    queryFn: () => getEvents({ upcoming: true, per_page: RECOMMENDED_FETCH_LIMIT }),
    staleTime: 5 * 60 * 1000,
    enabled: hasPreferences,
  })

  if (!hasPreferences) {
    // Show a prompt to set preferences
    return (
      <section
        aria-labelledby="for-you-heading"
        className="bg-gradient-to-r from-category-50 to-blue-50 dark:from-category-900/20 dark:to-blue-900/20 rounded-xl p-4 sm:p-6"
      >
        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
          <div className="p-3 bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm">
            <Sparkles
              aria-hidden="true"
              className="w-6 h-6 text-category-500 dark:text-category-400"
            />
          </div>
          <div className="flex-1">
            <h2
              id="for-you-heading"
              className="text-lg font-serif font-semibold text-lsc-dark dark:text-lsc-cream"
            >
              Get Personalized Recommendations
            </h2>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
              Tell us what you're interested in and we'll show you events tailored just for you.
            </p>
          </div>
          <button
            onClick={onOpenPreferences}
            className="flex items-center gap-2 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl font-medium transition-colors whitespace-nowrap"
          >
            <Settings aria-hidden="true" className="w-4 h-4" />
            Set Preferences
          </button>
        </div>
      </section>
    )
  }

  const allEvents: Event[] = data?.data ?? []

  // Filter events that match user preferences
  const recommendedEvents = allEvents.filter(event =>
    matchesPreferences(event.category, event.audience)
  )

  // Only show upcoming events
  const now = new Date()
  const upcomingRecommended = recommendedEvents
    .filter(event => new Date(event.start_time) > now)
    .slice(0, RECOMMENDED_DISPLAY_LIMIT)

  if (upcomingRecommended.length === 0) {
    return (
      <section
        aria-labelledby="for-you-heading"
        className="bg-gradient-to-r from-category-50 to-blue-50 dark:from-category-900/20 dark:to-blue-900/20 rounded-xl p-4 sm:p-6"
      >
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm">
              <Sparkles
                aria-hidden="true"
                className="w-5 h-5 text-category-500 dark:text-category-400"
              />
            </div>
            <div>
              <h2
                id="for-you-heading"
                className="text-lg font-serif font-semibold text-lsc-dark dark:text-lsc-cream"
              >
                {t("events.recommendedSection.title")}
              </h2>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                Based on your interests
              </p>
            </div>
          </div>
          <button
            onClick={onOpenPreferences}
            className="p-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose dark:hover:text-lsc-rose-light hover:bg-lsc-white dark:bg-earth-800 dark:hover:bg-earth-800 rounded-lg transition-colors"
            aria-label={t("aria.events.editPreferences")}
          >
            <Settings aria-hidden="true" className="w-5 h-5" />
          </button>
        </div>
        <div className="text-center py-6">
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
            {t("events.recommendedSection.emptyState")}
          </p>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
            Check back later or adjust your preferences to see more events.
          </p>
          <button
            onClick={onOpenPreferences}
            className="mt-4 text-sm text-lsc-rose dark:text-lsc-rose-light hover:underline font-medium"
          >
            Update preferences
          </button>
        </div>
      </section>
    )
  }

  // Show preference tags for context
  const preferenceTags = [
    ...preferences.categories,
    ...preferences.audiences,
  ]

  return (
    <section
      aria-labelledby="for-you-heading"
      className="bg-gradient-to-r from-category-50 to-blue-50 dark:from-category-900/20 dark:to-blue-900/20 rounded-xl p-4 sm:p-6"
    >
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm">
            <Sparkles
              aria-hidden="true"
              className="w-5 h-5 text-category-500 dark:text-category-400"
            />
          </div>
          <div>
            <h2
              id="for-you-heading"
              className="text-lg font-serif font-semibold text-lsc-dark dark:text-lsc-cream"
            >
              {t("events.recommendedSection.title")}
            </h2>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
              {upcomingRecommended.length} event{upcomingRecommended.length !== 1 ? "s" : ""} matching your interests
            </p>
          </div>
        </div>
        <button
          onClick={onOpenPreferences}
          className="p-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose dark:hover:text-lsc-rose-light hover:bg-lsc-white dark:bg-earth-800 dark:hover:bg-earth-800 rounded-lg transition-colors"
          aria-label={t("aria.events.editPreferences")}
        >
          <Settings aria-hidden="true" className="w-5 h-5" />
        </button>
      </div>

      {/* Show active preference tags */}
      <div className="flex flex-wrap gap-2 mb-4">
        {preferenceTags.map(tag => (
          <span
            key={tag}
            className="text-xs px-2 py-1 bg-lsc-white/70 dark:bg-earth-800/70 text-category-600 dark:text-category-300 rounded-full"
          >
            {tag}
          </span>
        ))}
      </div>

      {/* Recommended events carousel */}
      <HorizontalEventCarousel
        events={upcomingRecommended}
        onEventClick={onViewEvent}
        onRegister={onRegister}
        onToggleBookmark={onToggleBookmark}
        isBookmarked={isBookmarked}
        isRegistered={isRegistered}
      />
    </section>
  )
}

/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useCallback, useMemo, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Calendar, Printer, Bookmark, Settings } from 'lucide-react'
import { getEvents, getEventTags, cancelRegistration, type Event } from '@/api/api'
import { getEventCategories, getEventAudiences } from '@/api/events-api'
import { useTranslation } from '@/i18n/I18nContext'
import RegistrationModal from '@/components/RegistrationModal'
import SeriesRegistrationModal from '@/components/SeriesRegistrationModal'
import EventDetailModal from '@/components/EventDetailModal'
import EventFilters from '@/components/EventFilters'
import EventCalendarView, { type CalendarViewMode } from '@/components/EventCalendarView'
import EventAgendaView from '@/components/EventAgendaView'
import PrintableCalendar from '@/components/PrintableCalendar'
import { EventCardSkeletonList } from '@/components/skeletons/EventCardSkeleton'
import { useDebounce } from '@/hooks/useDebounce'
import { useEventPersonalization } from '@/hooks/useEventPersonalization'
import { MyEventsSection, SavedEventsSection, RecommendedEventsSection, EventPreferencesModal } from '@/components/events'
import toast from 'react-hot-toast'
import { EMPTY_STATE_KEYS, getRandomLoadingMessageKey } from '@/constants/brandMessages'
import { groupEventsBySeries, type SeriesGroup } from '@/pages/events/utils/eventsPageUtils'
import { useEventsPageState } from '@/pages/events/hooks/useEventsPageState'
import { useEventsFilterUrlSync } from '@/pages/events/hooks/useEventsFilterUrlSync'
import ViewToggle from './ViewToggle'
import ExportEventsButton from './ExportEventsButton'
import EventCard from './EventCard'
import FeaturedEventHero from './FeaturedEventHero'
import FeaturedEventsSection from './FeaturedEventsSection'
import HappeningNowSection from './HappeningNowSection'
import SeriesEventGroup from './SeriesEventGroup'
import StickyFilterBar from './StickyFilterBar'
import EventQuickChips from './EventQuickChips'
import ThisWeekStrip from './ThisWeekStrip'
import { useAccessibility } from '@/features/accessibility/hooks/useAccessibility'

// eslint-disable-next-line complexity
export default function EventsPage(): React.ReactElement {
  const { t } = useTranslation()
  const { seriesSlug } = useParams<{ seriesSlug?: string }>()
  const queryClient = useQueryClient()
  const {
    selectedEvent,
    setSelectedEvent,
    detailEvent,
    setDetailEvent,
    filters,
    setFilters,
    viewMode,
    setViewMode,
    showPastEvents,
    setShowPastEvents,
    showPrintModal,
    setShowPrintModal,
    showPreferencesModal,
    setShowPreferencesModal,
    selectedDate,
    setSelectedDate,
    showMiniCalendar,
    setShowMiniCalendar,
  } = useEventsPageState(seriesSlug)

  const { settings } = useAccessibility()
  const filterSectionRef = useRef<HTMLDivElement>(null)

  // Series chosen for the "register for all sessions" flow.
  const [selectedSeries, setSelectedSeries] = useState<SeriesGroup | null>(null)

  // URL <-> filter state sync (deep links + history). This hook is the single
  // owner of URL <-> filter sync for every param; the quick chips and filter
  // panel only set state. Returns an initial active-filter-count snapshot used
  // for the mobile-collapse decision below.
  const { initialActiveFilterCount } = useEventsFilterUrlSync({
    filters,
    setFilters,
    showPastEvents,
    setShowPastEvents,
  })

  // Mobile-collapse for the EventFilters panel. Computed synchronously at
  // first render so initial paint matches reality (no collapsed-then-snap-
  // open flash). On md+ or when any filter is active on URL load, start
  // expanded.
  const [filtersInitialCollapsed] = useState(() => {
    if (typeof window === 'undefined') return false
    const isMobile = window.matchMedia('(max-width: 767px)').matches
    return isMobile && initialActiveFilterCount === 0
  })

  // Count active filters (non-empty, non-pagination values)
  const activeFilterCount = useMemo(() => {
    return Object.entries(filters).filter(([key, value]) => {
      if (key === 'page' || key === 'per_page' || key === 'upcoming') return false
      return value !== undefined && value !== '' && value !== null
    }).length
  }, [filters])

  const scrollToFilters = useCallback(() => {
    filterSectionRef.current?.scrollIntoView({
      behavior: settings.reduceMotion ? 'auto' : 'smooth',
    })
  }, [settings.reduceMotion])

  // Event personalization hook for local storage of registrations, bookmarks, and preferences
  const personalization = useEventPersonalization()

  // Cancel registration mutation
  const cancelRegistrationMutation = useMutation({
    mutationFn: ({ eventId, registrationId, email }: { eventId: number; registrationId: number; email: string }) =>
      cancelRegistration(eventId, registrationId, email),
    onSuccess: (_, { eventId }) => {
      personalization.removeRegistration(eventId)
      queryClient.invalidateQueries({ queryKey: ['events'] })
      toast.success(t('toast.eventsContent.registrationCancelledSuccessfully'))
    },
    onError: () => {
      toast.error(t('eventsPageContent.failedToCancelRegistrationPlease'))
    },
  })

  // Handler for cancelling a registration
  const handleCancelRegistration = useCallback((eventId: number, registrationId: number) => {
    if (!personalization.userEmail) {
      toast.error(t('eventsPageContent.emailNotFoundPleaseRegister'))
      return
    }
    cancelRegistrationMutation.mutate({
      eventId,
      registrationId,
      email: personalization.userEmail,
    })
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cancelRegistrationMutation, personalization.userEmail])

  const handleDateSelect = useCallback((date: Date) => {
    setSelectedDate(date)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Get calendar view mode for EventCalendarView
  const calendarViewMode: CalendarViewMode = viewMode === 'calendar-week' ? 'week' : 'month'

  // Determine if we should show the mini calendar toggle
  const isCalendarView = viewMode === 'calendar-month' || viewMode === 'calendar-week'

  // Fetch available tags for filtering
  const { data: availableTags = [] } = useQuery({
    queryKey: ['event-tags'],
    queryFn: getEventTags,
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
  })

  // Fetch available categories for filtering
  const { data: availableCategories = [] } = useQuery({
    queryKey: ['event-categories'],
    queryFn: getEventCategories,
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
  })

  // Fetch available audiences for filtering
  const { data: availableAudiences = [] } = useQuery({
    queryKey: ['event-audiences'],
    queryFn: getEventAudiences,
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
  })

  // Debounce the search portion of filters so we do not refetch / re-announce on every keystroke.
  // 300ms balances responsiveness vs. screen-reader announcement churn.
  const debouncedSearch = useDebounce(filters.search ?? "", 300)

  // Compute effective filters based on past events toggle.
  // Non-search filters (category, audience, tag) apply immediately; only the
  // free-text search is debounced because thats where keystroke-rate refetches hurt.
  const effectiveFilters = useMemo(() => {
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const { search: _search, ...rest } = filters
    return {
      ...rest,
      ...(debouncedSearch ? { search: debouncedSearch } : {}),
      upcoming: !showPastEvents,
      // Backend caps page_size at 100; without this the API defaults to 20
      // and list/calendar/print/export silently drop events past the first page.
      per_page: 100,
    }
  }, [filters, debouncedSearch, showPastEvents])

  const { data, isLoading, isFetching, error } = useQuery({
    queryKey: ['events', effectiveFilters],
    queryFn: () => getEvents(effectiveFilters),
  })

  // Determine if an event is in the past
  const isPastEvent = useCallback((event: Event) => {
    return new Date(event.start_time) < new Date()
  }, [])

  // Language codes present on loaded events. Derived client-side (no
  // /events/languages endpoint exists); when a language filter is active the
  // option list shrinks to the matching events, but the active-filter pills
  // keep the selected codes removable. Sorted for stable chip order.
  const availableLanguages = useMemo(() => {
    if (!data) return []
    const codes = new Set<string>()
    for (const e of data.data) {
      if (e.event_language) codes.add(e.event_language)
    }
    return Array.from(codes).sort()
  }, [data])

  // Branches hosting the loaded events, derived client-side like languages
  // (branch_id + branch_name ride on the event payload). Selected ids stay
  // in the list even when filtering shrinks results to one branch, so the
  // facet remains visible and toggleable. The facet itself renders only when
  // 2+ branches are present (single-branch libraries never see it).
  const availableBranches = useMemo(() => {
    const byId = new Map<number, string>()
    for (const e of data?.data ?? []) {
      if (e.branch_id != null) byId.set(e.branch_id, e.branch_name ?? `#${e.branch_id}`)
    }
    for (const id of filters.branch_ids ?? []) {
      if (!byId.has(id)) byId.set(id, `#${id}`)
    }
    return Array.from(byId.entries())
      .map(([id, name]) => ({ id, name }))
      .sort((a, b) => a.name.localeCompare(b.name))
  }, [data, filters.branch_ids])

  // Find the first staff-featured event for the hero banner (list view, upcoming only)
  const heroEvent = useMemo(() => {
    if (showPastEvents || viewMode !== 'list') return null
    if (!data) return null
    return data.data.find(e => e.is_featured) ?? null
  }, [data, showPastEvents, viewMode])

  // Collect IDs of events shown in the "For You" carousel so they can be excluded from the main list
  const recommendedEventIds = useMemo(() => {
    if (showPastEvents || !data) return new Set<number>()
    const { categories = [], audiences = [] } = personalization.preferences
    if (categories.length === 0 && audiences.length === 0) return new Set<number>()
    const now = new Date()
    return new Set(
      data.data
        .filter(e => personalization.matchesPreferences(e.category, e.audience))
        .filter(e => new Date(e.start_time) > now)
        .slice(0, 6)
        .map(e => e.id)
    )
  }, [data, showPastEvents, personalization])

  return (
    <div className="space-y-6 events-page-container">
      {/* Utility controls */}
      <div className="flex flex-wrap items-center gap-2 justify-center md:justify-end">
          {/* Export button */}
          {data && data.data.length > 0 && <ExportEventsButton events={data.data} />}

          {/* Print button */}
          <button
            onClick={() => setShowPrintModal(true)}
            className="flex items-center gap-2 px-3 py-2 min-h-[44px] rounded-xl text-sm font-medium bg-lsc-cream dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream/80 hover:bg-lsc-border dark:hover:bg-lsc-brown/90 border-2 border-lsc-border dark:border-lsc-brown transition-all focus:outline-none focus:ring-2 focus:ring-lsc-rose shadow-sm hover:shadow touch-manipulation"
            aria-label={t('events.printCalendar')}
          >
            <Printer className="w-4 h-4" aria-hidden="true" />
            <span className="hidden sm:inline">{t('events.printCalendar')}</span>
          </button>

          {/* Preferences button */}
          <button
            onClick={() => setShowPreferencesModal(true)}
            className="flex items-center gap-2 px-3 py-2 min-h-[44px] rounded-xl text-sm font-medium bg-lsc-cream dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream/80 hover:bg-lsc-border dark:hover:bg-lsc-brown/90 border-2 border-lsc-border dark:border-lsc-brown transition-all focus:outline-none focus:ring-2 focus:ring-lsc-rose shadow-sm hover:shadow touch-manipulation"
            aria-label={t('events.preferences')}
          >
            <Settings className="w-4 h-4" aria-hidden="true" />
            <span className="hidden sm:inline">{t('events.preferences')}</span>
          </button>

          {/* Saved events indicator */}
          {personalization.bookmarksCount > 0 && (
            <div className="flex items-center gap-2 px-3 py-2 bg-lsc-rose/10 dark:bg-lsc-rose/20 rounded-xl text-sm font-medium text-lsc-rose dark:text-lsc-rose-light">
              <Bookmark className="w-4 h-4 fill-current" aria-hidden="true" />
              <span>{t('events.saved', { count: personalization.bookmarksCount })}</span>
            </div>
          )}

      </div>

      {/* View controls row */}
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-2 flex-wrap">
          {/* Mini calendar toggle for calendar views */}
          {isCalendarView && (
            <label className="flex items-center gap-2 text-sm text-lsc-dark dark:text-lsc-cream cursor-pointer mr-2">
              <input
                type="checkbox"
                checked={showMiniCalendar}
                onChange={(e) => setShowMiniCalendar(e.target.checked)}
                className="w-4 h-4 rounded border-lsc-border dark:border-earth-700 text-lsc-rose focus:ring-lsc-rose"
              />
              <span className="hidden sm:inline">{t('events.miniCalendar')}</span>
              <span className="sm:hidden">{t('events.miniCalShort')}</span>
            </label>
          )}
        </div>

        {/* View toggle */}
        <ViewToggle viewMode={viewMode} onChange={setViewMode} />
      </div>

      {/* Today & this week — HappeningNow + the day strip merged into one
          band (one section, one heading) so the stack above the first event
          card stays short. Promoted above filters so a patron on mobile sees
          today's storytime in the first viewport. Suppressed in linear view
          (a promotional rail). */}
      {viewMode !== 'linear' && (
        <section
          aria-labelledby="today-week-heading"
          className="rounded-xl border-2 border-lsc-border dark:border-earth-700 bg-lsc-cream/30 dark:bg-earth-800/40 p-4 space-y-4"
        >
          <h2 id="today-week-heading" className="text-lg font-serif font-bold text-lsc-dark dark:text-lsc-cream">
            {t('events.todayThisWeek', 'Today & this week')}
          </h2>
          {data && !showPastEvents && (
            <HappeningNowSection
              events={data.data}
              onEventClick={setDetailEvent}
              onRegister={setSelectedEvent}
              embedded
            />
          )}
          <ThisWeekStrip
            events={data?.data ?? []}
            isLoading={isLoading}
            scrollTargetRef={filterSectionRef}
            embedded
          />
        </section>
      )}

      {/* Quick chips (when/audience/drop-in) — first-tier filtering. */}
      <EventQuickChips filters={filters} setFilters={setFilters} />

      {/* Sticky filter bar (shows when the inline filter section scrolls
          out of view — always-accessible escape hatch on mobile). */}
      <StickyFilterBar
        filterRef={filterSectionRef}
        activeFilterCount={activeFilterCount}
        searchQuery={filters.search || ''}
        onClearFilters={() => setFilters({})}
        onExpandFilters={scrollToFilters}
      />

      {/* Filters — collapsed by default on mobile when no filter is active
          on URL load; expanded on md+. The internal panel still allows a
          manual collapse/expand toggle via its own header button. */}
      <div ref={filterSectionRef}>
        <EventFilters
          filters={filters}
          onChange={setFilters}
          showPastEvents={showPastEvents}
          onTogglePastEvents={setShowPastEvents}
          availableTags={availableTags}
          availableCategories={availableCategories}
          availableAudiences={availableAudiences}
          availableLanguages={availableLanguages}
          availableBranches={availableBranches}
          initialCollapsed={filtersInitialCollapsed}
        />
      </div>

      {/* Featured Event Hero Banner */}
      {heroEvent && (
        <FeaturedEventHero
          event={heroEvent}
          onEventClick={(e) => setDetailEvent(e)}
          onRegister={(e) => setSelectedEvent(e)}
          isRegistered={personalization.isRegistered(heroEvent.id)}
        />
      )}

      {/* Personalized Sections - only show when not viewing past events.
          The three rails (Upcoming/Saved/Recommended) are collapsed inside a
          single "Your events" disclosure to keep the main list near the top
          of the page. Default-open only when the patron has any personalization
          data (registrations, bookmarks, or preferences).
          Suppressed in linear view alongside the other promotional rails. */}
      {!showPastEvents && !isLoading && data && viewMode !== 'linear' && (() => {
        const hasMyEvents = personalization.registrations.some(
          r => new Date(r.eventStartTime) > new Date() && r.status !== 'cancelled'
        )
        const hasSaved = personalization.bookmarksCount > 0
        const hasRecommended =
          personalization.preferences.categories.length > 0 ||
          personalization.preferences.audiences.length > 0
        const hasAny = hasMyEvents || hasSaved || hasRecommended
        if (!hasAny) return null
        return (
          <details
            open={hasAny}
            className="bg-lsc-cream/40 dark:bg-earth-800/40 rounded-xl border-2 border-lsc-border dark:border-earth-700 group"
          >
            <summary
              className="cursor-pointer list-none flex items-center justify-between gap-3 p-4 sm:p-5 rounded-xl focus:outline-none focus:ring-2 focus:ring-lsc-rose touch-manipulation"
              aria-label={t('events.yourEvents.title', 'Your events')}
            >
              <div className="flex items-center gap-3">
                <div className="p-2 bg-lsc-rose/15 dark:bg-lsc-rose/25 rounded-xl">
                  <Bookmark
                    aria-hidden="true"
                    className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light"
                  />
                </div>
                <h2 className="text-lg font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
                  {t('events.yourEvents.title', 'Your events')}
                </h2>
              </div>
              <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 group-open:hidden">
                {t('events.yourEvents.expand', 'Show')}
              </span>
              <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hidden group-open:inline">
                {t('events.yourEvents.collapse', 'Hide')}
              </span>
            </summary>

            <div className="px-4 sm:px-5 pb-4 sm:pb-5 space-y-6">
              {/* Saved (bookmarked) events */}
              <SavedEventsSection
                bookmarkedEventIds={personalization.bookmarks}
                onToggleBookmark={personalization.toggleBookmark}
                onRemoveBookmark={personalization.removeBookmark}
                onViewEvent={setDetailEvent}
                onRegister={setSelectedEvent}
                isRegistered={personalization.isRegistered}
              />

              {/* Upcoming registrations */}
              <MyEventsSection
                registrations={personalization.registrations}
                events={data.data}
                onCancelRegistration={handleCancelRegistration}
                onViewEvent={setDetailEvent}
                userEmail={personalization.userEmail}
              />

              {/* Recommended events (only when preferences are set) */}
              <RecommendedEventsSection
                preferences={personalization.preferences}
                matchesPreferences={personalization.matchesPreferences}
                onToggleBookmark={personalization.toggleBookmark}
                isBookmarked={personalization.isBookmarked}
                onViewEvent={setDetailEvent}
                onRegister={setSelectedEvent}
                isRegistered={personalization.isRegistered}
                onOpenPreferences={() => setShowPreferencesModal(true)}
              />
            </div>
          </details>
        )
      })()}

      {/* Screen reader announcement for event results and filter changes */}
      <div role="status" aria-live="polite" aria-atomic="true" className="sr-only">
        {isLoading
          ? t('events.status.loading', 'Loading events...')
          : data
            ? t('events.status.resultsFound', { count: data.data.length })
            : ''}
      </div>

      {isLoading && (
        <div className="space-y-4">
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{t(getRandomLoadingMessageKey())}</p>
          <EventCardSkeletonList count={5} />
        </div>
      )}

      {error && (
        <div className="text-center text-status-danger-700 dark:text-status-danger-300 py-12" role="alert">
          <p className="mb-2">{t('events.loadError')}</p>
          <p className="text-sm">{t('events.loadErrorHelp')}</p>
        </div>
      )}

      {!isLoading && data && data.data.length > 0 && (
        <div className="motion-safe:animate-in motion-safe:fade-in motion-safe:duration-300">
          {/* List View */}
          {viewMode === 'list' && (
            <>
              {/* Featured Events Section - only for upcoming events, excludes hero event */}
              {!showPastEvents && (
                <FeaturedEventsSection
                  events={data.data.filter(e => heroEvent ? e.id !== heroEvent.id : true)}
                  onEventClick={setDetailEvent}
                  onRegister={setSelectedEvent}
                />
              )}

              {/* HappeningNowSection moved to the top of the page (above filters) — see PR #5 reorder. */}

              {/* Series Groups and Standalone Events */}
              <div className="space-y-4">
                {(() => {
                  const { standalone, series } = groupEventsBySeries(data.data)
                  // Filter out events already shown in featured for non-past view
                  const nonFeaturedStandalone = showPastEvents
                    ? standalone
                    : standalone.filter((e) => !e.is_featured && !recommendedEventIds.has(e.id))

                  return (
                    <>
                      {/* Series Groups */}
                      {series.map((group) => (
                        <SeriesEventGroup
                          key={group.series_id}
                          group={group}
                          onEventClick={setDetailEvent}
                          onRegister={setSelectedEvent}
                          onRegisterSeries={setSelectedSeries}
                        />
                      ))}

                      {/* Standalone Events */}
                      {nonFeaturedStandalone.length > 0 && (
                        <ul className="list-none p-0 m-0 space-y-4">
                          {nonFeaturedStandalone.map((event) => (
                            <li key={event.id}>
                              <EventCard
                                event={event}
                                onRegister={setSelectedEvent}
                                isPast={showPastEvents || isPastEvent(event)}
                                isBookmarked={personalization.isBookmarked(event.id)}
                                onToggleBookmark={personalization.toggleBookmark}
                                isRegistered={personalization.isRegistered(event.id)}
                                onTagClick={(tag) => setFilters(prev => ({ ...prev, tag }))}
                              />
                            </li>
                          ))}
                        </ul>
                      )}
                    </>
                  )
                })()}
              </div>
            </>
          )}

          {/* Calendar Views (Month & Week) */}
          {(viewMode === 'calendar-month' || viewMode === 'calendar-week') && (
            <EventCalendarView
              events={data.data}
              onEventClick={setDetailEvent}
              onRegister={setSelectedEvent}
              viewMode={calendarViewMode}
              showMiniCalendar={showMiniCalendar}
              selectedDate={selectedDate}
              onDateSelect={handleDateSelect}
            />
          )}

          {/* Agenda View */}
          {viewMode === 'agenda' && (
            <EventAgendaView
              events={data.data}
              onEventClick={setDetailEvent}
              onRegister={setSelectedEvent}
              showPastEvents={showPastEvents}
            />
          )}

          {/* Linear View — one flat, chronological, de-duplicated list with
              the promotional rails suppressed.
              Series occurrences appear inline at their own start times; each
              card keeps its "Part of: <series>" link, so series context is
              not lost. No featured/recommended exclusion — with the rails
              gone, every event must appear here exactly once. */}
          {viewMode === 'linear' && (
            <ul className="list-none p-0 m-0 space-y-4">
              {[...data.data]
                .sort(
                  (a, b) =>
                    new Date(a.start_time).getTime() - new Date(b.start_time).getTime(),
                )
                .map((event) => (
                  <li key={event.id}>
                    <EventCard
                      event={event}
                      onRegister={setSelectedEvent}
                      isPast={showPastEvents || isPastEvent(event)}
                      isBookmarked={personalization.isBookmarked(event.id)}
                      onToggleBookmark={personalization.toggleBookmark}
                      isRegistered={personalization.isRegistered(event.id)}
                      onTagClick={(tag) => setFilters((prev) => ({ ...prev, tag }))}
                    />
                  </li>
                ))}
            </ul>
          )}
        </div>
      )}

      {data && data.data.length === 0 && (
        <div className="motion-safe:animate-in motion-safe:fade-in motion-safe:duration-300 text-center py-16 px-4 rounded-xl bg-lsc-cream/30 dark:bg-lsc-brown/20 border-2 border-dashed border-lsc-border dark:border-earth-600/40">
          <Calendar aria-hidden="true" className="w-20 h-20 mx-auto mb-6 text-lsc-rose/70 dark:text-lsc-rose-light/60" />
          <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-3">
            {Object.keys(filters).length > 0 || showPastEvents
              ? t(EMPTY_STATE_KEYS.events.noEvents.message)
              : t(EMPTY_STATE_KEYS.events.noUpcoming.message)}
          </h3>
          <p className="text-sm text-lsc-dark/80 dark:text-lsc-cream/90 max-w-md mx-auto mb-6 leading-relaxed">
            {Object.keys(filters).length > 0 || showPastEvents
              ? t(EMPTY_STATE_KEYS.events.noEvents.suggestion)
              : t(EMPTY_STATE_KEYS.events.noUpcoming.suggestion)}
          </p>
          {(Object.keys(filters).length > 0 || showPastEvents) && (
            <button
              onClick={() => {
                setFilters({})
                setShowPastEvents(false)
              }}
              className="inline-flex items-center gap-2 px-6 py-3 bg-lsc-rose text-white rounded-xl font-medium hover:bg-lsc-rose-dark active:scale-95 transition-all focus:outline-none focus:ring-2 focus:ring-lsc-rose/50 shadow-sm hover:shadow-md touch-manipulation"
              aria-label={t('events.actions.clearFilters', 'Clear filters')}
            >
              {t('events.actions.clearFilters', 'Clear filters')}
            </button>
          )}
        </div>
      )}

      {!isLoading && !isFetching && !data && !error && (
        <div className="motion-safe:animate-in motion-safe:fade-in motion-safe:duration-300 text-center py-16 px-4 rounded-xl bg-lsc-cream/30 dark:bg-lsc-brown/20 border-2 border-dashed border-lsc-border dark:border-earth-600/40">
          <Calendar aria-hidden="true" className="w-20 h-20 mx-auto mb-6 text-lsc-dark/30 dark:text-lsc-cream/30" />
          <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-3">
            {t('events.unavailable', 'Events unavailable')}
          </h3>
          <p className="text-sm text-lsc-dark/80 dark:text-lsc-cream/90 max-w-md mx-auto leading-relaxed">
            {t('events.unavailableHelp', 'Unable to load events at this time. Please try again later.')}
          </p>
        </div>
      )}

      {detailEvent && (
        <EventDetailModal
          event={detailEvent}
          onClose={() => setDetailEvent(null)}
          onRegister={(event) => {
            setDetailEvent(null)
            setSelectedEvent(event)
          }}
          onEventClick={(event) => {
            // Switch to viewing the related event
            setDetailEvent(event)
          }}
        />
      )}

      {selectedEvent && (
        <RegistrationModal
          event={selectedEvent}
          onClose={() => { setSelectedEvent(null) }}
        />
      )}

      {selectedSeries && (
        <SeriesRegistrationModal
          seriesId={selectedSeries.series_id}
          seriesName={selectedSeries.series_name}
          seriesEvents={selectedSeries.events}
          onClose={() => { setSelectedSeries(null) }}
        />
      )}

      {/* Printable Calendar Modal */}
      <PrintableCalendar
        events={data?.data || []}
        isOpen={showPrintModal}
        onClose={() => setShowPrintModal(false)}
        month={new Date()}
      />

      {/* Event Preferences Modal */}
      <EventPreferencesModal
        isOpen={showPreferencesModal}
        onClose={() => setShowPreferencesModal(false)}
        preferences={personalization.preferences}
        onToggleCategory={personalization.toggleCategory}
        onToggleAudience={personalization.toggleAudience}
        onClearPreferences={() => personalization.setPreferences({ categories: [], audiences: [] })}
        availableCategories={availableCategories}
        availableAudiences={availableAudiences}
      />
    </div>
  )
}

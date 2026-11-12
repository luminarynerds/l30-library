/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useMemo } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { MessageCircle, Radio, Clock, Archive, Users, MessageSquare, AlertCircle } from 'lucide-react'
import StandardPageLayout from '@/components/StandardPageLayout'
import { usePageTitle } from '@/hooks/usePageTitle'
import { getAmaSessions, type AmaSession, type AmaSessionStatus } from '@/api/domains/content/ama-api'
import { t, getCurrentLocale } from '@/i18n'

type StatusFilter = 'all' | 'live' | 'upcoming' | 'archived'

const STATUS_FILTERS: { value: StatusFilter; label: string; icon: typeof Radio }[] = [
  { value: 'all', label: 'All Sessions', icon: MessageCircle },
  { value: 'live', label: 'Live Now', icon: Radio },
  { value: 'upcoming', label: 'Upcoming', icon: Clock },
  { value: 'archived', label: 'Past', icon: Archive },
]

function filterToApiStatus(filter: StatusFilter): string | undefined {
  if (filter === 'all') return undefined
  if (filter === 'archived') return 'archived'
  return filter
}

function formatSessionDate(dateStr: string): string {
  const date = new Date(dateStr)
  return date.toLocaleDateString(getCurrentLocale(), {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

function formatSessionTime(dateStr: string): string {
  const date = new Date(dateStr)
  return date.toLocaleTimeString(getCurrentLocale(), {
    hour: 'numeric',
    minute: '2-digit',
  })
}

function getAuthorName(session: AmaSession): string {
  const a = session.author
  if (a) return a.pen_name ?? a.guest_author_name ?? 'Author'
  return 'Author'
}

function getAuthorPhoto(session: AmaSession): string | null {
  const a = session.author
  if (a) return a.profile_image_url ?? a.guest_author_photo_url ?? null
  return null
}

function getStatusBadge(status: AmaSessionStatus) {
  switch (status) {
    case 'live':
      return {
        label: 'Live Now',
        className:
          'bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-700 dark:text-status-danger-400 border border-status-danger-200 dark:border-status-danger-800',
        dot: true,
      }
    case 'upcoming':
      return {
        label: 'Upcoming',
        className:
          'bg-status-info-100 dark:bg-status-info-900/30 text-status-info-700 dark:text-status-info-400 border border-status-info-200 dark:border-status-info-800',
        dot: false,
      }
    case 'grace_period':
      return {
        label: 'Wrapping Up',
        className:
          'bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-700 dark:text-status-warning-400 border border-status-warning-200 dark:border-status-warning-800',
        dot: false,
      }
    case 'archived':
      return {
        label: 'Completed',
        className:
          'bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 border border-lsc-border dark:border-earth-600',
        dot: false,
      }
    default:
      return {
        label: status,
        className: 'bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70',
        dot: false,
      }
  }
}

// ---------------------------------------------------------------------------
// Session Card
// ---------------------------------------------------------------------------

function AmaSessionCard({ session }: { session: AmaSession }) {
  const badge = getStatusBadge(session.status)
  const authorName = getAuthorName(session)
  const authorPhoto = getAuthorPhoto(session)
  const isLive = session.status === 'live'
  const isGrace = session.status === 'grace_period'

  return (
    <Link
      to={`/amas/${session.id}`}
      className={`group block bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm hover:shadow-md transition-all border border-lsc-border dark:border-earth-700 overflow-hidden ${
        isLive ? 'ring-2 ring-status-danger-400/50 dark:ring-status-danger-500/40' : ''
      }`}
      aria-label={`${session.title} with ${authorName} — ${badge.label}`}
    >
      <div className="p-5 sm:p-6">
        {/* Top row: status badge + date */}
        <div className="flex items-center justify-between gap-3 mb-3">
          <span
            className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${badge.className}`}
          >
            {badge.dot && (
              <span className="relative flex h-2 w-2" aria-hidden="true">
                <span className="motion-safe:animate-ping absolute inline-flex h-full w-full rounded-full bg-status-danger-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-status-danger-500" />
              </span>
            )}
            {badge.label}
          </span>

          <time
            dateTime={session.scheduled_start}
            className="text-xs text-earth-600 dark:text-earth-400 whitespace-nowrap"
          >
            {formatSessionDate(session.scheduled_start)}
          </time>
        </div>

        {/* Title */}
        <h3 className="font-serif text-lg font-semibold text-earth-700 dark:text-lsc-cream group-hover:text-lsc-rose dark:group-hover:text-lsc-rose-light transition-colors line-clamp-2 mb-2" title={session.title}>
          {session.title}
        </h3>

        {/* Author info */}
        <div className="flex items-center gap-3 mb-3">
          {authorPhoto ? (
            <img
              src={authorPhoto}
              alt=""
              className="w-9 h-9 rounded-full object-cover flex-shrink-0 border border-lsc-border dark:border-earth-600"
              loading="lazy"
            />
          ) : (
            <div
              className="w-9 h-9 rounded-full bg-lsc-rose/10 dark:bg-lsc-rose/20 flex items-center justify-center flex-shrink-0"
              aria-hidden="true"
            >
              <Users className="w-4 h-4 text-lsc-rose dark:text-lsc-rose-light" />
            </div>
          )}
          <span className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 truncate" title={authorName}>
            {authorName}
          </span>
        </div>

        {/* Description */}
        {session.description && (
          <p className="text-sm text-earth-600 dark:text-earth-400 line-clamp-2 mb-4" title={session.description}>
            {session.description}
          </p>
        )}

        {/* Footer: time + question stats */}
        <div className="flex items-center justify-between gap-4 pt-3 border-t border-earth-100 dark:border-earth-700">
          <div className="flex items-center gap-1.5 text-xs text-earth-600 dark:text-earth-400">
            <Clock className="w-3.5 h-3.5" aria-hidden="true" />
            <span>
              {formatSessionTime(session.scheduled_start)} &ndash;{' '}
              {formatSessionTime(session.scheduled_end)}
            </span>
          </div>

          <div className="flex items-center gap-3 text-xs text-earth-600 dark:text-earth-400">
            <span className="flex items-center gap-1">
              <MessageSquare className="w-3.5 h-3.5" aria-hidden="true" />
              {session.total_questions} {session.total_questions === 1 ? 'question' : 'questions'}
            </span>
            {session.total_answered > 0 && (
              <span className="text-forest-800 dark:text-forest-400 font-medium">
                {session.total_answered} answered
              </span>
            )}
          </div>
        </div>

        {/* Live / grace-period CTA */}
        {(isLive || isGrace) && (
          <div className="mt-3 text-center">
            <span className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium bg-lsc-rose/10 dark:bg-lsc-rose/20 text-lsc-rose dark:text-lsc-rose-light group-hover:bg-lsc-rose/20 dark:group-hover:bg-lsc-rose/30 transition-colors">
              {isLive ? 'Join the conversation' : 'View answers'}
            </span>
          </div>
        )}
      </div>
    </Link>
  )
}

// ---------------------------------------------------------------------------
// Skeleton for loading state
// ---------------------------------------------------------------------------

function AmaSessionCardSkeleton() {
  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border dark:border-earth-700 p-5 sm:p-6">
      <div className="flex items-center justify-between mb-3">
        <div className="h-6 w-20 bg-earth-200 dark:bg-earth-700 rounded-full motion-safe:animate-pulse" />
        <div className="h-4 w-28 bg-earth-200 dark:bg-earth-700 rounded motion-safe:animate-pulse" />
      </div>
      <div className="h-6 w-3/4 bg-earth-200 dark:bg-earth-700 rounded motion-safe:animate-pulse mb-3" />
      <div className="flex items-center gap-3 mb-3">
        <div className="w-9 h-9 rounded-full bg-earth-200 dark:bg-earth-700 motion-safe:animate-pulse" />
        <div className="h-4 w-32 bg-earth-200 dark:bg-earth-700 rounded motion-safe:animate-pulse" />
      </div>
      <div className="space-y-2 mb-4">
        <div className="h-4 w-full bg-earth-100 dark:bg-earth-800 rounded motion-safe:animate-pulse" />
        <div className="h-4 w-5/6 bg-earth-100 dark:bg-earth-800 rounded motion-safe:animate-pulse" />
      </div>
      <div className="pt-3 border-t border-earth-100 dark:border-earth-700 flex items-center justify-between">
        <div className="h-4 w-36 bg-earth-200 dark:bg-earth-700 rounded motion-safe:animate-pulse" />
        <div className="h-4 w-24 bg-earth-200 dark:bg-earth-700 rounded motion-safe:animate-pulse" />
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Page Content
// ---------------------------------------------------------------------------

function AmasPageContent() {
  const [filter, setFilter] = useState<StatusFilter>('all')

  const { data, isLoading, error } = useQuery({
    queryKey: ['ama-sessions', filter],
    queryFn: () => getAmaSessions(filterToApiStatus(filter)),
    staleTime: 30_000, // 30s — sessions can go live at any time
  })

  // eslint-disable-next-line react-hooks/exhaustive-deps
  const sessions = data?.items ?? []

  // Sort: live first, then upcoming (by date asc), then grace_period, then archived (by date desc)
  const sortedSessions = useMemo(() => {
    const statusOrder: Record<AmaSessionStatus, number> = {
      live: 0,
      grace_period: 1,
      upcoming: 2,
      archived: 3,
    }
    return [...sessions].sort((a, b) => {
      const orderDiff = (statusOrder[a.status] ?? 9) - (statusOrder[b.status] ?? 9)
      if (orderDiff !== 0) return orderDiff
      // Within same status: upcoming sorts ascending (soonest first), archived sorts descending (newest first)
      if (a.status === 'archived') {
        return new Date(b.scheduled_start).getTime() - new Date(a.scheduled_start).getTime()
      }
      return new Date(a.scheduled_start).getTime() - new Date(b.scheduled_start).getTime()
    })
  }, [sessions])

  // Count live sessions for the badge on the filter pill
  const liveCount = useMemo(
    () => sessions.filter((s) => s.status === 'live').length,
    [sessions]
  )

  return (
    <div className="space-y-6">
      {/* Status filter pills */}
      <div
        className="flex flex-wrap items-center gap-2"
        role="radiogroup"
        aria-label={t('aria.amas.filterAmaSessionsByStatus')}
      >
        {STATUS_FILTERS.map(({ value, label, icon: Icon }) => {
          const isActive = filter === value
          return (
            <button
              key={value}
              onClick={() => setFilter(value)}
              role="radio"
              aria-checked={isActive}
              className={`inline-flex items-center gap-2 px-4 py-2 min-h-[44px] rounded-xl text-sm font-medium transition-all focus:outline-none focus:ring-2 focus:ring-lsc-rose touch-manipulation ${
                isActive
                  ? 'bg-lsc-rose text-white shadow-sm'
                  : 'bg-lsc-cream dark:bg-earth-800 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-earth-200 dark:hover:bg-earth-700 border border-lsc-border dark:border-earth-700'
              }`}
            >
              <Icon className="w-4 h-4" aria-hidden="true" />
              {label}
              {value === 'live' && liveCount > 0 && (
                <span className="inline-flex items-center justify-center px-1.5 py-0.5 text-[10px] font-bold rounded-full bg-status-danger-500 text-white min-w-[18px] leading-none">
                  {liveCount}
                </span>
              )}
            </button>
          )
        })}
      </div>

      {/* Screen reader status announcement */}
      <div role="status" aria-live="polite" aria-atomic="true" className="sr-only">
        {isLoading
          ? 'Loading AMA sessions...'
          : sortedSessions.length > 0
            ? `${sortedSessions.length} AMA ${sortedSessions.length === 1 ? 'session' : 'sessions'} found`
            : 'No AMA sessions found'}
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {Array.from({ length: 6 }).map((_, i) => (
            <AmaSessionCardSkeleton key={i} />
          ))}
        </div>
      )}

      {/* Error */}
      {error && !isLoading && (
        <div
          className="text-center py-12"
          role="alert"
        >
          <AlertCircle
            className="w-12 h-12 text-status-danger-400 dark:text-status-danger-500 mx-auto mb-4"
            aria-hidden="true"
          />
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-lg mb-1">
            Unable to load AMA sessions
          </p>
          <p className="text-sm text-earth-600 dark:text-earth-400">
            Please try again later. If this continues, contact the library.
          </p>
        </div>
      )}

      {/* Sessions grid */}
      {!isLoading && !error && sortedSessions.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5 motion-safe:animate-in motion-safe:fade-in motion-safe:duration-300">
          {sortedSessions.map((session) => (
            <AmaSessionCard key={session.id} session={session} />
          ))}
        </div>
      )}

      {/* Empty state */}
      {!isLoading && !error && sortedSessions.length === 0 && (
        <div className="text-center py-16">
          <MessageCircle
            className="w-12 h-12 text-earth-300 dark:text-earth-600 mx-auto mb-4"
            aria-hidden="true"
          />
          <h3 className="text-lg font-medium text-earth-700 dark:text-lsc-cream mb-2">
            {filter === 'all'
              ? 'No AMA sessions yet'
              : filter === 'live'
                ? 'No live sessions right now'
                : filter === 'upcoming'
                  ? 'No upcoming sessions scheduled'
                  : 'No past sessions to show'}
          </h3>
          <p className="text-sm text-earth-600 dark:text-earth-400 max-w-md mx-auto">
            {filter === 'all' || filter === 'upcoming'
              ? 'Author Q&A sessions will appear here once scheduled by our team. Check back soon!'
              : filter === 'live'
                ? 'Check the upcoming tab to see when the next session starts.'
                : 'Completed sessions and their Q&A archives will appear here.'}
          </p>
          {filter !== 'all' && (
            <button
              onClick={() => setFilter('all')}
              className="mt-4 text-lsc-rose dark:text-lsc-rose-light font-medium hover:underline"
            >
              View all sessions
            </button>
          )}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Page Shell
// ---------------------------------------------------------------------------

export default function AmasPage(): React.ReactElement {
  usePageTitle('Author AMAs')

  return (
    <StandardPageLayout
      title="Author AMAs"
      subtitle="Live Q&A sessions with authors. Ask questions, upvote favorites, and join the conversation."
      icon={MessageCircle}
    >
      <AmasPageContent />
    </StandardPageLayout>
  )
}

/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/* eslint-disable react-refresh/only-export-components */
import { useState, useEffect, useMemo } from 'react'
import { Link } from 'react-router-dom'
import {
  Users, BookOpen, Calendar, Search, Filter, MessageCircle,
} from 'lucide-react'
import { EmptyState } from '../components/ui/EmptyState'
import { listBookClubs, type BookClubListItem } from '../api/book-clubs-api'
import { patronCapacityBadge } from '@/utils/bookClubCapacity'
import { useOrganizationFeatures } from '@/contexts/OrganizationFeaturesContext'
import { friendlyErrorMessage } from '@/utils/friendlyError'
import { t } from '@/i18n'
import { usePageTitle } from '@/hooks/usePageTitle'
import { useBranding } from '@/contexts/BrandingContext'

export function formatMemberSummary(memberCount: number, maxMembers: number | null | undefined): string {
  if (maxMembers != null) {
    return `${memberCount} members · capacity ${maxMembers}`
  }
  return `${memberCount} members`
}

export function deriveGenres(clubs: ReadonlyArray<Pick<BookClubListItem, 'genre'>>): string[] {
  const seen = new Set<string>()
  const out: string[] = []
  for (const club of clubs) {
    const g = club.genre
    if (!g) continue
    const key = g.toLowerCase()
    if (seen.has(key)) continue
    seen.add(key)
    out.push(g)
  }
  return out
}

export default function BookClubsPage(): React.ReactElement {
  const branding = useBranding()
  const { isFeatureEnabled } = useOrganizationFeatures()
  const waitlistEnabled = isFeatureEnabled('book_club_waitlist_enabled')
  usePageTitle('Book Clubs', `Join a book club at ${branding.library_short_name}. Browse active clubs, see current reads, and sign up.`)
  const [searchQuery, setSearchQuery] = useState('')
  const [debouncedQuery, setDebouncedQuery] = useState('')
  const [selectedGenre, setSelectedGenre] = useState<string | null>(null)
  const [clubs, setClubs] = useState<BookClubListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [retryKey, setRetryKey] = useState(0)

  // Fetch clubs once (and on retry). Filtering is now client-side; the
  // patron list is small (~4-10 clubs) so the server round-trip per
  // keystroke or pill click is unnecessary.
  useEffect(() => {
    let cancelled = false
    // eslint-disable-next-line react-hooks/set-state-in-effect -- loading/error reset for async fetch lifecycle
    setLoading(true)
    setError(null)
    listBookClubs()
      .then((res) => {
        if (!cancelled) {
          setClubs(res.clubs)
          setLoading(false)
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(friendlyErrorMessage(err))
          setLoading(false)
        }
      })
    return () => { cancelled = true }
  }, [retryKey])

  // Debounce the search input (~200ms) for the filter pipeline.
  useEffect(() => {
    const tid = setTimeout(() => setDebouncedQuery(searchQuery), 200)
    return () => clearTimeout(tid)
  }, [searchQuery])

  // Genre pills come from the actually-loaded clubs so we never render a
  // pill that would yield an empty state.
  const availableGenres = useMemo(() => deriveGenres(clubs), [clubs])

  // If the selected genre disappears (e.g. clubs reloaded), clear it.
  useEffect(() => {
    if (selectedGenre && !availableGenres.some((g) => g.toLowerCase() === selectedGenre.toLowerCase())) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- clear selection when its genre leaves the loaded set
      setSelectedGenre(null)
    }
  }, [availableGenres, selectedGenre])

  const filteredClubs = useMemo(() => {
    const q = debouncedQuery.trim().toLowerCase()
    return clubs.filter((c) => {
      if (selectedGenre && (c.genre ?? '').toLowerCase() !== selectedGenre.toLowerCase()) {
        return false
      }
      if (q) {
        const name = (c.name ?? '').toLowerCase()
        const desc = (c.description ?? '').toLowerCase()
        if (!name.includes(q) && !desc.includes(q)) return false
      }
      return true
    })
  }, [clubs, debouncedQuery, selectedGenre])

  const trimmedQuery = debouncedQuery.trim()

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
          Book Clubs
        </h1>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
          Join a community of readers. Discuss books, share perspectives, and make new friends.
        </p>
      </div>

      {/* Search and Filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/60" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={t('placeholder.bookClubs.searchBookClubs')}
            aria-label={t('aria.bookClubs.searchBookClubs')}
            className="w-full pl-10 pr-4 py-3 bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl text-lsc-dark dark:text-lsc-cream placeholder-earth-500 focus:outline-none focus:ring-2 focus:ring-lsc-rose"
          />
        </div>
        {availableGenres.length > 0 && (
          <div
            role="radiogroup"
            aria-label="Filter by genre"
            onKeyDown={(e) => {
              const all: (string | null)[] = [null, ...availableGenres]
              const idx = all.findIndex((g) => g === selectedGenre)
              let next = idx
              if (e.key === 'ArrowRight') next = (idx + 1) % all.length
              else if (e.key === 'ArrowLeft') next = (idx - 1 + all.length) % all.length
              else if (e.key === 'Home') next = 0
              else if (e.key === 'End') next = all.length - 1
              else return
              e.preventDefault()
              setSelectedGenre(all[next] ?? null)
              const target = all[next]
              const id = target === null ? 'genre-chip-all' : `genre-chip-${target}`
              document.getElementById(id)?.focus()
            }}
            className="relative flex gap-2 overflow-x-auto pb-1 [mask-image:linear-gradient(to_right,black_calc(100%-32px),transparent)]"
          >
            <button
              id="genre-chip-all"
              role="radio"
              aria-checked={!selectedGenre}
              tabIndex={!selectedGenre ? 0 : -1}
              onClick={() => setSelectedGenre(null)}
              className={`flex items-center gap-1.5 px-4 py-2 rounded-xl text-sm font-medium whitespace-nowrap transition-colors ${
                !selectedGenre
                  ? 'bg-lsc-rose text-white'
                  : 'bg-lsc-white dark:bg-earth-800 text-lsc-dark/70 dark:text-lsc-cream/70 border border-lsc-border dark:border-earth-700 hover:border-lsc-rose'
              }`}
            >
              <Filter className="w-4 h-4" />
              All
            </button>
            {availableGenres.map((genre) => (
              <button
                key={genre}
                id={`genre-chip-${genre}`}
                role="radio"
                aria-checked={selectedGenre === genre}
                tabIndex={selectedGenre === genre ? 0 : -1}
                onClick={() => setSelectedGenre(genre)}
                className={`px-4 py-2 rounded-xl text-sm font-medium whitespace-nowrap transition-colors ${
                  selectedGenre === genre
                    ? 'bg-lsc-rose text-white'
                    : 'bg-lsc-white dark:bg-earth-800 text-lsc-dark/70 dark:text-lsc-cream/70 border border-lsc-border dark:border-earth-700 hover:border-lsc-rose'
                }`}
              >
                {genre}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Loading State */}
      {loading && (
        <div
          role="status"
          aria-live="polite"
          aria-busy="true"
          className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4"
        >
          <span className="sr-only">Loading book clubs</span>
          {Array.from({ length: 6 }).map((_, i) => (
            <div
              key={i}
              aria-hidden="true"
              className="bg-lsc-white dark:bg-earth-800 rounded-xl p-5 border border-lsc-border dark:border-earth-700 motion-safe:animate-pulse"
            >
              <div className="h-5 w-3/4 bg-earth-200 dark:bg-earth-700 rounded" />
              <div className="mt-3 space-y-2">
                <div className="h-3 w-full bg-earth-200 dark:bg-earth-700 rounded" />
                <div className="h-3 w-5/6 bg-earth-200 dark:bg-earth-700 rounded" />
              </div>
              <div className="flex flex-wrap items-center gap-3 mt-4">
                <div className="h-3 w-20 bg-earth-200 dark:bg-earth-700 rounded" />
                <div className="h-3 w-24 bg-earth-200 dark:bg-earth-700 rounded" />
                <div className="h-3 w-28 bg-earth-200 dark:bg-earth-700 rounded" />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Error State */}
      {error && !loading && (
        <div className="bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800 rounded-xl p-4 flex items-center justify-between">
          <span className="text-status-danger-700 dark:text-status-danger-300 text-sm">{error}</span>
          <button
            onClick={() => { setError(null); setRetryKey(k => k + 1) }}
            className="text-sm font-medium text-lsc-rose hover:underline ml-4 shrink-0"
          >
            Try again
          </button>
        </div>
      )}

      {/* Club Cards */}
      {!loading && !error && filteredClubs.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredClubs.map((club) => {
            const nextMeeting = club.next_meeting_date ? new Date(club.next_meeting_date) : null
            const nextMeetingFriendly = nextMeeting
              ? nextMeeting.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' })
              : null
            const memberSummary = formatMemberSummary(club.member_count, club.max_members)
            const capacityBadge = patronCapacityBadge(
              {
                currentMemberCount: club.current_member_count ?? club.member_count,
                maxMembers: club.max_members,
                waitlistCount: club.waitlist_count ?? 0,
                isFull: club.is_full ?? false,
              },
              waitlistEnabled,
            )
            const capacitySummary = capacityBadge ?? memberSummary
            const currentlyReading = club.current_book_title
              ? (club.current_book_author
                  ? `${club.current_book_title} by ${club.current_book_author}`
                  : club.current_book_title)
              : null
            const labelParts = [
              club.name,
              capacitySummary,
              club.meeting_frequency ? `meets ${club.meeting_frequency}` : null,
              currentlyReading ? `currently reading ${currentlyReading}` : null,
              nextMeetingFriendly ? `next meeting ${nextMeetingFriendly}` : null,
            ].filter(Boolean) as string[]
            return (
              <Link
                key={club.id}
                to={`/book-clubs/${club.id}`}
                aria-label={labelParts.join(', ')}
                className="group bg-lsc-white dark:bg-earth-800 rounded-xl p-5 border border-lsc-border dark:border-earth-700 hover:border-lsc-rose dark:hover:border-lsc-rose transition-colors"
              >
                <h3 className="font-serif font-bold text-lg text-lsc-dark dark:text-lsc-cream group-hover:text-lsc-rose transition-colors">
                  {club.name}
                </h3>
                {club.description && (
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-2 line-clamp-2" title={club.description}>
                    {club.description}
                  </p>
                )}
                <div className="flex flex-wrap items-center gap-3 mt-4">
                  <span className="inline-flex items-center gap-1.5 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                    <Users className="w-3.5 h-3.5" />
                    {capacitySummary}
                  </span>
                  {club.meeting_frequency && (
                    <span className="inline-flex items-center gap-1.5 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                      <Calendar className="w-3.5 h-3.5" />
                      {club.meeting_frequency}
                    </span>
                  )}
                </div>
                {(currentlyReading || nextMeetingFriendly) && (
                  <div className="mt-3 pt-3 border-t border-lsc-border/60 dark:border-earth-700/60 space-y-1.5">
                    {currentlyReading && (
                      <div className="flex items-start gap-1.5 text-xs text-lsc-dark/80 dark:text-lsc-cream/80">
                        <BookOpen className="w-3.5 h-3.5 mt-0.5 shrink-0" aria-hidden="true" />
                        <span className="truncate" title={currentlyReading}>
                          Currently reading: <em>{club.current_book_title}</em>
                          {club.current_book_author ? ` by ${club.current_book_author}` : ""}
                        </span>
                      </div>
                    )}
                    {nextMeetingFriendly && (
                      <div className="flex items-center gap-1.5 text-xs text-lsc-rose font-medium">
                        <Calendar className="w-3.5 h-3.5 shrink-0" aria-hidden="true" />
                        <span>Next: {nextMeetingFriendly}</span>
                      </div>
                    )}
                  </div>
                )}
              </Link>
            )
          })}
        </div>
      )}

      {/* Empty State -- search-specific message wins over the cold-start one. */}
      {!loading && !error && filteredClubs.length === 0 && clubs.length > 0 && trimmedQuery && (
        <p
          role="status"
          aria-live="polite"
          className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70"
        >
          No clubs match &ldquo;{trimmedQuery}&rdquo;
        </p>
      )}
      {!loading && !error && filteredClubs.length === 0 && clubs.length > 0 && !trimmedQuery && selectedGenre && (
        <p
          role="status"
          aria-live="polite"
          className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70"
        >
          No clubs in this genre.
        </p>
      )}
      {!loading && !error && clubs.length === 0 && (
        <EmptyState
          icon={Users}
          title="No book clubs yet"
          description="Book clubs will appear here once they are created. Check back soon!"
          primaryAction={{ label: 'Browse Catalog', href: '/catalog' }}
          secondaryAction={{ label: 'View Events', href: '/events' }}
          size="lg"
          showTip
        />
      )}

      {/* How It Works */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700">
        <h2 className="font-serif font-bold text-lg text-lsc-dark dark:text-lsc-cream mb-4">
          How Book Clubs Work
        </h2>
        <div className="grid sm:grid-cols-3 gap-6">
          <div className="text-center">
            <div className="w-12 h-12 rounded-xl bg-lsc-rose/10 flex items-center justify-center mx-auto mb-3">
              <Search className="w-6 h-6 text-lsc-rose" />
            </div>
            <h3 className="font-medium text-lsc-dark dark:text-lsc-cream mb-1">Browse & Join</h3>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
              Find a club that matches your reading interests and join with one click.
            </p>
          </div>
          <div className="text-center">
            <div className="w-12 h-12 rounded-xl bg-lsc-rose/10 flex items-center justify-center mx-auto mb-3">
              <MessageCircle className="w-6 h-6 text-lsc-rose" />
            </div>
            <h3 className="font-medium text-lsc-dark dark:text-lsc-cream mb-1">Discuss</h3>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
              Share your thoughts in discussion threads and chat live during meetings.
            </p>
          </div>
          <div className="text-center">
            <div className="w-12 h-12 rounded-xl bg-lsc-rose/10 flex items-center justify-center mx-auto mb-3">
              <Calendar className="w-6 h-6 text-lsc-rose" />
            </div>
            <h3 className="font-medium text-lsc-dark dark:text-lsc-cream mb-1">Meet</h3>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
              Attend in-person or virtual meetings at your convenience.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

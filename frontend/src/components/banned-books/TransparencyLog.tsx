/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  AlertTriangle, BookOpen, CheckCircle, XCircle, Clock, Loader2,
} from 'lucide-react'
import {
  getPublicChallenges,
  getPublicStats,
  CHALLENGE_OUTCOME_LABELS,
  CHALLENGE_REASON_LABELS,
  type BookChallengePublic,
  type ChallengeOutcome,
  type ChallengeReason,
} from '@/api/domains/content/book-challenges-api'

const PER_PAGE = 10

interface FilterState {
  year: number | undefined
  outcome: ChallengeOutcome | undefined
  reason: ChallengeReason | undefined
  page: number
}

const INITIAL_FILTERS: FilterState = {
  year: undefined,
  outcome: undefined,
  reason: undefined,
  page: 1,
}

function getOutcomeIcon(outcome: ChallengeOutcome) {
  switch (outcome) {
    case 'retained':
    case 'retained_with_changes':
      return <CheckCircle className="w-5 h-5 text-status-success-600" aria-hidden="true" />
    case 'removed':
      return <XCircle className="w-5 h-5 text-status-danger-600" aria-hidden="true" />
    case 'restricted':
      return <AlertTriangle className="w-5 h-5 text-status-warning-600" aria-hidden="true" />
    case 'withdrawn':
    case 'pending':
    default:
      return <Clock className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" aria-hidden="true" />
  }
}

function getOutcomeColor(outcome: ChallengeOutcome): string {
  switch (outcome) {
    case 'retained':
    case 'retained_with_changes':
      return 'bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-300'
    case 'removed':
      return 'bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900/30 dark:text-status-danger-300'
    case 'restricted':
      return 'bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-300'
    case 'withdrawn':
    case 'pending':
    default:
      return 'bg-earth-100 text-earth-800 dark:bg-earth-900/30 dark:text-earth-300'
  }
}

export default function TransparencyLog() {
  const [filters, setFilters] = useState<FilterState>(INITIAL_FILTERS)

  const { data: stats } = useQuery({
    queryKey: ['publicChallengeStats'],
    queryFn: getPublicStats,
  })

  const { data, isLoading, isError, error } = useQuery({
    queryKey: [
      'publicChallenges',
      'log',
      filters.year ?? null,
      filters.outcome ?? null,
      filters.reason ?? null,
      filters.page,
    ],
    queryFn: () =>
      getPublicChallenges({
        year: filters.year,
        outcome: filters.outcome,
        reason: filters.reason,
        page: filters.page,
        per_page: PER_PAGE,
      }),
    placeholderData: (previous) => previous,
  })

  const items: BookChallengePublic[] = data?.items ?? []
  const total = data?.total ?? 0
  const pages = data?.pages ?? 1
  const hasFilters =
    filters.year !== undefined || filters.outcome !== undefined || filters.reason !== undefined
  const showPager = total > PER_PAGE

  const availableYears: number[] = stats?.available_years ?? []
  // Stats dicts are keyed by lowercase enum value. The UI dropdown values
  // need to match those keys exactly to round-trip back to the API.
  // 'pending' challenges are never made public, so exclude it from the filter.
  const outcomeKeys = (Object.keys(stats?.outcomes ?? {}) as ChallengeOutcome[]).filter(o => o !== 'pending')
  const reasonKeys = Object.keys(stats?.reasons ?? {}) as ChallengeReason[]

  const reset = () => setFilters({ ...INITIAL_FILTERS })

  return (
    <div>
      {/* Filters */}
      <div
        className="flex flex-wrap items-end gap-3 mb-6 p-4 bg-lsc-cream/50 dark:bg-earth-800/50 rounded-lg border border-lsc-border dark:border-earth-700"
        role="group"
        aria-label="Filter Transparency Log"
      >
        <div className="flex-1 min-w-[140px]">
          <label htmlFor="tl-year" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
            Year
          </label>
          <select
            id="tl-year"
            value={filters.year ?? ''}
            onChange={e =>
              setFilters(f => ({
                ...f,
                year: e.target.value ? Number(e.target.value) : undefined,
                page: 1,
              }))
            }
            className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-lsc-rose"
          >
            <option value="">All years</option>
            {availableYears.map(y => (
              <option key={y} value={y}>{y}</option>
            ))}
          </select>
        </div>

        <div className="flex-1 min-w-[160px]">
          <label htmlFor="tl-outcome" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
            Outcome
          </label>
          <select
            id="tl-outcome"
            value={filters.outcome ?? ''}
            onChange={e =>
              setFilters(f => ({
                ...f,
                outcome: (e.target.value || undefined) as ChallengeOutcome | undefined,
                page: 1,
              }))
            }
            className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-lsc-rose"
          >
            <option value="">All outcomes</option>
            {outcomeKeys.map(o => (
              <option key={o} value={o}>{CHALLENGE_OUTCOME_LABELS[o] ?? o}</option>
            ))}
          </select>
        </div>

        <div className="flex-1 min-w-[160px]">
          <label htmlFor="tl-reason" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
            Reason
          </label>
          <select
            id="tl-reason"
            value={filters.reason ?? ''}
            onChange={e =>
              setFilters(f => ({
                ...f,
                reason: (e.target.value || undefined) as ChallengeReason | undefined,
                page: 1,
              }))
            }
            className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-lsc-rose"
          >
            <option value="">All reasons</option>
            {reasonKeys.map(r => (
              <option key={r} value={r}>{CHALLENGE_REASON_LABELS[r] ?? r}</option>
            ))}
          </select>
        </div>

        <button
          type="button"
          onClick={reset}
          disabled={!hasFilters}
          className="px-4 py-2 border border-lsc-border dark:border-earth-700 rounded-lg text-sm font-medium text-lsc-dark dark:text-lsc-cream hover:bg-lsc-white dark:hover:bg-earth-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          Reset
        </button>
      </div>

      {/* List */}
      {isLoading && !data ? (
        <div className="motion-safe:animate-pulse space-y-4" data-testid="transparency-log-loading">
          {[1, 2, 3].map(i => (
            <div key={i} className="h-32 bg-lsc-cream dark:bg-earth-800 rounded-lg" />
          ))}
        </div>
      ) : isError ? (
        <div
          role="alert"
          className="bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800 rounded-lg p-6 text-status-danger-800 dark:text-status-danger-200"
        >
          <p className="font-medium">We couldn't load the Transparency Log right now.</p>
          <p className="text-sm mt-1">
            {error instanceof Error ? error.message : 'Please try again in a moment.'}
          </p>
        </div>
      ) : items.length === 0 ? (
        <div className="bg-lsc-cream dark:bg-earth-800 rounded-lg p-8 border border-lsc-border dark:border-earth-700 text-center">
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
            {hasFilters
              ? 'No challenges match the current filters.'
              : 'No public challenges have been recorded yet.'}
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {items.map(challenge => (
            <article
              key={challenge.id}
              className="bg-lsc-white dark:bg-earth-800 rounded-lg p-5 border border-lsc-border dark:border-earth-700"
              data-testid="transparency-log-item"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-2">
                    {getOutcomeIcon(challenge.outcome)}
                    <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
                      {challenge.public_title || challenge.title}
                    </h3>
                  </div>
                  {challenge.author && (
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
                      by {challenge.author}
                    </p>
                  )}
                  <div className="flex flex-wrap gap-2 mb-3">
                    <span
                      className={`px-2 py-1 rounded-full text-xs font-medium ${getOutcomeColor(challenge.outcome)}`}
                    >
                      {CHALLENGE_OUTCOME_LABELS[challenge.outcome] ?? challenge.outcome}
                    </span>
                    <span className="px-2 py-1 rounded-full text-xs font-medium bg-lsc-cream dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70">
                      {CHALLENGE_REASON_LABELS[challenge.primary_reason as ChallengeReason] ?? challenge.primary_reason}
                    </span>
                  </div>
                  {challenge.catalog_item_id != null && (
                    <div className="mb-3">
                      <Link
                        to={`/catalog/${challenge.catalog_item_id}`}
                        className="inline-flex items-center gap-1 text-sm text-lsc-rose hover:underline"
                      >
                        <BookOpen className="w-3.5 h-3.5" aria-hidden="true" />
                        View in Catalog
                      </Link>
                    </div>
                  )}
                  {challenge.public_summary && (
                    <p className="text-sm text-lsc-dark/80 dark:text-lsc-cream/90 mb-3">
                      {challenge.public_summary}
                    </p>
                  )}
                  {challenge.lessons_learned && (
                    <div className="bg-lsc-cream/50 dark:bg-earth-700/50 rounded p-3 mt-3">
                      <p className="text-sm text-lsc-dark/80 dark:text-lsc-cream/90">
                        <strong>What we learned:</strong> {challenge.lessons_learned}
                      </p>
                    </div>
                  )}
                </div>
                <div className="text-right text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                  <div>{new Date(challenge.date_received).toLocaleDateString()}</div>
                  {challenge.date_resolved && (
                    <div className="text-status-success-600 dark:text-status-success-400">
                      Resolved {new Date(challenge.date_resolved).toLocaleDateString()}
                    </div>
                  )}
                </div>
              </div>
            </article>
          ))}
        </div>
      )}

      {/* Pagination */}
      {showPager && (
        <nav
          className="flex items-center justify-between mt-6"
          aria-label="Transparency Log pagination"
        >
          <button
            type="button"
            onClick={() => setFilters(f => ({ ...f, page: Math.max(1, f.page - 1) }))}
            disabled={filters.page <= 1 || isLoading}
            className="px-4 py-2 border border-lsc-border dark:border-earth-700 rounded-lg text-sm font-medium text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            Previous
          </button>
          <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70" aria-live="polite">
            {isLoading ? (
              <span className="inline-flex items-center gap-2">
                <Loader2 className="w-3 h-3 motion-safe:animate-spin" aria-hidden="true" />
                Page {filters.page} of {pages}
              </span>
            ) : (
              <>Page {filters.page} of {pages}</>
            )}
          </div>
          <button
            type="button"
            onClick={() => setFilters(f => ({ ...f, page: Math.min(pages, f.page + 1) }))}
            disabled={filters.page >= pages || isLoading}
            className="px-4 py-2 border border-lsc-border dark:border-earth-700 rounded-lg text-sm font-medium text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            Next
          </button>
        </nav>
      )}
    </div>
  )
}

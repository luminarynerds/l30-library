/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Session resource-handouts picker for the parent-onboarding session
 * detail page. Self-contained: owns its own queries, mutations, and
 * forms so it can be dropped into the page without coupling to the
 * page's existing (drift-prone) session model.
 *
 * Three groups:
 *   1. Suggested for this family (only when patronLanguage is set and
 *      non-English; otherwise hidden -- the spec defers auto-filter to
 *      the family-snapshot follow-up)
 *   2. All resources (paginated with "Load more" -- a11y-simpler than
 *      infinite scroll)
 *   3. Given today (the active checklist for THIS session)
 *
 * Print packet:
 *   The button calls `requestPrintPacket()` which transparently maps the
 *   backend's 501 ("Print packet generator is not available yet.") to a
 *   disabled state with a sr-only explanation pointing at the dependent
 *   spec. This is the "graceful degradation" path per the spec.
 *
 * A11y:
 *   - Section wrapper carries an explicit <h2> via aria-labelledby
 *   - Catalog row buttons use <button aria-pressed> for toggle semantics
 *   - Given-today list is a <ul aria-label> with per-row labeled
 *     <select> + <button>; delivery-method labels include the resource
 *     name to avoid label collision (feedback_l30_form_label_collision)
 *   - Language pills carry visible text + the BCP-47 code, never color
 *     alone
 *   - Print Packet disabled state includes a <span class="sr-only">
 *     explanation pointing at the dependent spec
 *
 * i18n keys live under parentOnboarding.handouts.* -- see en.json.
 */
import { useId, useMemo, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, X, Printer, Loader2 } from 'lucide-react'
import toast from 'react-hot-toast'

import { useTranslation } from '@/i18n'
import {
  listResourceHandouts,
  listSessionHandouts,
  createSessionHandout,
  deleteSessionHandout,
  requestPrintPacket,
  type HandoutDeliveryMethod,
  type ResourceHandout,
  type SessionHandout,
} from '@/api/domains/services/parent-onboarding-session-handouts-api'

const FOCUS_RING =
  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2 dark:focus-visible:ring-offset-earth-900'

const DEFAULT_PAGE_SIZE = 25

const DELIVERY_METHODS: HandoutDeliveryMethod[] = [
  'printed',
  'emailed',
  'linked',
  'given_orally',
]

interface Props {
  sessionId: number
  /**
   * BCP-47 language code from the patron's preference (e.g. "es").
   * When set and non-English, the "Suggested for this family" group is
   * shown above the full catalog list and the picker auto-filters to
   * that language by default. When null/undefined (no snapshot yet),
   * the suggested group is hidden -- the picker still works, it just
   * doesn't auto-filter.
   */
  patronLanguage?: string | null
}

export function SessionResourceHandouts({ sessionId, patronLanguage }: Props) {
  // All hooks BEFORE any early return so call count is stable across renders
  // (rule-of-hooks; React #310 -- sibling pattern to AddToListDropdown).
  const { t } = useTranslation()
  const headingId = useId()
  const searchInputId = useId()
  const queryClient = useQueryClient()

  // --- Filters ------------------------------------------------------------

  // Auto-filter to the patron's language when known and non-English so the
  // coordinator doesn't have to click the chip every time.
  const initialLanguage =
    patronLanguage && patronLanguage !== 'en' ? patronLanguage : ''
  const [languageFilter, setLanguageFilter] = useState<string>(initialLanguage)
  const [categoryFilter, setCategoryFilter] = useState<string>('')
  const [search, setSearch] = useState('')

  // Pagination: "Load more" is incremented in chunks of DEFAULT_PAGE_SIZE.
  const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE)

  // --- Queries ------------------------------------------------------------

  const catalogQuery = useQuery({
    queryKey: [
      'resource-handouts-catalog',
      languageFilter, categoryFilter, search, pageSize,
    ],
    queryFn: () => listResourceHandouts({
      language: languageFilter || undefined,
      category: categoryFilter || undefined,
      search: search || undefined,
      is_active: true,
      limit: pageSize,
      offset: 0,
    }),
  })

  const sessionHandoutsQuery = useQuery({
    queryKey: ['session-handouts', sessionId],
    queryFn: () => listSessionHandouts(sessionId),
    enabled: !isNaN(sessionId),
  })

  // --- Mutations ----------------------------------------------------------

  const createMutation = useMutation({
    mutationFn: (input: {
      handoutId: number
      language: string
    }) => createSessionHandout(sessionId, {
      resource_handout_id: input.handoutId,
      given_in_language: input.language,
      delivery_method: 'printed',
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ['session-handouts', sessionId],
      })
      toast.success(t('parentOnboarding.handouts.toast.added'))
    },
    onError: () => {
      toast.error(t('parentOnboarding.handouts.toast.addError'))
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (assignmentId: number) =>
      deleteSessionHandout(sessionId, assignmentId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ['session-handouts', sessionId],
      })
      toast.success(t('parentOnboarding.handouts.toast.removed'))
    },
    onError: () => {
      toast.error(t('parentOnboarding.handouts.toast.removeError'))
    },
  })

  const printMutation = useMutation({
    mutationFn: () => requestPrintPacket(sessionId),
    onSuccess: (data) => {
      if (data.unavailable) {
        toast.error(t('parentOnboarding.handouts.printUnavailable'))
        return
      }
      if (data.packet_url) {
        window.open(data.packet_url, '_blank', 'noopener,noreferrer')
      }
    },
    onError: () => {
      toast.error(t('parentOnboarding.handouts.printUnavailable'))
    },
  })

  // --- Derived state ------------------------------------------------------

  const catalogHandouts = catalogQuery.data?.handouts ?? []
  const catalogTotal = catalogQuery.data?.total ?? 0
  const givenToday = sessionHandoutsQuery.data?.handouts ?? []

  // Map handout id -> active assignment id so the catalog row can toggle
  // its aria-pressed state and the +/Remove button mirrors the
  // given-today state.
  const handoutIdToAssignmentId = useMemo(() => {
    const m = new Map<number, number>()
    for (const a of givenToday) {
      if (a.resource_handout_id) m.set(a.resource_handout_id, a.id)
    }
    return m
  }, [givenToday])

  const showSuggested = Boolean(
    patronLanguage && patronLanguage !== 'en',
  )

  // For the disabled-print state we want to know whether any "printed"
  // item is in givenToday, per the spec UX rules.
  const hasPrintedItems = givenToday.some(
    (a) => a.delivery_method === 'printed',
  )

  // --- Render -------------------------------------------------------------

  function handleToggle(h: ResourceHandout) {
    const existing = handoutIdToAssignmentId.get(h.id)
    if (existing) {
      deleteMutation.mutate(existing)
    } else {
      // Default the assignment's language to the handout's own language;
      // an inline dropdown could override (out of scope here).
      createMutation.mutate({ handoutId: h.id, language: h.language })
    }
  }

  if (isNaN(sessionId)) return null

  return (
    <section
      aria-labelledby={headingId}
      className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-5 space-y-4"
    >
      <div className="flex items-center justify-between">
        <h2
          id={headingId}
          className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream"
        >
          {t('parentOnboarding.handouts.heading')}
        </h2>
      </div>

      {/* --- Filters --------------------------------------------------- */}
      <div className="flex flex-wrap items-center gap-2">
        <label htmlFor={searchInputId} className="sr-only">
          {t('parentOnboarding.handouts.search')}
        </label>
        <input
          id={searchInputId}
          type="search"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder={t('parentOnboarding.handouts.search')}
          className={`min-w-0 flex-1 text-sm border border-lsc-border dark:border-earth-600 rounded-lg px-3 py-2 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream ${FOCUS_RING}`}
        />
        {/* Language filter chips */}
        {(['', 'en', 'es'] as const).map((code) => (
          <button
            key={code || 'all'}
            type="button"
            aria-pressed={languageFilter === code}
            onClick={() => setLanguageFilter(code)}
            className={`px-2.5 py-1 text-xs rounded-full border ${
              languageFilter === code
                ? 'bg-lsc-rose text-white border-lsc-rose'
                : 'bg-lsc-cream dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream border-lsc-border dark:border-earth-600'
            } ${FOCUS_RING}`}
          >
            {code === ''
              ? t('parentOnboarding.handouts.filter.allLanguages')
              : code === 'en'
                ? t('parentOnboarding.handouts.filter.en')
                : t('parentOnboarding.handouts.filter.es')}
          </button>
        ))}
        {(categoryFilter || languageFilter || search) && (
          <button
            type="button"
            onClick={() => {
              setLanguageFilter('')
              setCategoryFilter('')
              setSearch('')
            }}
            className={`text-xs text-lsc-rose hover:underline ${FOCUS_RING}`}
          >
            {t('parentOnboarding.handouts.filter.clear')}
          </button>
        )}
      </div>

      {/* --- Suggested for this family --------------------------------- */}
      {showSuggested && (
        <SuggestedGroup
          patronLanguage={patronLanguage!}
          givenSet={handoutIdToAssignmentId}
          onToggle={handleToggle}
        />
      )}

      {/* --- All resources --------------------------------------------- */}
      <div className="space-y-2">
        <h3 className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
          {t('parentOnboarding.handouts.allResources', {
            count: String(catalogTotal),
          })}
        </h3>
        {catalogQuery.isLoading && (
          <p className="text-sm text-lsc-dark/60 dark:text-lsc-cream/50">
            {t('parentOnboarding.handouts.loading')}
          </p>
        )}
        {!catalogQuery.isLoading && catalogHandouts.length === 0 && (
          <p className="text-sm text-lsc-dark/60 dark:text-lsc-cream/50">
            {t('parentOnboarding.handouts.noMatches')}
          </p>
        )}
        <ul
          className="space-y-1"
          aria-label={t('parentOnboarding.handouts.allResources', {
            count: String(catalogTotal),
          })}
        >
          {catalogHandouts.map((h) => (
            <CatalogRow
              key={h.id}
              handout={h}
              isGiven={handoutIdToAssignmentId.has(h.id)}
              onToggle={() => handleToggle(h)}
              busy={createMutation.isPending || deleteMutation.isPending}
            />
          ))}
        </ul>
        {catalogTotal > catalogHandouts.length && (
          <button
            type="button"
            onClick={() => setPageSize(pageSize + DEFAULT_PAGE_SIZE)}
            className={`mt-1 text-xs text-lsc-rose hover:underline ${FOCUS_RING}`}
          >
            {t('parentOnboarding.handouts.loadMore')}
          </button>
        )}
      </div>

      {/* --- Given today ----------------------------------------------- */}
      <div className="space-y-2 pt-2 border-t border-lsc-border dark:border-earth-700">
        <h3 className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
          {t('parentOnboarding.handouts.givenToday', {
            count: String(givenToday.length),
          })}
        </h3>
        {sessionHandoutsQuery.isLoading && (
          <p className="text-sm text-lsc-dark/60 dark:text-lsc-cream/50">
            {t('parentOnboarding.handouts.loading')}
          </p>
        )}
        {!sessionHandoutsQuery.isLoading && givenToday.length === 0 && (
          <p className="text-sm text-lsc-dark/60 dark:text-lsc-cream/50">
            {t('parentOnboarding.handouts.empty')}
          </p>
        )}
        <ul
          className="space-y-1"
          aria-label={t('parentOnboarding.handouts.givenToday', {
            count: String(givenToday.length),
          })}
        >
          {givenToday.map((a) => (
            <GivenTodayRow
              key={a.id}
              assignment={a}
              onRemove={() => deleteMutation.mutate(a.id)}
              busy={deleteMutation.isPending}
            />
          ))}
        </ul>
      </div>

      {/* --- Print packet (disabled stub until cross-spec ships) ------ */}
      <div className="flex items-center justify-end pt-2">
        <button
          type="button"
          onClick={() => printMutation.mutate()}
          disabled={!hasPrintedItems || printMutation.isPending}
          aria-describedby={`${headingId}-print-help`}
          className={`inline-flex items-center gap-1.5 px-3 py-2 text-sm bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 transition-colors disabled:opacity-50 ${FOCUS_RING}`}
        >
          {printMutation.isPending ? (
            <Loader2 className="w-4 h-4 motion-safe:animate-spin" aria-hidden="true" />
          ) : (
            <Printer className="w-4 h-4" aria-hidden="true" />
          )}
          {t('parentOnboarding.handouts.printPacket', {
            count: String(
              givenToday.filter((a) => a.delivery_method === 'printed').length,
            ),
          })}
        </button>
        {/* sr-only context for screen readers when the button is disabled
            because the backend generator hasn't shipped yet. */}
        <span id={`${headingId}-print-help`} className="sr-only">
          {t('parentOnboarding.handouts.printUnavailable')}
        </span>
      </div>
    </section>
  )
}


// ---------------------------------------------------------------------------
// Subcomponents
// ---------------------------------------------------------------------------


function CatalogRow({
  handout,
  isGiven,
  onToggle,
  busy,
}: {
  handout: ResourceHandout
  isGiven: boolean
  onToggle: () => void
  busy: boolean
}) {
  const { t } = useTranslation()
  // Announce as "Add WIC Eligibility - Espanol, 2 pages, Spanish (es)."
  const pageLabel = handout.page_count
    ? t('parentOnboarding.handouts.pageCount', {
        count: String(handout.page_count),
      })
    : ''
  const langLabel = `${handout.language.toUpperCase()}`
  return (
    <li>
      <button
        type="button"
        aria-pressed={isGiven}
        onClick={onToggle}
        disabled={busy}
        className={`w-full flex items-center justify-between gap-3 px-3 py-2 rounded-lg border text-left text-sm transition-colors ${
          isGiven
            ? 'bg-status-success-50 dark:bg-status-success-900/20 border-status-success-300 dark:border-status-success-700'
            : 'bg-lsc-white dark:bg-earth-700 border-lsc-border dark:border-earth-600 hover:bg-lsc-cream dark:hover:bg-earth-600'
        } disabled:opacity-50 ${FOCUS_RING}`}
      >
        <div className="min-w-0 flex-1">
          <div className="font-medium text-lsc-dark dark:text-lsc-cream truncate">
            {handout.title}
          </div>
          <div className="text-xs text-lsc-dark/60 dark:text-lsc-cream/50">
            {pageLabel}
            {pageLabel ? ' · ' : ''}
            <span aria-label={`${t('parentOnboarding.handouts.language')}: ${langLabel}`}>
              {langLabel}
            </span>
          </div>
        </div>
        <span className="shrink-0 inline-flex items-center text-xs">
          {isGiven ? (
            <span className="text-status-success-700 dark:text-status-success-300">
              {t('parentOnboarding.handouts.added')}
            </span>
          ) : (
            <span className="text-lsc-rose inline-flex items-center gap-1">
              <Plus className="w-3 h-3" aria-hidden="true" />
              {t('parentOnboarding.handouts.add')}
            </span>
          )}
        </span>
      </button>
    </li>
  )
}


function GivenTodayRow({
  assignment,
  onRemove,
  busy,
}: {
  assignment: SessionHandout
  onRemove: () => void
  busy: boolean
}) {
  const { t } = useTranslation()
  const title = assignment.display_title ?? t('parentOnboarding.handouts.untitled')
  // Per feedback_l30_form_label_collision: the dropdown label includes the
  // resource name so two rows on the same page do not share the same
  // accessible name.
  const methodLabel = `${title} ${t('parentOnboarding.handouts.deliveryMethod').toLowerCase()}`
  const removeLabel = `${t('parentOnboarding.handouts.remove')}: ${title}`

  return (
    <li className="flex items-center gap-3 px-3 py-2 rounded-lg bg-lsc-cream/60 dark:bg-earth-700/50 border border-lsc-border/60 dark:border-earth-600/60">
      <div className="min-w-0 flex-1">
        <div className="text-sm font-medium text-lsc-dark dark:text-lsc-cream truncate">
          {title}
        </div>
        <div className="text-xs text-lsc-dark/60 dark:text-lsc-cream/50">
          {assignment.given_in_language.toUpperCase()}
          {assignment.given_by_name ? ` · ${assignment.given_by_name}` : ''}
        </div>
      </div>
      <label className="sr-only" htmlFor={`handout-method-${assignment.id}`}>
        {methodLabel}
      </label>
      <select
        id={`handout-method-${assignment.id}`}
        aria-label={methodLabel}
        defaultValue={assignment.delivery_method}
        disabled
        className="text-xs border border-lsc-border dark:border-earth-600 rounded px-2 py-1 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream disabled:opacity-70"
      >
        {DELIVERY_METHODS.map((m) => (
          <option key={m} value={m}>
            {t(`parentOnboarding.handouts.method.${m}`)}
          </option>
        ))}
      </select>
      <button
        type="button"
        onClick={onRemove}
        disabled={busy}
        aria-label={removeLabel}
        className={`inline-flex items-center gap-1 px-2 py-1 text-xs text-lsc-rose hover:underline disabled:opacity-50 ${FOCUS_RING}`}
      >
        <X className="w-3 h-3" aria-hidden="true" />
        {t('parentOnboarding.handouts.remove')}
      </button>
    </li>
  )
}


function SuggestedGroup({
  patronLanguage,
  givenSet,
  onToggle,
}: {
  patronLanguage: string
  givenSet: Map<number, number>
  onToggle: (h: ResourceHandout) => void
}) {
  const { t } = useTranslation()
  // Suggested = same query, filtered to patron language, capped at 5.
  const suggested = useQuery({
    queryKey: ['resource-handouts-suggested', patronLanguage],
    queryFn: () => listResourceHandouts({
      language: patronLanguage,
      is_active: true,
      limit: 5,
    }),
  })
  const rows = suggested.data?.handouts ?? []
  if (rows.length === 0) return null
  return (
    <div className="space-y-2 p-3 rounded-lg bg-lsc-cream/40 dark:bg-earth-700/30 border border-lsc-border/60 dark:border-earth-600/60">
      <h3 className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
        {t('parentOnboarding.handouts.suggested')}
      </h3>
      <ul className="space-y-1" aria-label={t('parentOnboarding.handouts.suggested')}>
        {rows.map((h) => (
          <CatalogRow
            key={h.id}
            handout={h}
            isGiven={givenSet.has(h.id)}
            onToggle={() => onToggle(h)}
            busy={false}
          />
        ))}
      </ul>
    </div>
  )
}


export default SessionResourceHandouts

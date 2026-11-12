/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { BookOpen, Headphones, Smartphone, Film, AlertTriangle } from 'lucide-react'
import { type Virtualizer } from '@tanstack/react-virtual'
import * as Sentry from "@/lib/sentry-lazy"
import { type CatalogDisplayItem } from '@/pages/catalog/hooks/useCatalogSearch'
import { useTranslation } from '@/i18n/I18nContext'
import { CatalogItemSkeletonList, CatalogItemSkeletonGrid } from '@/components/skeletons/CatalogItemSkeleton'
import { FORMAT_LABELS } from '@/pages/catalog/utils/catalogHelpers'
import CatalogListCard from '@/pages/catalog/components/CatalogListCard'
import CatalogGridCard from '@/pages/catalog/components/CatalogGridCard'
import type { ItemAvailabilityInfo } from '@/hooks/useAvailabilityMap'
import ZeroResultsLanguageCTA from '@/pages/catalog/components/ZeroResultsLanguageCTA'

const STAFF_ROLES = new Set(['staff', 'admin', 'super_admin', 'director', 'legal', 'bookmobile', 'homebond'])

// ---------------------------------------------------------------------------
// Copy & helpers (kept local to preserve exact behavior)
// ---------------------------------------------------------------------------

function getEmptyStateHeadline(activeQuery: string, hasFilters: boolean, t: (key: string, params?: Record<string, unknown>) => string): string {
  if (activeQuery && hasFilters) {
    return t('catalog.emptyState.queryWithFilters', { query: activeQuery })
  }
  if (activeQuery) {
    return t('catalog.emptyState.queryOnly', { query: activeQuery })
  }
  return t('catalog.emptyState.filtersOnly')
}

// Returns the page tokens to render: numbers for pages, 'ellipsis-left'/'ellipsis-right' for gaps.
// Always shows first and last; shows current ± 1; collapses gaps with an ellipsis.
function getPaginationItems(current: number, total: number): Array<number | 'ellipsis-left' | 'ellipsis-right'> {
  if (total <= 7) {
    return Array.from({ length: total }, (_, i) => i + 1)
  }
  const items: Array<number | 'ellipsis-left' | 'ellipsis-right'> = [1]
  const windowStart = Math.max(2, current - 1)
  const windowEnd = Math.min(total - 1, current + 1)
  if (windowStart > 2) items.push('ellipsis-left')
  for (let p = windowStart; p <= windowEnd; p++) items.push(p)
  if (windowEnd < total - 1) items.push('ellipsis-right')
  items.push(total)
  return items
}

interface CatalogResultsListProps {
  filteredItems: CatalogDisplayItem[]
  viewMode: 'list' | 'grid'
  isLoading: boolean
  error: Error | null
  data: { total: number; pages: number; per_page?: number; query_was_all_stopwords?: boolean } | undefined
  activeQuery: string
  hasActiveFilters: boolean
  effectiveQuietMode: boolean
  effectiveSimplifiedView: boolean
  effectiveShowImages: boolean
  speakingItemId: number | null
  onSpeak: (text: string, itemId: number) => void
  onStopSpeak: () => void
  shouldVirtualize: boolean
  virtualizer: Virtualizer<HTMLElement, Element>
  virtualScrollRef: React.RefObject<HTMLElement>
  preferPagination: boolean
  currentPage: number
  onPageChange: (page: number) => void
  didYouMean: string | null
  onDidYouMeanClick: (term: string) => void
  onClearFilters: () => void
  onBrowseFormat: (format: string) => void
  onRetry?: () => void
  /** Map of catalog item ID to user's shelf status. */
  shelfStatusMap: Map<number, string>
  availabilityMap?: Map<number, ItemAvailabilityInfo>
  /** Set of catalog item IDs that have been challenged or banned. */
  challengedItemIds?: Set<number>
  /** Current language filter value (ISO 639-2/B code). */
  languageFilter: string
  /** Current viewer's role, used to suppress the patron-facing translation CTA for staff. */
  currentUserRole?: string
}

export default function CatalogResultsList({
  filteredItems,
  viewMode,
  isLoading,
  error,
  data,
  activeQuery,
  hasActiveFilters,
  effectiveQuietMode,
  effectiveSimplifiedView,
  effectiveShowImages,
  speakingItemId,
  onSpeak,
  onStopSpeak,
  shouldVirtualize,
  virtualizer,
  virtualScrollRef,
  preferPagination,
  currentPage,
  onPageChange,
  didYouMean,
  onDidYouMeanClick,
  onClearFilters,
  onBrowseFormat,
  onRetry,
  shelfStatusMap,
  availabilityMap = new Map<number, ItemAvailabilityInfo>(),
  challengedItemIds,
  languageFilter,
  currentUserRole,
}: CatalogResultsListProps) {
  const { t } = useTranslation()
  const [searchParams] = useSearchParams()

  const buildNextPageHref = (nextPage: number): string => {
    const next = new URLSearchParams(searchParams)
    next.set('page', String(nextPage))
    return `/catalog?${next.toString()}`
  }

  // -----------------------------------------------------------------------
  // Render helpers
  // -----------------------------------------------------------------------

  const copyAvailabilityFor = (item: CatalogDisplayItem) =>
    !item.source || item.source === 'local' ? availabilityMap.get(item.id) : undefined

  const renderListItems = () => {
    // Note: If viewMode is 'grid', this function shouldn't be called.
    // This check is defensive to ensure we don't render list when grid is requested.
    if (viewMode === 'grid') {
      return renderGridItems()
    }

    if (effectiveQuietMode) {
      return (
        <div className="divide-y divide-lsc-border dark:divide-earth-700 border border-lsc-border dark:border-earth-700 rounded-xl overflow-hidden">
          {filteredItems.map((item: CatalogDisplayItem) => (
            <CatalogListCard
              key={`${item.source}-${item.id}`}
              item={item}
              {...(item.source ? { source: item.source } : {})}
              simplifiedView={effectiveSimplifiedView}
              quietMode={effectiveQuietMode}
              showImages={effectiveShowImages}
              isSpeaking={speakingItemId === item.id}
              onSpeak={(text) => onSpeak(text, item.id)}
              onStopSpeak={onStopSpeak}
              shelfStatus={shelfStatusMap.get(item.id)}
              copyAvailability={copyAvailabilityFor(item)}
              hasChallengeOrBan={challengedItemIds?.has(item.id)}
            />
          ))}
        </div>
      )
    }

    if (shouldVirtualize) {
      return (
        <div
          role="region"
          aria-label={t('aria.catalogResultsList.catalogResults')}
          tabIndex={0}
        >
          <ul
            ref={virtualScrollRef as React.RefObject<HTMLUListElement>}
            className="h-[600px] overflow-auto"
            aria-label={`${t('aria.catalogResultsList.catalogResults')} - ${filteredItems.length} items`}
          >
            <div
              style={{
                height: `${virtualizer.getTotalSize()}px`,
                width: '100%',
                position: 'relative',
              }}
            >
              {virtualizer.getVirtualItems().map((virtualRow) => {
                const item = filteredItems[virtualRow.index]
                if (!item) {
                  Sentry.captureMessage(
                    `[Catalog Bug Guard] Missing item at virtual index ${virtualRow.index}, filtered items length: ${filteredItems.length}`,
                    'warning',
                  )
                  return null
                }
                return (
                  <li
                    key={`${item.source}-${item.id}`}
                    aria-setsize={filteredItems.length}
                    aria-posinset={virtualRow.index + 1}
                    style={{
                      position: 'absolute',
                      top: 0,
                      left: 0,
                      width: '100%',
                      height: `${virtualRow.size}px`,
                      transform: `translateY(${virtualRow.start}px)`,
                    }}
                    className="pb-3"
                  >
                    <CatalogListCard
                      item={item}
                      {...(item.source != null ? { source: item.source } : {})}
                      simplifiedView={effectiveSimplifiedView}
                      quietMode={effectiveQuietMode}
                      showImages={effectiveShowImages}
                      isSpeaking={speakingItemId === item.id}
                      onSpeak={(text) => onSpeak(text, item.id)}
                      onStopSpeak={onStopSpeak}
                      shelfStatus={shelfStatusMap.get(item.id)}
                      copyAvailability={copyAvailabilityFor(item)}
                      hasChallengeOrBan={challengedItemIds?.has(item.id)}
                    />
                  </li>
                )
              })}
            </div>
          </ul>
        </div>
      )
    }

    return (
      <ul className="flex flex-col gap-3">
        {filteredItems.map((item: CatalogDisplayItem) => (
          <li key={`${item.source}-${item.id}`}>
            <CatalogListCard
              item={item}
              {...(item.source ? { source: item.source } : {})}
              simplifiedView={effectiveSimplifiedView}
              quietMode={effectiveQuietMode}
              showImages={effectiveShowImages}
              isSpeaking={speakingItemId === item.id}
              onSpeak={(text) => onSpeak(text, item.id)}
              onStopSpeak={onStopSpeak}
              shelfStatus={shelfStatusMap.get(item.id)}
              copyAvailability={copyAvailabilityFor(item)}
              hasChallengeOrBan={challengedItemIds?.has(item.id)}
            />
          </li>
        ))}
      </ul>
    )
  }

  const renderGridItems = () => (
    <ul className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-x-6 gap-y-9">
      {filteredItems.map((item: CatalogDisplayItem) => (
        <li key={`${item.source}-${item.id}`}>
          <CatalogGridCard item={item} {...(item.source ? { source: item.source } : {})} shelfStatus={shelfStatusMap.get(item.id)} copyAvailability={copyAvailabilityFor(item)} hasChallengeOrBan={challengedItemIds?.has(item.id)} />
        </li>
      ))}
    </ul>
  )

  return (
    <>
      {/* Loading state — skeleton count mirrors the previous result count so the
          layout doesn't shift when real results paint. Falls back to the page-size
          defaults (8 grid / 5 list) on the very first fetch when no prior data exists. */}
      {isLoading && (() => {
        const defaultCount = viewMode === 'grid' ? 8 : 5
        const cap = data?.per_page ?? defaultCount
        const skeletonCount = data?.total
          ? Math.max(1, Math.min(data.total, cap))
          : defaultCount
        return (
          <div className="space-y-4">
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">{t('catalog.loadingItems')}</p>
            {viewMode === 'grid'
              ? <CatalogItemSkeletonGrid count={skeletonCount} />
              : <CatalogItemSkeletonList count={skeletonCount} />}
          </div>
        )
      })()}

      {/* Error state */}
      {error && (
        <div className="text-center py-8" role="alert">
          <AlertTriangle className="w-12 h-12 mx-auto mb-4 text-status-warning-500" aria-hidden="true" />
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
            {t('catalog.unableToLoad')}
          </p>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
            {t('catalog.unableToLoadHelp')}
          </p>
          <button
            onClick={() => onRetry ? onRetry() : window.location.reload()}
            className="mt-4 px-4 py-2 bg-forest-800 text-white rounded-lg hover:bg-forest-900"
          >
            {t('catalog.refreshPage')}
          </button>
        </div>
      )}

      {/* Results */}
      {!isLoading && data && filteredItems.length > 0 && (activeQuery || hasActiveFilters) && (
        <>
          {viewMode === 'list' ? renderListItems() : renderGridItems()}

          {/* Pagination + back to top */}
          <div className="mt-8 text-center space-y-5">
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 font-medium">
              {t('catalog.results.showingOf', { showing: filteredItems.length, total: data.total })}
            </p>

            {/* Load More (non-pagination mode) */}
            {!preferPagination && filteredItems.length < data.total && (
              <Link
                to={buildNextPageHref(currentPage + 1)}
                className="inline-block px-7 py-[11px] min-h-[44px] border-2 border-forest-700 rounded-lg text-forest-800 dark:text-forest-500 text-sm font-bold bg-lsc-white dark:bg-earth-800 hover:bg-forest-700/10"
              >
                {t('catalog.results.viewAllResults', { total: data.total })}
              </Link>
            )}

            {/* Pagination controls */}
            {preferPagination && data.pages > 1 && (
              <nav
                className="flex items-center justify-center gap-1 flex-wrap"
                aria-label={t('catalog.pagination.label', 'Pagination')}
              >
                <button
                  onClick={() => onPageChange(Math.max(1, currentPage - 1))}
                  disabled={currentPage === 1}
                  className="px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-lsc-cream dark:hover:bg-lsc-brown"
                  aria-label={t('common.previous')}
                >
                  {t('common.previous')}
                </button>
                {getPaginationItems(currentPage, data.pages).map((item, idx) =>
                  item === 'ellipsis-left' || item === 'ellipsis-right' ? (
                    <span
                      key={`${item}-${idx}`}
                      aria-hidden="true"
                      className="px-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 select-none"
                    >
                      &hellip;
                    </span>
                  ) : (
                    <button
                      key={item}
                      onClick={() => onPageChange(item)}
                      aria-label={t('catalog.pagination.goToPage', 'Go to page {{page}}').replace('{{page}}', String(item))}
                      aria-current={item === currentPage ? 'page' : undefined}
                      className={item === currentPage
                        ? 'min-w-[40px] px-3 py-2 rounded-lg border border-lsc-rose bg-lsc-rose text-white text-sm font-semibold'
                        : 'min-w-[40px] px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 text-sm text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-lsc-brown'}
                    >
                      {item}
                    </button>
                  ),
                )}
                <button
                  onClick={() => onPageChange(Math.min(data.pages, currentPage + 1))}
                  disabled={currentPage === data.pages}
                  className="px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-lsc-cream dark:hover:bg-lsc-brown"
                  aria-label={t('common.next')}
                >
                  {t('common.next')}
                </button>
              </nav>
            )}

            <div className="pt-3 border-t border-dashed border-lsc-border dark:border-earth-700">
              <a
                href="#results-top"
                className="inline-block text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose dark:hover:text-lsc-rose transition-colors"
              >
                &uarr; {t('catalog.results.backToTop')}
              </a>
            </div>
          </div>
        </>
      )}

      {/* Empty state: search / filters active but no results */}
      {data && filteredItems.length === 0 && (activeQuery || hasActiveFilters) && (
        <div role="status" className="text-center py-12 text-lsc-dark/70 dark:text-lsc-cream/70">
          {!effectiveQuietMode && (
            <BookOpen aria-hidden="true" className="w-16 h-16 mx-auto mb-4 opacity-50" />
          )}
          <p className="mb-2 text-lg font-semibold">{getEmptyStateHeadline(activeQuery, hasActiveFilters, t)}</p>

          {!effectiveQuietMode && (
            <p className="text-sm mb-5 max-w-md mx-auto">
              {hasActiveFilters && activeQuery
                ? t('catalog.emptyStateSuggestionBoth', 'Try removing some filters or broadening your search terms.')
                : hasActiveFilters
                  ? t('catalog.emptyStateSuggestionFilters', 'Try removing or changing your active filters to see more results.')
                  : t('catalog.tryDifferentSearch')}
            </p>
          )}

          {didYouMean && (
            <p className="text-sm mb-4">
              {t('catalog.results.didYouMean')}{' '}
              <button
                onClick={() => onDidYouMeanClick(didYouMean)}
                className="text-forest-800 dark:text-forest-500 font-semibold hover:underline"
              >
                &ldquo;{didYouMean}&rdquo;
              </button>
              ?
            </p>
          )}

          <button
            onClick={onClearFilters}
            className="mb-6 px-5 py-2.5 bg-lsc-rose text-white font-semibold rounded-lg hover:bg-lsc-rose/90 transition-colors"
          >
            {hasActiveFilters ? t('catalog.clearAllFilters', 'Clear all filters') : t('catalog.clearSearch', 'Clear search')}
          </button>

          {activeQuery && data.total === 0 && (
            <p className="mb-6 text-sm">
              {t('catalog.partnerSearchCta', "Can't find it? ")}{' '}
              <Link
                to={`/catalog/partner-search?q=${encodeURIComponent(activeQuery)}`}
                className="font-semibold text-lsc-rose hover:underline"
              >
                {t('catalog.partnerSearchCtaLink', 'Search partner libraries →')}
              </Link>
            </p>
          )}

          {data.total === 0 && languageFilter && !(currentUserRole && STAFF_ROLES.has(currentUserRole)) && (
            <ZeroResultsLanguageCTA languageCode={languageFilter} />
          )}

          {!effectiveQuietMode && !effectiveSimplifiedView && (
            <div className="pt-6 border-t border-lsc-border dark:border-earth-700">
              <p className="text-sm mb-4 font-medium">{t('catalog.results.exploreByType')}</p>
              <div className="flex flex-wrap justify-center gap-3">
                {[
                  { type: 'book', icon: <BookOpen className="w-4 h-4" aria-hidden="true" /> },
                  { type: 'audiobook', icon: <Headphones className="w-4 h-4" aria-hidden="true" /> },
                  { type: 'ebook', icon: <Smartphone className="w-4 h-4" aria-hidden="true" /> },
                  { type: 'dvd', icon: <Film className="w-4 h-4" aria-hidden="true" /> },
                ].map(({ type, icon }) => (
                  <button
                    key={type}
                    onClick={() => onBrowseFormat(type)}
                    className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-forest-500/30 hover:border-forest-500 hover:bg-forest-500/10 text-lsc-dark dark:text-lsc-cream transition-colors"
                  >
                    {icon}
                    <span>{FORMAT_LABELS[type]}</span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </>
  )
}

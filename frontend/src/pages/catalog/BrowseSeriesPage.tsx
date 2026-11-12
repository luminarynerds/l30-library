/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import {
  BookOpen,
  Loader2,
  Search,
  X,
  BookText,
} from 'lucide-react'
import { searchCatalog, type FacetValue } from '@/api/api'
import { useTranslation } from '@/i18n/I18nContext'
import { clsx } from '@/utils/helpers'
import { Button } from '@/components/ui/Button'
import { usePageTitle } from '@/hooks/usePageTitle'

export default function BrowseSeriesPage(): React.ReactElement {
  const { t } = useTranslation()
  usePageTitle(t('browseSeries.heading', 'Browse Series'))
  const [searchQuery, setSearchQuery] = useState('')

  // Server-side series facet: exact-match counts on CatalogItem.series_name
  // (top series by holdings count). One request; filtering happens client-side
  // against the facet values, never against item titles.
  const { data, isLoading } = useQuery({
    queryKey: ['catalog-series-facets'],
    queryFn: () => searchCatalog({ per_page: 1, include_facets: true }),
    staleTime: 5 * 60 * 1000,
  })

  const allSeries: FacetValue[] = data?.facets?.series ?? []
  const normalizedQuery = searchQuery.trim().toLowerCase()
  const seriesList = normalizedQuery
    ? allSeries.filter((s) => s.value.toLowerCase().includes(normalizedQuery))
    : allSeries

  const handleClearSearch = () => {
    setSearchQuery('')
  }

  return (
    <div className={clsx('space-y-8 px-4 py-8 bg-lsc-cream dark:bg-lsc-dark min-h-screen')}>
      <div className="text-center space-y-4 max-w-4xl mx-auto">
        <p className="inline-flex items-center rounded-full bg-lsc-rose/10 dark:bg-lsc-rose/20 px-4 py-1.5 text-xs font-semibold tracking-wide text-earth-600 dark:text-lsc-cream/80">
          {t('browseSeries.badge', 'Series browser')}
        </p>
        <h1 className="text-3xl sm:text-4xl md:text-5xl font-serif font-bold text-lsc-dark dark:text-lsc-cream leading-relaxed">
          {t('browseSeries.heading', 'Browse Series')}
        </h1>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-lg leading-relaxed max-w-3xl mx-auto">
          {t('browseSeries.subtitle', 'The most collected series in our catalog. Pick one to see every title we hold.')}
        </p>
      </div>

      {/* Search Bar */}
      <form className="max-w-3xl mx-auto w-full" onSubmit={(e) => e.preventDefault()}>
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" aria-hidden="true" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              maxLength={1000}
              placeholder={t('browseSeries.searchPlaceholder', 'Filter series by name...')}
              aria-label={t('aria.browseSeries.searchSeries')}
              className="w-full pl-10 pr-10 py-3 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream placeholder-earth-500 dark:placeholder-earth-500 focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
            />
            {searchQuery && (
              <Button variant="secondary" size="sm"
                type="button"
                onClick={handleClearSearch}
                aria-label={t('aria.advancedStaffSearchModal.clearSearch')}
              >
                <X className="w-5 h-5" aria-hidden="true" />
              </Button>
            )}
          </div>
        </div>
      </form>

      {/* Results */}
      <div aria-live="polite" aria-atomic="true" className="sr-only">
        {isLoading
          ? t('browseSeries.loading', 'Loading series…')
          : t('browseSeries.foundCount', { count: seriesList.length })}
      </div>
      {isLoading ? (
        <div className="flex items-center justify-center py-12" aria-busy="true">
          <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" aria-hidden="true" />
        </div>
      ) : seriesList.length > 0 ? (
        <div className="max-w-6xl mx-auto">
          <div className="bg-lsc-cream/50 dark:bg-lsc-dark/30 rounded-lg p-4 mb-6">
            <p className="text-sm text-lsc-dark/80 dark:text-lsc-cream/90 font-medium">
              {t('browseSeries.foundCount', { count: seriesList.length })}
            </p>
          </div>

          <ul className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 list-none p-0">
            {seriesList.map((series) => (
              <li key={series.value}>
                <article className="h-full bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-5 hover:shadow-md transition-all duration-200 space-y-2">
                  <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream line-clamp-2" title={series.value}>
                    <Link
                      to={`/catalog?series_facets=${encodeURIComponent(series.value)}`}
                      className="hover:underline focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-2 dark:focus:ring-offset-lsc-dark rounded-sm"
                    >
                      {series.value}
                    </Link>
                  </h2>

                  <div className="flex items-center gap-2 pt-2 border-t border-lsc-border dark:border-earth-700">
                    <span className="inline-flex items-center gap-1 px-3 py-1 bg-lsc-rose/10 text-lsc-rose rounded-full text-sm font-medium">
                      <BookText className="w-4 h-4" aria-hidden="true" />
                      {t('browseSeries.titleCount', { count: series.count })}
                    </span>
                  </div>

                  <div className="pt-2">
                    <Link
                      to={`/catalog?series_facets=${encodeURIComponent(series.value)}`}
                      className="text-sm font-medium text-lsc-rose hover:underline focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-2 dark:focus:ring-offset-lsc-dark rounded-sm"
                      aria-label={t('aria.browseSeries.seeTitlesIn', { seriesName: series.value })}
                    >
                      {t('browseSeries.seeTitles', 'See titles in this series')}
                    </Link>
                  </div>
                </article>
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <div className="text-center py-12 text-lsc-dark/70 dark:text-lsc-cream/70">
          <BookOpen aria-hidden="true" className="w-16 h-16 mx-auto mb-4 opacity-50" />
          <p className="mb-4 text-lg">{t('browseSeries.emptyHeading', 'No series found')}</p>
          <p className="text-sm mb-3">
            {normalizedQuery
              ? t('browseSeries.emptyFiltered', 'No series match that name. Try a shorter search, or search the full catalog.')
              : t('browseSeries.emptyNone', 'No items in the catalog have series information yet.')}
          </p>
          <Link to="/catalog" className="text-sm font-medium text-lsc-rose hover:underline">
            {t('browseSeries.browseCatalog', 'Browse the full catalog')}
          </Link>
        </div>
      )}
    </div>
  )
}

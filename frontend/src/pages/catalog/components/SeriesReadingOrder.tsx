/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Link } from 'react-router-dom'
import { ChevronLeft, ChevronRight, BookMarked } from 'lucide-react'
import type { CatalogItem, SeriesReadingOrder as SeriesReadingOrderData } from '@/api/api'
import { useTranslation } from '@/i18n/I18nContext'

interface SeriesReadingOrderProps {
  item: CatalogItem
  series: SeriesReadingOrderData | undefined
}

/**
 * Reading-order context block for the catalog item page.
 *
 * Honesty rules baked in:
 *  - Shows "Book N in [series]" ONLY when the current item has a parsed
 *    numeric position. Never fabricates a position.
 *  - Never claims a series length ("of M"). We only hold a subset, so the copy
 *    says we're showing the titles in the series that are in our catalog.
 *  - prev/next are the adjacent titles WE HOLD by position, labeled "in our
 *    catalog" so it never reads as "next published".
 * Renders nothing when there's no parsed position or no series payload.
 */
export function SeriesReadingOrder({ item, series }: SeriesReadingOrderProps): React.ReactElement | null {
  const { t } = useTranslation()

  if (item.series_position == null || !series || !series.series_name) {
    return null
  }

  const prev = series.prev_id != null ? series.items.find((m) => m.id === series.prev_id) : undefined
  const next = series.next_id != null ? series.items.find((m) => m.id === series.next_id) : undefined

  return (
    <section
      aria-label={t('aria.seriesReadingOrder.region')}
      className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm p-6 md:p-8"
    >
      <div className="flex items-center gap-2 mb-1">
        <BookMarked className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
        <h2 className="text-xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
          {t('catalogItem.series.readingOrder.heading')}
        </h2>
      </div>

      <p className="text-lsc-dark dark:text-lsc-cream font-medium">
        {t('catalogItem.series.readingOrder.bookN', {
          position: item.series_position,
          seriesName: series.series_name,
        })}
      </p>

      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60 mt-1">
        {t('catalogItem.series.readingOrder.inCatalogNote', { count: series.total_held })}
      </p>

      {/* Prev / next adjacent held titles */}
      {(prev || next) && (
        <div className="flex flex-col sm:flex-row gap-3 mt-4">
          {prev ? (
            <Link
              to={`/catalog/${prev.id}`}
              state={{ fromCatalog: true }}
              className="flex-1 flex items-center gap-2 px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 hover:border-lsc-rose hover:bg-lsc-rose/5 dark:hover:bg-lsc-rose/10 transition-colors"
              aria-label={t('aria.seriesReadingOrder.previous', { title: prev.title })}
            >
              <ChevronLeft className="w-4 h-4 text-lsc-rose dark:text-lsc-rose-light flex-shrink-0" aria-hidden="true" />
              <span className="min-w-0">
                <span className="block text-xs text-lsc-dark/60 dark:text-lsc-cream/50">
                  {t('catalogItem.series.readingOrder.previous')}
                </span>
                <span className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream truncate">
                  {prev.series_position != null
                    ? `${t('catalogItem.series.readingOrder.positionLabel', { position: prev.series_position })} · `
                    : ''}
                  {prev.title}
                </span>
              </span>
            </Link>
          ) : (
            <span className="flex-1" aria-hidden="true" />
          )}

          {next ? (
            <Link
              to={`/catalog/${next.id}`}
              state={{ fromCatalog: true }}
              className="flex-1 flex items-center justify-end gap-2 px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 hover:border-lsc-rose hover:bg-lsc-rose/5 dark:hover:bg-lsc-rose/10 transition-colors text-right"
              aria-label={t('aria.seriesReadingOrder.next', { title: next.title })}
            >
              <span className="min-w-0">
                <span className="block text-xs text-lsc-dark/60 dark:text-lsc-cream/50">
                  {t('catalogItem.series.readingOrder.next')}
                </span>
                <span className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream truncate">
                  {next.series_position != null
                    ? `${t('catalogItem.series.readingOrder.positionLabel', { position: next.series_position })} · `
                    : ''}
                  {next.title}
                </span>
              </span>
              <ChevronRight className="w-4 h-4 text-lsc-rose dark:text-lsc-rose-light flex-shrink-0" aria-hidden="true" />
            </Link>
          ) : (
            <span className="flex-1" aria-hidden="true" />
          )}
        </div>
      )}

      <Link
        to={`/catalog?series_facets=${encodeURIComponent(series.series_name)}`}
        className="inline-block mt-4 text-sm text-lsc-rose dark:text-lsc-rose-light hover:underline font-medium"
      >
        {t('catalogItem.series.readingOrder.viewAll')}
      </Link>
    </section>
  )
}

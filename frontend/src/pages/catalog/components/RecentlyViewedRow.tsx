/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { History } from 'lucide-react'
import { useTranslation } from '@/i18n/I18nContext'
import { getCatalogItem, type CatalogItem } from '@/api/domains/catalog/catalog-api'
import CatalogItemThumbnail, { CatalogCover } from './CatalogItemThumbnail'
import { catalogItemLink } from '../utils/catalogHelpers'
import { useRecentlyViewed } from '../hooks/useRecentlyViewed'

interface RecentlyViewedRowProps {
  showImages: boolean
}

export default function RecentlyViewedRow({ showImages }: RecentlyViewedRowProps) {
  const { t } = useTranslation()
  const { ids, clear } = useRecentlyViewed()

  // Fetch the full items in one batched query keyed on the id list. Items that
  // 404 (deleted from the catalog) are silently dropped so the strip degrades
  // gracefully if a patron's history references stale ids.
  const { data: items } = useQuery({
    queryKey: ['catalog', 'recently-viewed', ids],
    enabled: ids.length > 0,
    staleTime: 5 * 60 * 1000,
    queryFn: async (): Promise<CatalogItem[]> => {
      const settled = await Promise.allSettled(ids.map((id) => getCatalogItem(id)))
      return settled
        .filter((r): r is PromiseFulfilledResult<CatalogItem> => r.status === 'fulfilled')
        .map((r) => r.value)
    },
  })

  if (!items || items.length < 2) return null

  return (
    <div className="mb-8">
      <div className="flex items-center justify-between mb-1">
        <h2 className="text-lg font-serif font-bold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
          <History className="w-5 h-5 text-lsc-rose" aria-hidden="true" />
          {t('catalog.recentlyViewed.title', 'Pick up where you left off')}
        </h2>
        <button
          onClick={clear}
          className="text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose transition-colors"
        >
          {t('catalog.recentlyViewed.clear', 'Clear history')}
        </button>
      </div>
      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60 mb-3">
        {t('catalog.recentlyViewed.subtitle', 'Items you opened recently. Stored only on this device.')}
      </p>
      <div
        className="flex overflow-x-auto scrollbar-hide pb-2"
        role="list"
        aria-label={t('catalog.recentlyViewed.ariaLabel', 'Recently viewed items')}
      >
        <div className="flex gap-4">
          {items.map((item) => (
            <Link
              key={item.id}
              to={catalogItemLink(item.id, item.title)}
              state={{ fromCatalog: true }}
              role="listitem"
              className="flex-shrink-0 w-[130px] group focus:outline-none focus:ring-2 focus:ring-lsc-rose rounded-xl"
            >
              {showImages ? (
                <div className="w-full h-[180px] rounded-xl overflow-hidden bg-lsc-border dark:bg-earth-700 shadow-sm mb-2">
                  {item.cover_url ? (
                    <CatalogCover
                      coverUrl={item.cover_url}
                      itemId={item.id}
                      alt=""
                      title={item.title}
                      itemType={item.item_type}
                    />
                  ) : (
                    <CatalogItemThumbnail title={item.title} itemType={item.item_type} />
                  )}
                </div>
              ) : (
                <div className="w-full h-10 rounded-lg bg-lsc-border dark:bg-earth-700 mb-2 flex items-center justify-center">
                  <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 capitalize">
                    {item.item_type}
                  </span>
                </div>
              )}
              <h3
                className="text-sm font-bold text-lsc-dark dark:text-lsc-cream leading-snug line-clamp-2 group-hover:text-lsc-rose transition-colors"
                title={item.title}
              >
                {item.title}
              </h3>
              {item.author && (
                <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 truncate" title={item.author}>
                  {item.author}
                </p>
              )}
            </Link>
          ))}
        </div>
      </div>
    </div>
  )
}

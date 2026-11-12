/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { useTranslation } from '@/i18n/I18nContext'
import { getNewArrivals } from '@/api/domains/catalog/catalog-api'
import CatalogItemThumbnail, { CatalogCover } from './CatalogItemThumbnail'
import { catalogItemLink } from '../utils/catalogHelpers'

interface NewArrivalsRowProps {
  showImages: boolean
}

export default function NewArrivalsRow({ showImages }: NewArrivalsRowProps) {
  const { t } = useTranslation()

  const { data } = useQuery({
    queryKey: ['catalog', 'new-arrivals'],
    queryFn: () => getNewArrivals({ days: 14, limit: 12 }),
    staleTime: 5 * 60 * 1000,
  })

  if (!data || data.items.length < 3) return null

  const heading = data.period === 'week'
    ? t('catalog.newArrivals.titleWeek')
    : t('catalog.newArrivals.titleMonth')

  return (
    <div className="mb-8">
      <h2 className="text-lg font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-1">
        {heading}
      </h2>
      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60 mb-3">
        {t('catalog.newArrivals.subtitle')}
      </p>
      <div
        className="flex overflow-x-auto scrollbar-hide pb-2"
        role="list"
        aria-label={t('catalog.newArrivals.ariaLabel')}
      >
        <div className="flex gap-4">
          {data.items.map((item) => (
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

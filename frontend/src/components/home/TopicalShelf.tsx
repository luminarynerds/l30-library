/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Patron-facing topical shelf.
 *
 * Renders a single shelf from GET /home/page (PR #670). The backend already
 * suppresses empty shelves, so we assume `items` has length >= 1.
 */
import { useState } from 'react'
import { Link } from 'react-router-dom'
import type { HomeItemCard, PublicShelfRead } from '@/api/home'
import { coverProxyUrl, buildCoverAlt } from '@/pages/catalog/utils/catalogHelpers'
import CatalogItemThumbnail from '@/pages/catalog/components/CatalogItemThumbnail'
import { useTranslation } from '@/i18n/I18nContext'

interface TopicalShelfProps {
  shelf: PublicShelfRead
}

function ShelfCard({ item }: { item: HomeItemCard }): React.ReactElement {
  // The cover proxy 404s for items without a cover; fall back to the
  // generative thumbnail instead of leaving a broken image.
  const [imageError, setImageError] = useState(false)
  return (
    <Link
      to={`/catalog/${item.id}`}
      className="group block focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2 rounded-xl"
    >
      <div className="aspect-[2/3] rounded-xl overflow-hidden bg-lsc-cream dark:bg-earth-800 border border-lsc-border dark:border-earth-700 shadow-sm motion-safe:group-hover:scale-[1.02] motion-safe:transition-transform">
        {imageError ? (
          <CatalogItemThumbnail
            title={item.title}
            {...(item.item_type ? { itemType: item.item_type } : {})}
            size="lg"
            className="w-full"
          />
        ) : (
          <img
            src={coverProxyUrl(item.id)}
            alt={buildCoverAlt(item.title, item.author, item.item_type)}
            loading="lazy"
            className="w-full h-full object-cover"
            onError={() => setImageError(true)}
          />
        )}
      </div>
      <div className="pt-3 space-y-1">
        <p className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream line-clamp-2 leading-snug">
          {item.title}
        </p>
        {item.author && (
          <p className="text-xs text-earth-600 dark:text-earth-400 line-clamp-1">
            {item.author}
          </p>
        )}
      </div>
    </Link>
  )
}

export default function TopicalShelf({ shelf }: TopicalShelfProps): React.ReactElement {
  const { t } = useTranslation()
  const headingId = `home-shelf-${shelf.slug || shelf.id}`

  return (
    <section aria-labelledby={headingId} className="space-y-5 md:space-y-6">
      <div className="space-y-2">
        <h2
          id={headingId}
          className="font-serif text-2xl md:text-3xl text-lsc-dark dark:text-lsc-cream leading-tight"
        >
          {shelf.heading}
        </h2>
        {shelf.description && (
          <p className="text-base text-earth-700 dark:text-earth-300 max-w-3xl">
            {shelf.description}
          </p>
        )}
      </div>

      <ul className="flex gap-4 overflow-x-auto snap-x snap-mandatory -mx-6 px-6 pb-3 md:mx-0 md:grid md:grid-cols-3 md:gap-6 md:overflow-visible md:px-0 md:pb-0 lg:grid-cols-6 list-none m-0">
        {shelf.items.map((item) => (
          <li key={item.id} className="w-[42vw] min-w-[140px] max-w-[172px] shrink-0 snap-start md:w-auto md:min-w-0 md:max-w-none">
            <ShelfCard item={item} />
          </li>
        ))}
      </ul>

      {shelf.view_all_href && (
        <div>
          <Link
            to={shelf.view_all_href}
            className="inline-flex min-h-[44px] items-center gap-2 text-base font-bold text-sage-700 dark:text-lsc-rose hover:text-sage-800 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2 rounded-sm"
          >
            {t('home.shelves.seeMore', 'See more')} <span aria-hidden="true">→</span>
          </Link>
        </div>
      )}
    </section>
  )
}

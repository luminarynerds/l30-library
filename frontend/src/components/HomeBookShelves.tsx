/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useQueries } from '@tanstack/react-query'
import { BookOpen } from 'lucide-react'
import { getNewArrivals } from '@/api/domains/catalog/catalog-api'
import {
  getPublicStaffPicksLists,
  getPublicStaffPicksList,
} from '@/api/domains/content/staff-picks-api'
import { useTranslation } from '@/i18n/I18nContext'

interface ShelfCardItem {
  id: number
  title: string
  author: string | null
  cover_url: string | null
  note: string | null
}

interface ShelfProps {
  title: string
  subtitle?: string | null
  items: ShelfCardItem[]
  ariaLabel: string
  /** When true, lay out covers in a denser 3-up gallery row on lg+. */
  fullWidth?: boolean
}

function ShelfCover({ src }: { src: string | null }): React.ReactElement {
  const [failed, setFailed] = useState(false)
  if (!src || failed) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-lsc-cream via-lsc-cream/80 to-sage-100 dark:from-earth-700 dark:to-earth-800">
        <BookOpen className="w-10 h-10 text-lsc-rose/40" aria-hidden="true" />
      </div>
    )
  }
  return (
    <img
      src={src}
      alt=""
      loading="lazy"
      onError={() => setFailed(true)}
      className="w-full h-full object-cover"
    />
  )
}

function Shelf({ title, subtitle, items, ariaLabel, fullWidth = false }: ShelfProps): React.ReactElement {
  const gridCols = fullWidth
    ? 'grid grid-cols-2 sm:grid-cols-3 gap-5 md:gap-7 lg:gap-8'
    : 'grid grid-cols-3 gap-4 md:gap-5'

  return (
    <section aria-label={ariaLabel} className="space-y-7">
      <div className="space-y-1.5">
        <h2 className="font-serif text-2xl md:text-3xl lg:text-4xl text-lsc-dark dark:text-lsc-cream leading-tight">
          {title}
        </h2>
        {subtitle && (
          <p className="text-base text-earth-700 dark:text-earth-400">{subtitle}</p>
        )}
      </div>

      <ul className={gridCols + ' list-none'}>
        {items.slice(0, 6).map((item) => (
          <li key={item.id}>
            <Link
              to={`/catalog/${item.id}`}
              className="group block rounded-xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2"
            >
              <div className="aspect-[2/3] rounded-xl overflow-hidden bg-lsc-cream dark:bg-earth-800 border border-lsc-border dark:border-earth-700 shadow-sm motion-safe:group-hover:scale-[1.04] motion-safe:group-hover:shadow-soft-lg motion-safe:transition-all motion-safe:duration-300">
                <ShelfCover src={item.cover_url} />
              </div>

              <div className="mt-3 space-y-1">
                <p className="font-serif text-sm md:text-base font-semibold text-lsc-dark dark:text-lsc-cream leading-snug line-clamp-2 group-hover:text-lsc-rose dark:group-hover:text-lsc-rose-light transition-colors">
                  {item.title}
                </p>
                {item.author && (
                  <p className="text-xs md:text-sm italic text-earth-700 dark:text-earth-400 line-clamp-1">
                    {item.author}
                  </p>
                )}
                {item.note && (
                  <p className="text-xs text-earth-600 dark:text-earth-500 line-clamp-2 italic leading-relaxed pt-1">
                    &ldquo;{item.note}&rdquo;
                  </p>
                )}
              </div>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  )
}

export default function HomeBookShelves(): React.ReactElement | null {
  const { t } = useTranslation()

  const { data: arrivals } = useQuery({
    queryKey: ['home-new-arrivals'],
    queryFn: () => getNewArrivals({ limit: 6, days: 30 }),
    staleTime: 600_000,
  })

  const { data: picksLists } = useQuery({
    queryKey: ['home-staff-picks-lists'],
    queryFn: () => getPublicStaffPicksLists(10),
    staleTime: 600_000,
  })

  const lists = picksLists ?? []
  const detailQueries = useQueries({
    queries: lists.map((list) => ({
      queryKey: ['home-staff-picks-list', list.id],
      queryFn: () => getPublicStaffPicksList(list.id),
      staleTime: 600_000,
    })),
  })

  const arrivalItems: ShelfCardItem[] =
    arrivals?.items?.map((i) => ({
      id: i.id,
      title: i.title,
      author: i.author,
      cover_url: i.cover_url,
      note: null,
    })) ?? []

  const pickShelves = detailQueries
    .map((q) => q.data)
    .filter((detail): detail is NonNullable<typeof detail> => !!detail)
    .map((detail) => ({
      id: detail.id,
      title: detail.title,
      subtitle: detail.description,
      items: detail.items.map((i) => ({
        id: i.catalog_item.id,
        title: i.catalog_item.title,
        author: i.catalog_item.author ?? null,
        cover_url: i.catalog_item.cover_url ?? null,
        note: i.staff_notes ?? null,
      })),
    }))
    .filter((shelf) => shelf.items.length > 0)

  const hasArrivals = arrivalItems.length > 0
  const hasPicks = pickShelves.length > 0
  if (!hasArrivals && !hasPicks) return null

  return (
    <section
      aria-label={t('catalog.newArrivals.ariaLabel')}
      className="max-w-6xl mx-auto px-6"
    >
      <div className="grid grid-cols-1 gap-12 lg:gap-14">
        {hasArrivals && (
          <Shelf
            title={t('catalog.newArrivals.titleMonth')}
            subtitle={t('catalog.newArrivals.subtitle')}
            items={arrivalItems}
            ariaLabel={t('catalog.newArrivals.ariaLabel')}
            fullWidth
          />
        )}
        {pickShelves.map((shelf) => (
          <Shelf
            key={shelf.id}
            title={shelf.title}
            subtitle={shelf.subtitle}
            items={shelf.items}
            ariaLabel={shelf.title}
            fullWidth
          />
        ))}
      </div>
    </section>
  )
}

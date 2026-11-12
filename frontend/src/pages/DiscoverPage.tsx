/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Discover — the library's front door. Leads with New Arrivals, offers
 * reader-shelf doorways, and routes to /picks (curation) and /catalog
 * (full browse) rather than duplicating either in-page.
 */
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import CatalogShelf from '@/pages/catalog/components/CatalogShelf'
import { getNewArrivals } from '@/api/domains/catalog/catalog-api'
import { getDiscoverShelves, type DiscoverShelfSummary } from '@/api/discover-shelves-api'
import { t, useLanguage } from '@/i18n'

function ShelfDoorways(): React.ReactElement | null {
  const { language } = useLanguage()
  const { data } = useQuery({
    queryKey: ['discover-shelves', language],
    queryFn: () => getDiscoverShelves(undefined, language),
    staleTime: 5 * 60 * 1000,
  })
  const shelves = (data ?? []).filter((s: DiscoverShelfSummary) => s.item_count > 0)
  if (shelves.length === 0) return null

  return (
    <section aria-labelledby="discover-shelves-heading" className="space-y-4">
      <h2 id="discover-shelves-heading" className="text-lg font-serif font-bold text-lsc-dark dark:text-lsc-cream">
        {t('discover.shelves.heading', 'Reader shelves')}
      </h2>
      <ul className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 list-none p-0">
        {shelves.map((shelf) => {
          const count = t('discover.shelves.titleCount', { count: shelf.item_count })
          return (
            <li key={shelf.id}>
              <Link
                to={`/catalog?shelf=${encodeURIComponent(shelf.slug)}`}
                aria-label={t('discover.shelves.shelfAria', { title: shelf.title, count: shelf.item_count })}
                className="flex flex-col gap-1.5 h-full rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 p-4 hover:-translate-y-0.5 motion-reduce:transform-none transition-transform focus-ring"
              >
                <span className="font-serif font-bold text-lsc-rose">{shelf.title}</span>
                <span className="text-sm text-earth-600 dark:text-cream-400">{count}</span>
                <span aria-hidden="true" className="mt-1 text-sm font-semibold text-lsc-rose">
                  {t('discover.shelves.open', 'Open shelf')} →
                </span>
              </Link>
            </li>
          )
        })}
      </ul>
    </section>
  )
}

function KeepExploring(): React.ReactElement {
  return (
    <section aria-labelledby="discover-explore-heading" className="space-y-4">
      <h2 id="discover-explore-heading" className="text-lg font-serif font-bold text-lsc-dark dark:text-lsc-cream">
        {t('discover.explore.heading', 'Keep exploring')}
      </h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Link
          to="/picks"
          className="flex flex-col min-h-[9rem] rounded-xl bg-lsc-rose text-white p-6 hover:-translate-y-0.5 motion-reduce:transform-none transition-transform focus-ring"
        >
          <span className="font-serif text-xl font-bold">{t('discover.explore.picksTitle', 'Curated Picks')}</span>
          <span className="text-sm text-white mt-1 max-w-[34ch]">
            {t('discover.explore.picksBody', 'Staff favorites that reflect the full range of who walks through our doors.')}
          </span>
          <span className="mt-auto pt-4 font-semibold">{t('discover.explore.picksCta', 'See all curated picks')} →</span>
        </Link>
        <Link
          to="/catalog"
          className="flex flex-col min-h-[9rem] rounded-xl bg-lsc-dark text-white p-6 hover:-translate-y-0.5 motion-reduce:transform-none transition-transform focus-ring"
        >
          <span className="font-serif text-xl font-bold">{t('discover.explore.catalogTitle', 'Browse the full catalog')}</span>
          <span className="text-sm text-white mt-1 max-w-[34ch]">
            {t('discover.explore.catalogBody', 'Everything the library holds, with filters for format, language, reading level, and more.')}
          </span>
          <span className="mt-auto pt-4 font-semibold">{t('discover.explore.catalogCta', 'Open the catalog')} →</span>
        </Link>
      </div>
    </section>
  )
}

export default function DiscoverPage(): React.ReactElement {
  const { data: arrivals } = useQuery({
    queryKey: ['discover-new-arrivals'],
    queryFn: () => getNewArrivals({ limit: 12, days: 30 }),
    staleTime: 5 * 60 * 1000,
  })

  const arrivalItems = (arrivals?.items ?? []).map((i) => ({
    id: i.id,
    title: i.title,
    author: i.author,
    item_type: i.item_type,
    status: i.status,
    cover_url: i.cover_url,
    page_count: i.page_count,
  }))

  return (
    <div className="max-w-6xl mx-auto px-6 py-10 md:py-12 space-y-12">
      <header className="space-y-2">
        <h1 className="text-3xl md:text-4xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
          {t('discover.pageTitle', 'Discover')}
        </h1>
        <p className="text-earth-600 dark:text-cream-400 max-w-2xl">
          {t('discover.intro', 'Start here. See what just landed, follow a reader shelf, or head straight to the full catalog.')}
        </p>
      </header>

      {/* New Arrivals — CatalogShelf returns null when empty, so no dead band. */}
      <CatalogShelf title={t('discover.newArrivals', 'New Arrivals')} items={arrivalItems} />

      <ShelfDoorways />

      <KeepExploring />
    </div>
  )
}

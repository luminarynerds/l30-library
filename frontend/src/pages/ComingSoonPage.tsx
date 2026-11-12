/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useQuery } from '@tanstack/react-query'
import { usePageTitle } from '@/hooks/usePageTitle'
import { useTranslation } from '@/i18n/I18nContext'
import { getFeaturedUpcoming, type FeaturedUpcomingItem } from '@/api/releases-api'

function formatWhen(
  item: FeaturedUpcomingItem,
  t: (k: string, f?: string) => string,
  locale: string,
): string {
  if (!item.release_date) return t('comingSoon.tbd', 'Coming soon')
  const d = new Date(`${item.release_date}T00:00:00`)
  const month = d.toLocaleString(locale, { month: 'long' })
  return item.is_date_exact
    ? d.toLocaleDateString(locale, { month: 'long', day: 'numeric', year: 'numeric' })
    : `${t('comingSoon.coming', 'Coming')} ${month} ${d.getFullYear()}`
}

export default function ComingSoonPage(): React.ReactElement {
  const { t, language } = useTranslation()
  usePageTitle(t('comingSoon.pageTitle', 'Coming Soon'))
  const { data, isLoading, isError } = useQuery({
    queryKey: ['releases', 'featured-upcoming'],
    queryFn: getFeaturedUpcoming,
  })
  const items = data?.items ?? []

  return (
    <div className="max-w-6xl mx-auto px-6 py-12 md:py-16 space-y-10">
      <header className="space-y-3">
        <h1 className="font-serif text-4xl md:text-5xl text-lsc-dark dark:text-lsc-cream leading-tight">
          {t('comingSoon.heading', 'Coming Soon')}
        </h1>
        <p className="text-base md:text-lg text-earth-700 dark:text-earth-300 max-w-2xl">
          {t('comingSoon.intro', 'Forthcoming titles our librarians are excited about.')}
        </p>
      </header>

      <div role="status" aria-live="polite">
        {isLoading && <p className="text-earth-700 dark:text-earth-300">{t('comingSoon.loading', 'Loading…')}</p>}
        {isError && <p className="text-earth-700 dark:text-earth-300">{t('comingSoon.error', 'Could not load upcoming titles.')}</p>}
        {!isLoading && !isError && items.length === 0 && (
          <p className="text-earth-700 dark:text-earth-300">{t('comingSoon.empty', 'Nothing featured just yet — check back soon.')}</p>
        )}
      </div>

      <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {items.map((item) => (
          <li key={item.tracker_book_id} className="rounded-xl border border-earth-200 dark:border-earth-700 p-4 space-y-2">
            <h2 className="font-serif text-lg text-lsc-dark dark:text-lsc-cream">{item.title}</h2>
            {item.author_name && <div className="text-sm text-earth-700 dark:text-earth-300">{item.author_name}</div>}
            <div className="text-xs uppercase tracking-wide text-earth-700 dark:text-earth-300">{formatWhen(item, t, language)}</div>
            {item.library_status === 'owned' && (
              <div className="text-xs text-earth-700 dark:text-earth-300">
                {item.catalog_item_id != null ? (
                  <a href={`/catalog/${item.catalog_item_id}`} className="underline">
                    {t('comingSoon.inCatalog', 'In our catalog')}
                  </a>
                ) : (
                  t('comingSoon.inCatalog', 'In our catalog')
                )}
              </div>
            )}
            {item.library_status === 'on_order' && (
              <div className="text-xs text-earth-700 dark:text-earth-300">{t('comingSoon.onOrder', 'On order')}</div>
            )}
            {item.source === 'libraryreads' && (
              <div className="text-xs text-earth-700 dark:text-earth-300">
                <a href={item.source_url || 'https://libraryreads.org'} target="_blank" rel="noopener noreferrer" className="underline">
                  <span aria-hidden="true">★</span> {t('comingSoon.libraryReadsBadge', 'LibraryReads pick')}
                </a>
                {item.blurb_credit && <span> — {item.blurb_credit}</span>}
              </div>
            )}
          </li>
        ))}
      </ul>
    </div>
  )
}

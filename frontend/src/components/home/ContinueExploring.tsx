/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { ArrowRight, Clock3 } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useRecentSearches } from '@/hooks/useRecentSearches'
import { useTranslation } from '@/i18n/I18nContext'

export default function ContinueExploring(): React.ReactElement | null {
  const { t } = useTranslation()
  const { recentSearches } = useRecentSearches()
  const searches = recentSearches.slice(0, 3)

  if (searches.length === 0) return null

  return (
    <section aria-labelledby="continue-exploring-heading" className="max-w-6xl mx-auto px-6">
      <div className="border-y border-earth-200 dark:border-earth-700 py-6 md:flex md:items-center md:justify-between md:gap-8">
        <div>
          <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-earth-700 dark:text-earth-400">{t('home.continue.kicker', 'Make yourself at home')}</p>
          <h2 id="continue-exploring-heading" className="mt-1 font-serif text-2xl text-lsc-dark dark:text-lsc-cream">{t('home.continue.title', 'Continue exploring')}</h2>
        </div>
        <ul className="mt-4 flex flex-wrap gap-2 md:mt-0" role="list">
          {searches.map((search) => (
            <li key={search.query}>
              <Link to={`/catalog?q=${encodeURIComponent(search.query)}`} className="inline-flex min-h-[44px] items-center gap-2 rounded-lg border border-earth-200 bg-lsc-white px-3 py-2 text-sm font-medium text-lsc-dark hover:border-sage-500 hover:bg-sage-50 dark:border-earth-700 dark:bg-earth-800 dark:text-lsc-cream dark:hover:bg-earth-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sage-500">
                <Clock3 className="h-4 w-4 text-sage-700 dark:text-lsc-rose" aria-hidden="true" />
                {search.query}
                <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
              </Link>
            </li>
          ))}
        </ul>
      </div>
    </section>
  )
}

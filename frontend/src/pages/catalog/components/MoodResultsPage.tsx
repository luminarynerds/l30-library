/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { searchCatalog, type CatalogItem } from '@/api/domains/catalog/catalog-api'
import { MoodIcon } from '@/pages/catalog/utils/catalogLandingConfig'
import { useMoodCategories } from '@/hooks/useMoodCategories'
import { getMoodTags } from '@/pages/catalog/utils/catalogItemUtils'
import { useUnifiedAccessibility } from '@/features/accessibility/hooks/useUnifiedAccessibility'
import CatalogGridCard from './CatalogGridCard'
import { useTranslation } from '@/i18n/I18nContext'
import CatalogListCard from './CatalogListCard'
import PageContainer from '@/components/layout/PageContainer'

export default function MoodResultsPage() {
  const { slug } = useParams<{ slug: string }>()
  const { data: moods, isLoading: moodsLoading } = useMoodCategories()
  const mood = moods?.find((m) => m.slug === slug) ?? null
  const { quietMode, simplifiedView, showImages } = useUnifiedAccessibility()
  const { t } = useTranslation()

  const [items, setItems] = useState<CatalogItem[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!mood) return

    let cancelled = false
    setIsLoading(true)
    setError(null)

    // Fire one search per keyword in parallel: backend FTS AND-joins multi-word
    // queries, so a single concatenated query matches nothing.
    Promise.all(
      mood.keywords.map((kw) =>
        searchCatalog({ query: kw, per_page: 50, sort_by: 'relevance' }).catch(
          () => ({ items: [] as CatalogItem[], total: 0, page: 1, per_page: 50, pages: 0 })
        )
      )
    )
      .then((results) => {
        if (cancelled) return
        const seen = new Set<number>()
        const merged: CatalogItem[] = []
        for (const r of results) {
          for (const item of r.items) {
            if (!seen.has(item.id)) {
              seen.add(item.id)
              merged.push(item)
            }
          }
        }
        // Client-side filter: keep items that have at least one matching mood tag
        const filtered = merged.filter((item) => {
          const tags = getMoodTags(item.id, item.subjects)
          return tags.some((tag) => mood.tags.includes(tag))
        })
        // Sort: popularity (total_checkouts desc) then recency (created_at desc)
        filtered.sort((a, b) => {
          const checkoutDiff = (b.total_checkouts ?? 0) - (a.total_checkouts ?? 0)
          if (checkoutDiff !== 0) return checkoutDiff
          return new Date(b.created_at ?? 0).getTime() - new Date(a.created_at ?? 0).getTime()
        })
        setItems(filtered)
      })
      .catch(() => {
        if (!cancelled) setError(t('mood.loadError'))
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false)
      })

    return () => { cancelled = true }
  }, [mood])

  if (moodsLoading && !mood) {
    return (
      <PageContainer className="py-12 text-center text-sm text-lsc-dark/60 dark:text-lsc-cream/60">
        Loading...
      </PageContainer>
    )
  }

  if (!mood) {
    return (
      <PageContainer className="py-12 text-center">
        <h1 className="text-xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">{t('mood.notFound')}</h1>
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60 mb-4">
          {t('mood.notFoundDescription')}
        </p>
        <Link to="/catalog" className="text-sm text-lsc-rose hover:underline">{t('mood.backToCatalog')}</Link>
      </PageContainer>
    )
  }

  return (
    <PageContainer className="py-6">
      {/* Header */}
      <div className="mb-6">
        <Link
          to="/catalog"
          className="inline-flex items-center gap-1 text-sm text-lsc-dark/70 dark:text-lsc-cream/60 hover:text-lsc-rose transition-colors mb-3"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to catalog
        </Link>
        {!quietMode && (
          <div className="flex items-center gap-3">
            <MoodIcon name={mood.icon} className="w-8 h-8 text-lsc-rose dark:text-lsc-rose-light" />
            <div>
              <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
                {mood.label}
              </h1>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60">
                {t('mood.itemCount', { count: items.length })}
              </p>
            </div>
          </div>
        )}
        {quietMode && (
          <h1 className="text-xl font-bold text-lsc-dark dark:text-lsc-cream">
            {t('mood.browseResults', { count: items.length })}
          </h1>
        )}
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="flex items-center justify-center py-16">
          <div className="w-8 h-8 border-2 border-lsc-rose border-t-transparent rounded-full motion-safe:animate-spin" />
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="text-center py-12" role="alert">
          <p className="text-sm text-status-danger-600 dark:text-status-danger-400 mb-3">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="text-sm text-lsc-rose hover:underline"
          >
            Try again
          </button>
        </div>
      )}

      {/* Results */}
      {!isLoading && !error && items.length === 0 && (
        <div className="text-center py-12">
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60">
            {t('mood.noItems')}
          </p>
        </div>
      )}

      {!isLoading && !error && items.length > 0 && (
        <>
          {quietMode ? (
            <div className="divide-y divide-lsc-border dark:divide-earth-700 border border-lsc-border dark:border-earth-700 rounded-xl overflow-hidden">
              {items.map((item) => (
                <CatalogListCard
                  key={item.id}
                  item={item}
                  simplifiedView={simplifiedView}
                  quietMode={quietMode}
                  showImages={showImages}
                  isSpeaking={false}
                  onSpeak={() => {}}
                  onStopSpeak={() => {}}
                />
              ))}
            </div>
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-[18px]" role="list">
              {items.map((item) => (
                <div key={item.id} role="listitem">
                  <CatalogGridCard item={item} />
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {/* Other moods */}
      {!quietMode && (
        <div className="mt-12 pt-8 border-t border-lsc-border dark:border-earth-700">
          <h2 className="text-base font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-3">
            Try another mood
          </h2>
          <div className="flex flex-wrap gap-2">
            {(moods ?? []).filter((m) => m.slug !== slug).map((m) => (
              <Link
                key={m.slug}
                to={`/catalog/mood/${m.slug}`}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-full border border-lsc-border dark:border-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 hover:border-lsc-rose/50 hover:text-lsc-rose transition-colors"
              >
                <MoodIcon name={m.icon} className="w-4 h-4" />
                {m.label}
              </Link>
            ))}
          </div>
        </div>
      )}
    </PageContainer>
  )
}

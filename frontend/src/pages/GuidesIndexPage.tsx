/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Printer,
  Mail,
  Wifi,
  KeyRound,
  Smartphone,
  CreditCard,
  ShieldAlert,
  FileCheck,
  BookOpen,
  BookMarked,
  ArrowRight,
  Search,
  Clock,
  X,
  type LucideIcon,
} from 'lucide-react'
import StandardPageLayout from '@/components/StandardPageLayout'
import { useTranslation } from '@/i18n'
import { useSchemaOrg } from '@/components/linked-data/SchemaOrgHead'
import {
  GUIDES,
  GUIDE_CATEGORIES,
  CATEGORY_TILE_CLASSES,
  type GuideMeta,
  type GuideIconName,
  type GuideCategoryId,
} from './guides/_data'

const ICON_MAP: Record<GuideIconName, LucideIcon> = {
  CreditCard,
  BookMarked,
  Printer,
  FileCheck,
  Mail,
  Smartphone,
  Wifi,
  KeyRound,
  ShieldAlert,
}

// Exponential ease-out from CLAUDE.md design mandate.
const EASE_OUT_EXPO = '[transition-timing-function:cubic-bezier(0.16,1,0.3,1)]'

function GuideCard({ guide }: { guide: GuideMeta }): React.ReactElement {
  const { t } = useTranslation()
  const Icon = ICON_MAP[guide.iconName]
  const title = t(guide.titleKey)
  const description = t(guide.descriptionKey)
  const minutesLabel = t('guidesIndex.estimatedMinutes', { minutes: guide.estimatedMinutes })
  const minutesAria = t('guidesIndex.estimatedMinutesLabel', { minutes: guide.estimatedMinutes })
  const ariaLabel = t('guidesIndex.openGuideAriaLabel', { title })

  return (
    <Link
      to={guide.href}
      aria-label={ariaLabel}
      data-guide-id={guide.id}
      className={`group block bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl p-5 hover:border-lsc-rose dark:hover:border-lsc-rose hover:shadow-soft-lg motion-safe:hover:scale-[1.02] motion-safe:transition-[transform,box-shadow,border-color] duration-300 ${EASE_OUT_EXPO} focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2 focus-visible:ring-offset-lsc-cream dark:focus-visible:ring-offset-lsc-dark`}
    >
      <div className="flex items-start gap-4">
        <div
          aria-hidden="true"
          className={`flex-shrink-0 w-11 h-11 rounded-lg flex items-center justify-center ${CATEGORY_TILE_CLASSES[guide.category]}`}
        >
          <Icon className="w-6 h-6" />
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream group-hover:text-lsc-rose motion-safe:transition-colors">
            {title}
          </h3>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">{description}</p>
          <p className="mt-2 inline-flex items-center gap-1 text-xs text-lsc-dark/60 dark:text-lsc-cream/60">
            <Clock aria-hidden="true" className="w-3.5 h-3.5" />
            <span aria-label={minutesAria}>{minutesLabel}</span>
          </p>
        </div>
        <ArrowRight
          aria-hidden="true"
          className={`w-4 h-4 text-lsc-dark/30 dark:text-lsc-cream/60 group-hover:text-lsc-rose motion-safe:group-hover:translate-x-0.5 motion-safe:transition-transform flex-shrink-0 mt-1 ${EASE_OUT_EXPO}`}
        />
      </div>
    </Link>
  )
}

export default function GuidesIndexPage(): React.ReactElement {
  const { t } = useTranslation()
  const [query, setQuery] = useState('')
  const [activeCategory, setActiveCategory] = useState<GuideCategoryId | 'all'>('all')

  const normalizedQuery = query.trim().toLowerCase()

  const visibleGuides = useMemo<GuideMeta[]>(() => {
    return GUIDES.filter((guide) => {
      if (activeCategory !== 'all' && guide.category !== activeCategory) return false
      if (!normalizedQuery) return true
      const title = t(guide.titleKey).toLowerCase()
      const description = t(guide.descriptionKey).toLowerCase()
      return title.includes(normalizedQuery) || description.includes(normalizedQuery)
    })
  }, [activeCategory, normalizedQuery, t])

  // Group visible guides by their category, preserving GUIDE_CATEGORIES order.
  const grouped = useMemo(() => {
    const byCategory = new Map<GuideCategoryId, GuideMeta[]>()
    for (const cat of GUIDE_CATEGORIES) {
      byCategory.set(cat.id, [])
    }
    for (const guide of visibleGuides) {
      byCategory.get(guide.category)?.push(guide)
    }
    return GUIDE_CATEGORIES
      .map((cat) => ({ category: cat, guides: byCategory.get(cat.id) ?? [] }))
      .filter((group) => group.guides.length > 0)
  }, [visibleGuides])

  // Schema.org ItemList for SEO — exposes all 9 guides (not the filtered subset)
  // so search engines see the full collection regardless of UI state.
  const itemListSchema = useMemo(
    () => ({
      '@context': 'https://schema.org',
      '@type': 'ItemList',
      '@id': 'https://l30.org/guides',
      name: t('guidesIndex.pageTitle'),
      description: t('guidesIndex.pageSubtitle'),
      numberOfItems: GUIDES.length,
      itemListElement: GUIDES.map((guide, index) => ({
        '@type': 'ListItem',
        position: index + 1,
        url: `https://l30.org${guide.href}`,
        name: t(guide.titleKey),
      })),
    }),
    [t]
  )
  useSchemaOrg(itemListSchema, 'guides-index')

  const hasResults = visibleGuides.length > 0
  const isFiltered = normalizedQuery.length > 0 || activeCategory !== 'all'

  return (
    <StandardPageLayout title={t('guidesIndex.pageTitle')} subtitle={t('guidesIndex.pageSubtitle')}>
      <div className="max-w-5xl mx-auto">
        <div className="bg-lsc-cream dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl p-5 mb-6 flex items-start gap-4 print:hidden">
          <BookOpen aria-hidden="true" className="w-6 h-6 text-lsc-rose flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-lsc-dark dark:text-lsc-cream font-medium">
              {t('guidesIndex.noTechExperienceNeeded')}
            </p>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
              {t('guidesIndex.noTechExperienceDescription')}
            </p>
          </div>
        </div>

        {/* Search + category filter */}
        <div className="mb-8 print:hidden">
          <label htmlFor="guides-search" className="sr-only">
            {t('guidesIndex.searchAriaLabel')}
          </label>
          <div className="relative">
            <Search
              aria-hidden="true"
              className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-lsc-dark/50 dark:text-lsc-cream/50"
            />
            <input
              id="guides-search"
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={t('guidesIndex.searchPlaceholder')}
              aria-label={t('guidesIndex.searchAriaLabel')}
              className="w-full pl-9 pr-9 py-2.5 rounded-lg bg-lsc-white dark:bg-earth-900 border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream placeholder:text-lsc-dark/50 dark:placeholder:text-lsc-cream/50 focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
            />
            {query && (
              <button
                type="button"
                onClick={() => setQuery('')}
                aria-label={t('guidesIndex.noResultsClear')}
                className="absolute right-2 top-1/2 -translate-y-1/2 p-1 rounded text-lsc-dark/60 dark:text-lsc-cream/60 hover:text-lsc-rose focus:outline-none focus:ring-2 focus:ring-lsc-rose"
              >
                <X aria-hidden="true" className="w-4 h-4" />
              </button>
            )}
          </div>

          <div
            role="group"
            aria-label={t('guidesIndex.filterAriaLabel')}
            className="mt-3 flex flex-wrap gap-2"
          >
            <FilterChip
              isActive={activeCategory === 'all'}
              onClick={() => setActiveCategory('all')}
              label={t('guidesIndex.filterAll')}
            />
            {GUIDE_CATEGORIES.map((cat) => (
              <FilterChip
                key={cat.id}
                isActive={activeCategory === cat.id}
                onClick={() => setActiveCategory(cat.id)}
                label={t(cat.labelKey)}
              />
            ))}
          </div>
        </div>

        {hasResults ? (
          <div className="space-y-10">
            {grouped.map(({ category, guides }) => (
              <section key={category.id} aria-labelledby={`guides-section-${category.id}`}>
                <h2
                  id={`guides-section-${category.id}`}
                  className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4"
                >
                  {t(category.labelKey)}
                </h2>
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                  {guides.map((guide) => (
                    <GuideCard key={guide.id} guide={guide} />
                  ))}
                </div>
              </section>
            ))}
          </div>
        ) : (
          <div
            role="status"
            className="text-center py-12 px-4 rounded-xl bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700"
          >
            <Search aria-hidden="true" className="w-12 h-12 mx-auto text-lsc-dark/40 dark:text-lsc-cream/40 opacity-50" />
            <h3 className="mt-3 font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
              {t('guidesIndex.noResultsTitle')}
            </h3>
            <p className="mt-1 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
              {t('guidesIndex.noResultsBody')}
            </p>
            {isFiltered && (
              <button
                type="button"
                onClick={() => {
                  setQuery('')
                  setActiveCategory('all')
                }}
                className="mt-4 inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-lsc-rose text-white hover:bg-lsc-rose/90 motion-safe:transition-colors focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-2 focus:ring-offset-lsc-cream dark:focus:ring-offset-lsc-dark"
              >
                <X aria-hidden="true" className="w-4 h-4" />
                {t('guidesIndex.noResultsClear')}
              </button>
            )}
          </div>
        )}

        <div className="mt-10 text-center print:hidden">
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60">
            {t('guidesIndex.footerNeedHelp')}{' '}
            <Link to="/tech" className="text-lsc-rose hover:underline font-medium">
              {t('guidesIndex.footerVisitTechSupport')}
            </Link>{' '}
            {t('guidesIndex.footerOrAskDesk')}
          </p>
        </div>
      </div>

      {/* Print stylesheet — hide search/filters, expand grids, drop background fills. */}
      <style>{`
        @media print {
          [data-guide-id] {
            break-inside: avoid;
            page-break-inside: avoid;
            border-color: #000 !important;
          }
        }
      `}</style>
    </StandardPageLayout>
  )
}

interface FilterChipProps {
  isActive: boolean
  onClick: () => void
  label: string
}

function FilterChip({ isActive, onClick, label }: FilterChipProps): React.ReactElement {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={isActive}
      className={`px-3 py-1.5 rounded-full text-sm font-medium border motion-safe:transition-colors focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-2 focus:ring-offset-lsc-cream dark:focus:ring-offset-lsc-dark ${
        isActive
          ? 'bg-lsc-rose text-white border-lsc-rose'
          : 'bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream border-lsc-border dark:border-earth-700 hover:border-lsc-rose'
      }`}
    >
      {label}
    </button>
  )
}

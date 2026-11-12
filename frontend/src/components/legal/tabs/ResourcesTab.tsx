/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Link } from 'react-router-dom'
import {
  ArrowRight,
  Briefcase,
  FileText,
  Heart,
  Home,
  Landmark,
  Loader2,
  Scale,
  Search,
  Users,
} from 'lucide-react'
import type { LegalGuideSummary, LegalTopic } from '@/api/legal-api'
import { useTranslation } from '@/i18n'
import ExpandableGuideCard from '../ExpandableGuideCard'

interface ResourcesTabProps {
  topics: LegalTopic[]
  topicsLoading: boolean
  guides: LegalGuideSummary[]
  guidesLoading: boolean
  searchQuery: string
  onSearchChange: (value: string) => void
  activeCategory: number | null
  onActiveCategoryChange: (id: number | null) => void
  guidesLimit: number
  onShowMore: () => void
}

const getCategoryIcon = (slug: string): React.ReactNode => {
  const icons: Record<string, React.ReactNode> = {
    family: <Heart aria-hidden="true" className="w-4 h-4" />,
    housing: <Home aria-hidden="true" className="w-4 h-4" />,
    employment: <Briefcase aria-hidden="true" className="w-4 h-4" />,
    consumer: <Users aria-hidden="true" className="w-4 h-4" />,
    immigration: <FileText aria-hidden="true" className="w-4 h-4" />,
  }
  return icons[slug] || <Scale aria-hidden="true" className="w-4 h-4" />
}

export default function ResourcesTab({
  topics,
  topicsLoading,
  guides,
  guidesLoading,
  searchQuery,
  onSearchChange,
  activeCategory,
  onActiveCategoryChange,
  guidesLimit,
  onShowMore,
}: ResourcesTabProps): React.ReactElement {
  const { t } = useTranslation()

  const filteredGuides = guides.filter(
    (guide) =>
      !searchQuery ||
      guide.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      guide.summary?.toLowerCase().includes(searchQuery.toLowerCase()),
  )

  return (
    <div>
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700 mb-6">
        <div className="flex gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
            <input
              type="text"
              placeholder={t('legalResources.searchLegalGuidesAndResources')}
              aria-label={t('aria.legalResources.searchLegalResources')}
              value={searchQuery}
              onChange={(e) => onSearchChange(e.target.value)}
              className="w-full pl-10 pr-4 py-3 text-base border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-earth-50 placeholder-earth-500 dark:placeholder-earth-500 focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
            />
          </div>
        </div>
      </div>

      {topicsLoading ? (
        <div className="flex items-center justify-center py-4">
          <Loader2 className="w-5 h-5 motion-safe:animate-spin text-lsc-rose" />
        </div>
      ) : topics.length > 0 && (
        <div role="group" aria-label={t('aria.legalResources.filterByTopic')} className="flex gap-2 sm:gap-3 mb-8 overflow-x-auto pb-1 scrollbar-thin scrollbar-track-transparent scrollbar-thumb-lsc-border sm:flex-wrap">
          <button
            onClick={() => onActiveCategoryChange(null)}
            aria-pressed={activeCategory === null}
            className={`flex items-center gap-1 sm:gap-2 px-3 sm:px-4 py-2 min-h-[44px] rounded-full border transition-colors text-xs sm:text-sm ${
              activeCategory === null
                ? 'bg-lsc-rose text-white border-earth-600'
                : 'bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream/80 border-lsc-border dark:border-earth-700 hover:border-earth-400'
            }`}
          >
            <Scale aria-hidden="true" className="w-4 h-4" />
            <span className="font-medium">{t('components.legal.resourcesTab.allTopics', 'All Topics')}</span>
          </button>
          {topics.map((topic) => (
            <button
              key={topic.id}
              onClick={() => onActiveCategoryChange(activeCategory === topic.id ? null : topic.id)}
              aria-pressed={activeCategory === topic.id}
              className={`flex items-center gap-1 sm:gap-2 px-3 sm:px-4 py-2 min-h-[44px] rounded-full border transition-colors text-xs sm:text-sm ${
                activeCategory === topic.id
                  ? 'bg-lsc-rose text-white border-earth-600'
                  : 'bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream/80 border-lsc-border dark:border-earth-700 hover:border-earth-400'
              }`}
            >
              {getCategoryIcon(topic.slug)}
              <span className="font-medium">{topic.name}</span>
            </button>
          ))}
        </div>
      )}

      <Link
        to="/legal/bankruptcy"
        className="block bg-lsc-white dark:bg-earth-800 rounded-xl p-5 border border-lsc-border dark:border-earth-700 hover:border-lsc-rose/40 dark:hover:border-lsc-rose/30 transition-colors mb-6"
      >
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-2">
              <Landmark aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
              <h3 className="font-medium text-lsc-dark dark:text-earth-50">{t('components.legal.resourcesTab.bankruptcyFilingSearch', 'Bankruptcy Filing Search')}</h3>
            </div>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">
              {t(
                'components.legal.resourcesTab.searchRecentFederalBankruptcy',
                'Search recent federal bankruptcy filings from all U.S. courts. Free access via CourtListener.',
              )}
            </p>
            <span className="inline-flex items-center gap-1 text-sm text-lsc-rose dark:text-lsc-rose-light font-medium">
              {t('components.legal.resourcesTab.searchFilings', 'Search Filings')}
              <ArrowRight aria-hidden="true" className="w-4 h-4" />
            </span>
          </div>
        </div>
      </Link>

      {guidesLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
        </div>
      ) : filteredGuides.length > 0 ? (
        <>
          <div className="grid gap-6">
            {filteredGuides.slice(0, guidesLimit).map((guide) => (
              <ExpandableGuideCard
                key={guide.id}
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                guide={guide as any}
              />
            ))}
          </div>
          {filteredGuides.length > guidesLimit && (
            <button
              onClick={onShowMore}
              className="mt-6 w-full py-3 text-sm font-medium text-lsc-rose dark:text-lsc-rose-light bg-lsc-cream/50 dark:bg-earth-800/50 hover:bg-lsc-cream dark:hover:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl transition-colors"
            >
              {t('components.legal.resourcesTab.showMoreRemaining', { count: filteredGuides.length - guidesLimit })}
            </button>
          )}
        </>
      ) : (
        <div className="text-center py-16">
          <Scale aria-hidden="true" className="w-16 h-16 mx-auto text-lsc-border dark:text-lsc-cream/70 mb-4" />
          <h3 className="text-lg font-medium text-lsc-dark dark:text-earth-50 mb-2">{t('components.legal.resourcesTab.noLegalGuidesFound', 'No legal guides found')}</h3>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
            {searchQuery || activeCategory
              ? t('components.legal.resourcesTab.tryAdjustingYourSearch2', 'Try adjusting your search or filters.')
              : t('components.legal.resourcesTab.legalGuidesWillAppear', 'Legal guides will appear here once they are added to the system.')}
          </p>
        </div>
      )}
    </div>
  )
}

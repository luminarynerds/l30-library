/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Link } from 'react-router-dom'
import { Bookmark, ListChecks } from 'lucide-react'
import { type CatalogDisplayItem } from '@/pages/catalog/hooks/useCatalogSearch'
import { useTranslation } from '@/i18n/I18nContext'
import { ExploreIcon, EXPLORE_CARDS } from '@/pages/catalog/utils/catalogLandingConfig'
import CatalogFormatChips from './CatalogFormatChips'
import MoodBrowseRow from './MoodBrowseRow'
import NewArrivalsRow from './NewArrivalsRow'
import RecentlyViewedRow from './RecentlyViewedRow'
import StaffPicksSection from './StaffPicksSection'
import CatalogListCard from '@/pages/catalog/components/CatalogListCard'
import CatalogGridCard from '@/pages/catalog/components/CatalogGridCard'
import { YourListsSection } from '@/components/reading-lists/YourListsSection'

interface CatalogLandingPanelProps {
  filteredItems: CatalogDisplayItem[]
  activeFormat: string | null
  onBrowseFormat: (format: string) => void
  effectiveQuietMode: boolean
  effectiveSimplifiedView: boolean
  effectiveShowImages: boolean
  speakingItemId: number | null
  onSpeak: (text: string, itemId: number) => void
  onStopSpeak: () => void
  viewMode: 'list' | 'grid'
  readingLists: Array<{ id: number; name: string; description?: string; item_count?: number; creator?: { name: string } }> | undefined
  hasData: boolean
}

export default function CatalogLandingPanel({
  filteredItems,
  activeFormat,
  onBrowseFormat,
  effectiveQuietMode,
  effectiveSimplifiedView,
  effectiveShowImages,
  speakingItemId,
  onSpeak,
  onStopSpeak,
  viewMode,
  readingLists,
  hasData,
}: CatalogLandingPanelProps) {
  const { t } = useTranslation()

  const renderListItems = () => {
    if (effectiveQuietMode) {
      return (
        <div className="divide-y divide-lsc-border dark:divide-earth-700 border border-lsc-border dark:border-earth-700 rounded-xl overflow-hidden">
          {filteredItems.map((item: CatalogDisplayItem) => (
            <CatalogListCard
              key={`${item.source}-${item.id}`}
              item={item}
              {...(item.source ? { source: item.source } : {})}
              simplifiedView={effectiveSimplifiedView}
              quietMode={effectiveQuietMode}
              showImages={effectiveShowImages}
              isSpeaking={speakingItemId === item.id}
              onSpeak={(text) => onSpeak(text, item.id)}
              onStopSpeak={onStopSpeak}
            />
          ))}
        </div>
      )
    }

    return (
      <div className="flex flex-col gap-3" role="list">
        {filteredItems.map((item: CatalogDisplayItem) => (
          <div key={`${item.source}-${item.id}`} role="listitem">
            <CatalogListCard
              item={item}
              {...(item.source ? { source: item.source } : {})}
              simplifiedView={effectiveSimplifiedView}
              quietMode={effectiveQuietMode}
              showImages={effectiveShowImages}
              isSpeaking={speakingItemId === item.id}
              onSpeak={(text) => onSpeak(text, item.id)}
              onStopSpeak={onStopSpeak}
            />
          </div>
        ))}
      </div>
    )
  }

  const renderGridItems = () => (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-[18px]" role="list">
      {filteredItems.map((item: CatalogDisplayItem) => (
        <div key={`${item.source}-${item.id}`} role="listitem">
          <CatalogGridCard item={item} {...(item.source ? { source: item.source } : {})} />
        </div>
      ))}
    </div>
  )

  return (
    <div>
      <div className="lg:hidden">
      <CatalogFormatChips
        activeFormat={activeFormat}
        onSelect={(format) => onBrowseFormat(format)}
      />
      </div>
      {hasData && filteredItems.length > 0 && (
        <div className="mt-8 pt-6 border-t border-lsc-border dark:border-earth-700">
          <h2 className="text-lg font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-4">
            {t('catalog.landing.everythingAvailable')}
          </h2>
          {viewMode === 'list' ? renderListItems() : renderGridItems()}
        </div>
      )}
      {!effectiveQuietMode && <details className="mt-8 border-t border-lsc-border dark:border-earth-700 pt-4">
        <summary className="cursor-pointer min-h-[44px] py-3 rounded text-base font-semibold text-sage-700 dark:text-lsc-rose focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sage-500">
          {t('libraryExperience.browseCollections', 'Browse reading collections')}
        </summary>
        <div className="pt-4">
      {!effectiveQuietMode && (
        <RecentlyViewedRow showImages={effectiveShowImages} />
      )}
      <MoodBrowseRow quietMode={effectiveQuietMode} />
      {!effectiveQuietMode && (
        <NewArrivalsRow showImages={effectiveShowImages} />
      )}
      {!effectiveQuietMode && (
        <StaffPicksSection showImages={effectiveShowImages} />
      )}

      {!effectiveQuietMode && (
        <div className="mt-8 mb-8">
          <h2 className="text-lg font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-4">{t('catalog.landing.moreToExplore')}</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {EXPLORE_CARDS.map(card => (
              <Link
                key={card.link}
                to={card.link}
                className="flex items-start gap-3 p-4 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 hover:border-lsc-rose/50 hover:shadow-sm transition-[border-color,box-shadow] duration-150 ease-[cubic-bezier(0.23,1,0.32,1)] focus:outline-none focus:ring-2 focus:ring-lsc-rose"
              >
                <ExploreIcon name={card.icon} />
                <div>
                  <h3 className="text-sm font-bold text-lsc-dark dark:text-lsc-cream">{t(card.titleKey)}</h3>
                  <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 mt-0.5">{t(card.descKey)}</p>
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}
      {!effectiveQuietMode && <YourListsSection />}

      {/* Curated reading lists */}
      {readingLists && readingLists.length > 0 && !effectiveQuietMode && (
        <div className="mt-8 mb-8">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-serif font-bold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
              <ListChecks className="w-5 h-5 text-lsc-rose" aria-hidden="true" />
              {t('catalog.landing.curatedLists') || 'Curated Lists'}
            </h2>
            <Link
              to="/public-reading-lists"
              className="text-xs font-medium text-lsc-rose hover:underline"
            >
              {t('catalog.landing.viewAllLists') || 'View all lists'}
            </Link>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {readingLists.map((list) => (
              <Link
                key={list.id}
                to={`/public-reading-lists/${list.id}`}
                className="flex items-start gap-3 p-4 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 hover:border-lsc-rose/50 hover:shadow-sm transition-[border-color,box-shadow] duration-150 ease-[cubic-bezier(0.23,1,0.32,1)] focus:outline-none focus:ring-2 focus:ring-lsc-rose"
              >
                <Bookmark className="w-5 h-5 text-lsc-rose flex-shrink-0 mt-0.5" aria-hidden="true" />
                <div className="min-w-0">
                  <h3 className="text-sm font-bold text-lsc-dark dark:text-lsc-cream truncate" title={list.name}>{list.name}</h3>
                  {list.description && (
                    <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 mt-0.5 line-clamp-2" title={list.description}>{list.description}</p>
                  )}
                  <p className="text-xs text-earth-600 dark:text-earth-400 mt-1">
                    {list.item_count || 0} {t('catalog.landing.items') || 'items'}
                    {list.creator?.name && ` \u00b7 ${list.creator.name}`}
                  </p>
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}


        </div>
      </details>}
    </div>
  )
}

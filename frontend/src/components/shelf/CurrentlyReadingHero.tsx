/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Link } from 'react-router-dom'
import { BookOpen } from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import { useReadingStatus } from '@/hooks/useReadingStatus'
import { useReadingProgress } from '@/hooks/useReadingProgress'
import { setReadingStatus } from '@/api/domains/content/reading-status-api'
import { useQueryClient } from '@tanstack/react-query'
import ProgressBar from './ProgressBar'
import TagInput from './TagInput'
import type { ReadingStatusRecord } from '@/api/domains/content/reading-status-api'
import { CatalogCover } from '@/pages/catalog/components/CatalogItemThumbnail'
import { t } from '@/i18n'

interface CurrentlyReadingHeroProps {
  activeFilters?: string[]
  allTags?: string[]
}

export default function CurrentlyReadingHero({ activeFilters = [], allTags = [] }: CurrentlyReadingHeroProps) {
  const { token } = useAuth()
  const { allStatuses } = useReadingStatus()
  const { progressMap, handleLogProgress } = useReadingProgress()
  const queryClient = useQueryClient()

  let currentlyReading = allStatuses.filter(
    (s: ReadingStatusRecord) => s.status === 'currently_reading',
  )

  // Apply tag filters
  if (activeFilters.length > 0) {
    currentlyReading = currentlyReading.filter((s: ReadingStatusRecord) =>
      activeFilters.some((tag) => s.personal_tags?.includes(tag)),
    )
  }

  if (currentlyReading.length === 0) {
    return (
      <section aria-label={t('aria.shelf.currentlyReading')} className="mb-8">
        <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-3">
          Currently Reading
        </h2>
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border/60 dark:border-earth-700/80 p-8 text-center">
          <BookOpen className="w-10 h-10 mx-auto mb-3 text-lsc-dark/30 dark:text-lsc-cream/60" aria-hidden="true" />
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">
            Nothing on the go right now. Pick something from your shelf or browse the catalog!
          </p>
          <div className="flex justify-center gap-3">
            <Link
              to="/catalog"
              className="text-sm font-medium text-lsc-rose dark:text-lsc-rose-light hover:underline"
            >
              Browse Catalog
            </Link>
          </div>
        </div>
      </section>
    )
  }

  const handleTagsChange = async (entry: ReadingStatusRecord, newTags: string[]) => {
    if (!token) return
    await setReadingStatus(token, entry.catalog_item_id, entry.status, entry.private_notes, newTags)
    queryClient.invalidateQueries({ queryKey: ['reading-statuses'] })
    queryClient.invalidateQueries({ queryKey: ['patron-tags'] })
  }

  const handlePageSubmit = (catalogItemId: number, totalPages: number | null) => (page: number) => {
    handleLogProgress(catalogItemId, {
      current_page: page,
      total_pages: totalPages,
    })
  }

  return (
    <section aria-label={t('aria.shelf.currentlyReading')} className="mb-8">
      <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-3">
        Currently Reading
      </h2>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {currentlyReading.map((entry: ReadingStatusRecord) => {
          const item = entry.catalog_item
          const progress = progressMap.get(entry.catalog_item_id)
          const percent = progress?.percent ?? 0
          const currentPage = progress?.current_page ?? null
          const totalPages = progress?.total_pages ?? item.page_count ?? null

          return (
            <div
              key={entry.id}
              className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border/60 dark:border-earth-700/80 p-4 flex gap-3"
            >
              {/* Cover */}
              <Link to={`/catalog/${item.id}`} className="shrink-0">
                {item.cover_url ? (
                  <div className="w-14 h-20 rounded-lg overflow-hidden">
                    <CatalogCover
                      coverUrl={item.cover_url}
                      alt={`Cover of ${item.title}`}
                      title={item.title}
                      itemType={item.item_type}
                      size="sm"
                    />
                  </div>
                ) : (
                  <div className="w-14 h-20 bg-earth-100 dark:bg-earth-700 rounded-lg flex items-center justify-center">
                    <BookOpen className="w-5 h-5 text-lsc-dark/30 dark:text-lsc-cream/60" aria-hidden="true" />
                  </div>
                )}
              </Link>

              {/* Info */}
              <div className="flex-1 min-w-0">
                <Link
                  to={`/catalog/${item.id}`}
                  className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream hover:text-lsc-rose dark:hover:text-lsc-rose-light line-clamp-1"
                  title={item.title}
                >
                  {item.title}
                </Link>
                {item.author && (
                  <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 line-clamp-1" title={item.author}>
                    {item.author}
                  </p>
                )}

                {/* Progress bar */}
                <ProgressBar
                  percent={percent}
                  currentPage={currentPage}
                  totalPages={totalPages}
                  onPageSubmit={handlePageSubmit(entry.catalog_item_id, totalPages)}
                />

                {/* Inline tag editor */}
                <div className="mt-2">
                  <TagInput
                    tags={entry.personal_tags ?? []}
                    allTags={allTags}
                    onChange={(newTags) => handleTagsChange(entry, newTags)}
                  />
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </section>
  )
}

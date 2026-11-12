/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { X, BookOpen } from 'lucide-react'
import { useReadingStatus } from '@/hooks/useReadingStatus'
import { useReadingProgress } from '@/hooks/useReadingProgress'
import type { ReadingStatusRecord } from '@/api/domains/content/reading-status-api'
import { CatalogCover } from '@/pages/catalog/components/CatalogItemThumbnail'
import { t } from '@/i18n'
import FocusTrap from 'focus-trap-react'

interface QuickLogSheetProps {
  open: boolean
  onClose: () => void
}

const PERCENT_OPTIONS = [25, 50, 75, 100] as const

export default function QuickLogSheet({ open, onClose }: QuickLogSheetProps) {
  const { allStatuses } = useReadingStatus()
  const { progressMap, handleLogProgress, isLogging } = useReadingProgress()
  const [selectedItemId, setSelectedItemId] = useState<number | null>(null)
  const [pageInput, setPageInput] = useState('')
  const [noteInput, setNoteInput] = useState('')

  const currentlyReading = allStatuses.filter(
    (s: ReadingStatusRecord) => s.status === 'currently_reading',
  )

  if (!open) return null

  const selectedEntry = selectedItemId
    ? currentlyReading.find((s: ReadingStatusRecord) => s.catalog_item_id === selectedItemId)
    : null
  const latestProgress = selectedItemId ? progressMap.get(selectedItemId) : null
  const totalPages = latestProgress?.total_pages ?? selectedEntry?.catalog_item?.page_count ?? null

  const handleSubmitPage = async () => {
    if (!selectedItemId) return
    const page = parseInt(pageInput, 10)
    if (!page || page < 1) return
    await handleLogProgress(selectedItemId, {
      current_page: page,
      total_pages: totalPages,
      note: noteInput || null,
    })
    resetAndClose()
  }

  const handleSubmitPercent = async (pct: number) => {
    if (!selectedItemId) return
    await handleLogProgress(selectedItemId, {
      percent: pct,
      note: noteInput || null,
    })
    resetAndClose()
  }

  const resetAndClose = () => {
    setSelectedItemId(null)
    setPageInput('')
    setNoteInput('')
    onClose()
  }

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/40 z-50"
        onClick={resetAndClose}
        aria-hidden="true"
      />

      {/* Sheet */}
      <FocusTrap active={true} focusTrapOptions={{ escapeDeactivates: false, allowOutsideClick: true, returnFocusOnDeactivate: true, fallbackFocus: () => document.body }}>
      <div
        role="dialog"
        aria-label={t('aria.shelf.quickLogReadingProgress')}
        className="fixed bottom-0 left-0 right-0 z-50 bg-lsc-white dark:bg-earth-800 rounded-t-2xl shadow-lg max-h-[80vh] overflow-y-auto sm:max-w-md sm:mx-auto sm:bottom-8 sm:rounded-xl"
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-lsc-border/40 dark:border-earth-700/60">
          <h2 className="font-serif text-base font-semibold text-lsc-dark dark:text-lsc-cream">
            Log Reading
          </h2>
          <button
            onClick={resetAndClose}
            aria-label={t('aria.authModals.close')}
            className="text-lsc-dark/70 dark:text-lsc-cream/60 hover:text-lsc-dark dark:hover:text-lsc-cream"
          >
            <X className="w-5 h-5" aria-hidden="true" />
          </button>
        </div>

        <div className="p-4">
          {/* Book selector */}
          {!selectedItemId ? (
            <div>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">
                Which book are you reading?
              </p>
              <div className="grid grid-cols-4 gap-3">
                {currentlyReading.map((entry: ReadingStatusRecord) => {
                  const item = entry.catalog_item
                  return (
                    <button
                      key={entry.id}
                      onClick={() => setSelectedItemId(entry.catalog_item_id)}
                      className="flex flex-col items-center gap-1.5 p-2 rounded-xl hover:bg-earth-50 dark:hover:bg-earth-700 transition-colors"
                      aria-label={`Log progress for ${item.title}`}
                    >
                      {item.cover_url ? (
                        <div className="w-12 h-16 rounded-lg overflow-hidden">
                          <CatalogCover
                            coverUrl={item.cover_url}
                            alt={`Cover of ${item.title}`}
                            title={item.title}
                            itemType={item.item_type}
                            size="sm"
                          />
                        </div>
                      ) : (
                        <div className="w-12 h-16 bg-earth-100 dark:bg-earth-700 rounded-lg flex items-center justify-center">
                          <BookOpen className="w-4 h-4 text-lsc-dark/30 dark:text-lsc-cream/60" aria-hidden="true" />
                        </div>
                      )}
                      <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 line-clamp-2 text-center leading-tight" title={item.title}>
                        {item.title}
                      </span>
                    </button>
                  )
                })}
              </div>
            </div>
          ) : (
            <div>
              {/* Selected book info */}
              <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-3">
                {selectedEntry?.catalog_item?.title}
              </p>

              {/* Page input or percentage fallback */}
              {totalPages ? (
                <div>
                  <label htmlFor="quick-page" className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 mb-1 block">
                    What page are you on?
                  </label>
                  <input
                    id="quick-page"
                    type="number"
                    inputMode="numeric"
                    min={1}
                    max={totalPages}
                    value={pageInput}
                    onChange={(e) => setPageInput(e.target.value)}
                    placeholder={latestProgress?.current_page ? `After pg ${latestProgress.current_page}...` : 'Page #'}
                    autoFocus
                    className="w-full text-lg rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-lsc-rose/50"
                  />
                </div>
              ) : (
                <div>
                  <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 mb-2">
                    How far along are you?
                  </p>
                  <div className="grid grid-cols-4 gap-2">
                    {PERCENT_OPTIONS.map((pct) => (
                      <button
                        key={pct}
                        onClick={() => handleSubmitPercent(pct)}
                        disabled={isLogging}
                        className="py-2.5 rounded-xl text-sm font-medium border border-lsc-border dark:border-earth-600 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-rose hover:text-white hover:border-lsc-rose transition-colors disabled:opacity-50"
                      >
                        {pct === 100 ? 'Done' : `${pct}%`}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Note */}
              <div className="mt-3">
                <label htmlFor="quick-note" className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 mb-1 block">
                  Note (optional)
                </label>
                <input
                  id="quick-note"
                  type="text"
                  maxLength={280}
                  value={noteInput}
                  onChange={(e) => setNoteInput(e.target.value)}
                  placeholder={t('placeholder.shelf.whatStoodOut')}
                  className="w-full text-sm rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream px-3 py-2 focus:outline-none focus:ring-2 focus:ring-lsc-rose/50"
                />
              </div>

              {/* Submit (page-level) */}
              {totalPages && (
                <button
                  onClick={handleSubmitPage}
                  disabled={isLogging || !pageInput}
                  className="w-full mt-4 py-2.5 rounded-xl text-sm font-medium bg-lsc-rose text-white hover:bg-lsc-rose/90 disabled:opacity-50 transition-colors"
                >
                  {isLogging ? 'Saving...' : 'Log Progress'}
                </button>
              )}
            </div>
          )}
        </div>
      </div>
      </FocusTrap>
    </>
  )
}

/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useRef, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { BookOpen, Clock, Pause, CheckCircle, XCircle, ChevronDown, Trash2 } from 'lucide-react'
import { useReadingStatus } from '@/hooks/useReadingStatus'
import { setReadingStatus, removeReadingStatus, type ShelfStatus, type ReadingStatusRecord } from '@/api/domains/content/reading-status-api'
import { placeHold } from '@/api/domains/circulation/circulation-api'
import { useAuth } from '@/contexts/AuthContext'
import { useQueryClient } from '@tanstack/react-query'
import { useUnifiedAccessibility } from '@/features/accessibility/hooks/useUnifiedAccessibility'
import { clsx } from '@/utils/helpers'
import toast from 'react-hot-toast'
import TagInput from './TagInput'
import WantToReadActions from './WantToReadActions'
import { CatalogCover } from '@/pages/catalog/components/CatalogItemThumbnail'
import { t } from '@/i18n'

// Shelf tabs WITHOUT "currently_reading" — that's in the Hero zone
const TABS: { key: ShelfStatus; label: string; icon: React.ElementType }[] = [
  { key: 'want_to_read', label: 'Want to Read', icon: Clock },
  { key: 'on_hold', label: 'On Hold', icon: Pause },
  { key: 'finished', label: 'Finished', icon: CheckCircle },
  { key: 'did_not_finish', label: 'Did Not Finish', icon: XCircle },
]

// All shelf statuses for status dropdown (includes currently_reading)
const ALL_STATUSES: { key: ShelfStatus; label: string }[] = [
  { key: 'currently_reading', label: 'Currently Reading' },
  { key: 'want_to_read', label: 'Want to Read' },
  { key: 'on_hold', label: 'On Hold' },
  { key: 'finished', label: 'Finished' },
  { key: 'did_not_finish', label: 'Did Not Finish' },
]

interface ShelfTabsProps {
  activeFilters?: string[]
  allTags?: string[]
}

export default function ShelfTabs({ activeFilters = [], allTags = [] }: ShelfTabsProps) {
  const { token } = useAuth()
  const { allStatuses, stats, SHELF_LABELS } = useReadingStatus()
  const { announceToScreenReader } = useUnifiedAccessibility()
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState(0)
  const [expandedNotes, setExpandedNotes] = useState<Set<number>>(new Set())
  const [editingNotes, setEditingNotes] = useState<Record<number, string>>({})
  const [savingNotes, setSavingNotes] = useState<Set<number>>(new Set())
  const [openDropdown, setOpenDropdown] = useState<number | null>(null)
  const tabRefs = useRef<(HTMLButtonElement | null)[]>([])

  const handleTabKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLButtonElement>, idx: number) => {
      let nextIdx = idx
      if (e.key === 'ArrowRight') nextIdx = (idx + 1) % TABS.length
      else if (e.key === 'ArrowLeft') nextIdx = (idx - 1 + TABS.length) % TABS.length
      else if (e.key === 'Home') nextIdx = 0
      else if (e.key === 'End') nextIdx = TABS.length - 1
      else return
      e.preventDefault()
      setActiveTab(nextIdx)
      tabRefs.current[nextIdx]?.focus()
    },
    [],
  )

  const currentShelf = TABS[activeTab]!.key
  let filteredBooks = allStatuses.filter((s: ReadingStatusRecord) => s.status === currentShelf)

  // Apply tag filters
  if (activeFilters.length > 0) {
    filteredBooks = filteredBooks.filter((s: ReadingStatusRecord) =>
      activeFilters.some((tag) => s.personal_tags?.includes(tag)),
    )
  }

  const tabCount = (key: ShelfStatus) => stats?.[key] ?? 0

  const handleChangeStatus = async (catalogItemId: number, newStatus: ShelfStatus, currentTags?: string[]) => {
    if (!token) return
    setOpenDropdown(null)
    try {
      await setReadingStatus(token, catalogItemId, newStatus, undefined, currentTags)
      toast.success(t('toast.shelf.movedToShelflabelsnewstatus', { SHELFLABELSnewStatus: SHELF_LABELS[newStatus] }))
      announceToScreenReader(`Moved to ${SHELF_LABELS[newStatus]}`)
      queryClient.invalidateQueries({ queryKey: ['reading-statuses'] })
      queryClient.invalidateQueries({ queryKey: ['reading-stats'] })
      queryClient.invalidateQueries({ queryKey: ['reading-activity'] })
      queryClient.invalidateQueries({ queryKey: ['reading-milestones'] })
    } catch {
      toast.error(t('toast.shelf.failedToUpdateStatus'))
    }
  }

  const handleRemoveBook = async (catalogItemId: number) => {
    if (!token) return
    setOpenDropdown(null)
    try {
      await removeReadingStatus(token, catalogItemId)
      toast.success(t('toast.shelf.removedFromShelves'))
      announceToScreenReader('Removed from shelves')
      queryClient.invalidateQueries({ queryKey: ['reading-statuses'] })
      queryClient.invalidateQueries({ queryKey: ['reading-stats'] })
    } catch {
      toast.error(t('toast.shelf.failedToRemove'))
    }
  }

  const handleSaveNotes = async (catalogItemId: number, status: ShelfStatus, currentTags?: string[]) => {
    if (!token) return
    const notes = editingNotes[catalogItemId] ?? ''
    setSavingNotes((prev: Set<number>) => new Set(prev).add(catalogItemId))
    try {
      await setReadingStatus(token, catalogItemId, status, notes || null, currentTags)
      toast.success(t('toast.shelf.notesSaved'))
      announceToScreenReader('Private notes saved')
      queryClient.invalidateQueries({ queryKey: ['reading-statuses'] })
      setEditingNotes((prev: Record<number, string>) => {
        const next = { ...prev }
        delete next[catalogItemId]
        return next
      })
    } catch {
      toast.error(t('toast.shelf.failedToSaveNotes'))
    } finally {
      setSavingNotes((prev: Set<number>) => {
        const next = new Set(prev)
        next.delete(catalogItemId)
        return next
      })
    }
  }

  const toggleNotes = (id: number, currentNotes: string | null) => {
    setExpandedNotes((prev: Set<number>) => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
        setEditingNotes((p: Record<number, string>) => { const n = { ...p }; delete n[id]; return n })
      } else {
        next.add(id)
        setEditingNotes((p: Record<number, string>) => ({ ...p, [id]: currentNotes ?? '' }))
      }
      return next
    })
  }

  const handlePlaceHold = async (itemId: number) => {
    if (!token) return
    try {
      await placeHold(token, itemId)
      toast.success(t('toast.shelf.holdPlaced'))
      announceToScreenReader('Hold placed successfully')
    } catch {
      toast.error(t('toast.holdFailed'))
    }
  }

  const handleTagsChange = async (entry: ReadingStatusRecord, newTags: string[]) => {
    if (!token) return
    await setReadingStatus(token, entry.catalog_item_id, entry.status, entry.private_notes, newTags)
    queryClient.invalidateQueries({ queryKey: ['reading-statuses'] })
    queryClient.invalidateQueries({ queryKey: ['patron-tags'] })
  }

  return (
    <section aria-label={t('aria.shelf.bookShelves')}>
      {/* Tab bar */}
      <div
        role="tablist"
        aria-label={t('aria.shelf.readingShelves')}
        className="flex gap-1 border-b border-lsc-border dark:border-earth-700 mb-6 overflow-x-auto"
      >
        {TABS.map((tab, idx) => {
          const Icon = tab.icon
          return (
            <button
              key={tab.key}
              ref={(el) => { tabRefs.current[idx] = el }}
              role="tab"
              id={`shelf-tab-${idx}`}
              aria-selected={activeTab === idx}
              aria-controls={`shelf-panel-${idx}`}
              tabIndex={activeTab === idx ? 0 : -1}
              onClick={() => setActiveTab(idx)}
              onKeyDown={(e) => handleTabKeyDown(e, idx)}
              className={clsx(
                'flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium whitespace-nowrap border-b-2 transition-colors -mb-px',
                activeTab === idx
                  ? 'border-lsc-rose text-lsc-rose dark:text-lsc-rose-light'
                  : 'border-transparent text-lsc-dark/80 dark:text-lsc-cream/80 hover:text-lsc-dark dark:hover:text-lsc-cream hover:border-lsc-border dark:hover:border-earth-600',
              )}
            >
              <Icon className="w-4 h-4" aria-hidden="true" />
              <span className="hidden sm:inline">{tab.label}</span>
              <span className="sm:hidden" aria-label={tab.label}>{tab.label.split(' ')[0]}</span>
              <span className="ml-1 text-xs bg-earth-100 dark:bg-earth-700 px-1.5 py-0.5 rounded-full">
                {tabCount(tab.key)}
              </span>
            </button>
          )
        })}
      </div>

      {/* Tab panel */}
      <div
        role="tabpanel"
        id={`shelf-panel-${activeTab}`}
        aria-labelledby={`shelf-tab-${activeTab}`}
        className="min-h-[200px]"
      >
        {filteredBooks.length === 0 ? (
          <div className="text-center py-16">
            <BookOpen className="w-10 h-10 mx-auto mb-3 text-lsc-dark/30 dark:text-lsc-cream/60" aria-hidden="true" />
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">No books here yet. Browse the catalog to add some!</p>
            <Link to="/catalog" className="text-lsc-rose dark:text-lsc-rose-light font-medium hover:underline">
              Browse Catalog
            </Link>
          </div>
        ) : (
          <ul className="space-y-3" aria-label={`Books ${TABS[activeTab]?.label ?? ''}`}>
            {filteredBooks.map((entry) => {
              const item = entry.catalog_item
              const isExpanded = expandedNotes.has(entry.id)
              return (
                <li
                  key={entry.id}
                  className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border/60 dark:border-earth-700/80 p-4"
                >
                  <div className="flex gap-4">
                    {/* Cover */}
                    <Link to={`/catalog/${item.id}`} className="shrink-0">
                      {item.cover_url ? (
                        <div className="w-16 h-24 rounded-lg overflow-hidden">
                          <CatalogCover
                            coverUrl={item.cover_url}
                            alt={`Cover of ${item.title}`}
                            title={item.title}
                            itemType={item.item_type}
                            size="sm"
                          />
                        </div>
                      ) : (
                        <div className="w-16 h-24 bg-earth-100 dark:bg-earth-700 rounded-lg flex items-center justify-center">
                          <BookOpen className="w-6 h-6 text-lsc-dark/30 dark:text-lsc-cream/60" aria-hidden="true" />
                        </div>
                      )}
                    </Link>

                    {/* Details */}
                    <div className="flex-1 min-w-0">
                      <Link
                        to={`/catalog/${item.id}`}
                        className="text-base font-semibold text-lsc-dark dark:text-lsc-cream hover:text-lsc-rose dark:hover:text-lsc-rose-light line-clamp-1"
                        title={item.title}
                      >
                        {item.title}
                      </Link>
                      {item.author && (
                        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 line-clamp-1 mt-0.5" title={item.author}>{item.author}</p>
                      )}

                      {entry.private_notes && !isExpanded && (
                        <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 mt-1 line-clamp-1 italic" title={entry.private_notes}>{entry.private_notes}</p>
                      )}

                      {/* Inline tag editor */}
                      <div className="mt-1.5">
                        <TagInput
                          tags={entry.personal_tags ?? []}
                          allTags={allTags}
                          onChange={(newTags) => handleTagsChange(entry, newTags)}
                        />
                      </div>

                      {currentShelf === 'want_to_read' && (
                        <WantToReadActions item={item} onPlaceHold={handlePlaceHold} />
                      )}

                      {/* Actions row */}
                      <div className="flex flex-wrap items-center gap-2 mt-2">
                        {/* Status dropdown */}
                        <div className="relative">
                          <button
                            onClick={() => setOpenDropdown(openDropdown === entry.id ? null : entry.id)}
                            aria-haspopup="listbox"
                            aria-expanded={openDropdown === entry.id}
                            aria-label={`Change status for ${item.title}, currently ${SHELF_LABELS[entry.status]}`}
                            className="inline-flex items-center gap-1 text-xs font-medium px-2.5 py-1.5 rounded-lg border border-lsc-border dark:border-earth-600 text-lsc-dark/80 dark:text-lsc-cream/80 hover:bg-earth-50 dark:hover:bg-earth-700 transition-colors"
                          >
                            {SHELF_LABELS[entry.status]}
                            <ChevronDown className="w-3 h-3" aria-hidden="true" />
                          </button>
                          {openDropdown === entry.id && (
                            <ul
                              role="listbox"
                              aria-label={t('aria.shelf.moveToShelf')}
                              className="absolute left-0 top-full mt-1 z-20 bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl shadow-lg py-1 min-w-[180px]"
                            >
                              {ALL_STATUSES.filter((t) => t.key !== entry.status).map((t) => (
                                <li
                                  key={t.key}
                                  role="option"
                                  aria-selected={false}
                                  tabIndex={0}
                                  onClick={() => handleChangeStatus(entry.catalog_item_id, t.key, entry.personal_tags)}
                                  onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handleChangeStatus(entry.catalog_item_id, t.key, entry.personal_tags) } }}
                                  className="px-3 py-2 text-sm text-lsc-dark dark:text-lsc-cream hover:bg-earth-50 dark:hover:bg-earth-700 cursor-pointer"
                                >
                                  {t.label}
                                </li>
                              ))}
                            </ul>
                          )}
                        </div>

                        <button
                          onClick={() => toggleNotes(entry.id, entry.private_notes)}
                          aria-expanded={isExpanded}
                          aria-label={`${isExpanded ? 'Hide' : 'Show'} private notes for ${item.title}`}
                          className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 hover:text-lsc-rose dark:hover:text-lsc-rose-light transition-colors"
                        >
                          {isExpanded ? 'Hide notes' : 'Notes'}
                        </button>

                        <button
                          onClick={() => handleRemoveBook(entry.catalog_item_id)}
                          aria-label={`Remove ${item.title} from shelves`}
                          className="text-xs text-status-danger-500/70 hover:text-status-danger-600 dark:text-status-danger-400/70 dark:hover:text-status-danger-400 transition-colors ml-auto"
                        >
                          <Trash2 className="w-3.5 h-3.5" aria-hidden="true" />
                          <span className="sr-only">Remove</span>
                        </button>
                      </div>
                    </div>
                  </div>

                  {/* Expanded notes editor */}
                  {isExpanded && (
                    <div className="mt-3 pt-3 border-t border-lsc-border/40 dark:border-earth-700/60">
                      <label htmlFor={`notes-${entry.id}`} className="sr-only">Private notes for {item.title}</label>
                      <textarea
                        id={`notes-${entry.id}`}
                        value={editingNotes[entry.id] ?? ''}
                        onChange={(e) => setEditingNotes((prev) => ({ ...prev, [entry.id]: e.target.value }))}
                        placeholder={t('placeholder.shelf.addPrivateNotes')}
                        rows={3}
                        className="w-full text-sm rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream p-2.5 resize-y focus:outline-none focus:ring-2 focus:ring-lsc-rose/50"
                      />
                      <div className="flex justify-end mt-2">
                        <button
                          onClick={() => handleSaveNotes(entry.catalog_item_id, entry.status, entry.personal_tags)}
                          disabled={savingNotes.has(entry.id)}
                          className="text-xs font-medium px-3 py-1.5 rounded-lg bg-lsc-rose text-white hover:bg-lsc-rose/90 disabled:opacity-50 transition-colors"
                        >
                          {savingNotes.has(entry.id) ? 'Saving...' : 'Save Notes'}
                        </button>
                      </div>
                    </div>
                  )}
                </li>
              )
            })}
          </ul>
        )}
      </div>
    </section>
  )
}

/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useMemo, useRef, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Clock,
  Star,
  Trash2,
  Copy,
  Loader2,
  Search,
  X,
  Download,
} from 'lucide-react'
import toast from 'react-hot-toast'
import {
  getSavedContent,
  deleteSavedContent,
  toggleFavorite,
  getContentTypeLabel,
  CONTENT_TYPE_OPTIONS,
  type ContentType,
  type SavedContent,
} from '@/api/marketing-hub-api'
import { useTranslation, getCurrentLocale } from '@/i18n'
import { clean } from '@/lib/utils'
import ConfirmDialog from '@/components/ConfirmDialog'

const PAGE_SIZE = 25

function formatDateForFilename(d: Date): string {
  const yyyy = d.getFullYear()
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  return `${yyyy}-${mm}-${dd}`
}

export function HistoryTab({ token }: { token: string }): React.ReactElement {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [filterType, setFilterType] = useState<string>('all')
  const [favoritesOnly, setFavoritesOnly] = useState(false)
  const [deleteConfirm, setDeleteConfirm] = useState<SavedContent | null>(null)

  // Search (debounced)
  const [searchInput, setSearchInput] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  useEffect(() => {
    const id = window.setTimeout(() => setDebouncedSearch(searchInput.trim()), 250)
    return () => window.clearTimeout(id)
  }, [searchInput])

  // Pagination via increasing limit
  const [limit, setLimit] = useState<number>(PAGE_SIZE)

  // Reset limit when filters or search change
  useEffect(() => {
    setLimit(PAGE_SIZE)
  }, [filterType, favoritesOnly, debouncedSearch])

  // Selection
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())
  const [bulkDeleteConfirm, setBulkDeleteConfirm] = useState(false)
  const [bulkDeleting, setBulkDeleting] = useState(false)

  const { data, isLoading, isFetching } = useQuery({
    queryKey: ['marketing-hub-history', filterType, favoritesOnly, limit],
    queryFn: () =>
      getSavedContent(
        token,
        clean({
          content_type: filterType !== 'all' ? (filterType as ContentType) : undefined,
          favorites_only: favoritesOnly,
          limit,
        }),
      ),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteSavedContent(token, id),
    onSuccess: () => {
      toast.success(t('toast.marketingHub.contentDeleted'))
      queryClient.invalidateQueries({ queryKey: ['marketing-hub-history'] })
      setDeleteConfirm(null)
    },
    onError: (error: Error) => toast.error(error.message),
  })

  const favoriteMutation = useMutation({
    mutationFn: (id: number) => toggleFavorite(token, id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['marketing-hub-history'] })
    },
    onError: (error: Error) => toast.error(error.message),
  })

  const handleCopy = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text)
      toast.success(t('toast.copiedToClipboard'))
    } catch {
      toast.error(t('marketingHub.failedToCopyToClipboard'))
    }
  }

  const allItems = useMemo(() => data?.items ?? [], [data?.items])
  const total = data?.total ?? 0

  // Client-side search filter
  const visibleItems = useMemo(() => {
    if (!debouncedSearch) return allItems
    const q = debouncedSearch.toLowerCase()
    return allItems.filter((it) => {
      return (
        (it.title ?? '').toLowerCase().includes(q) ||
        it.user_prompt.toLowerCase().includes(q) ||
        it.generated_text.toLowerCase().includes(q)
      )
    })
  }, [allItems, debouncedSearch])

  // Drop selections that no longer match the visible list
  useEffect(() => {
    setSelectedIds((prev) => {
      if (prev.size === 0) return prev
      const visibleIds = new Set(visibleItems.map((i) => i.id))
      let changed = false
      const next = new Set<number>()
      for (const id of prev) {
        if (visibleIds.has(id)) next.add(id)
        else changed = true
      }
      return changed ? next : prev
    })
  }, [visibleItems])

  const selectedItems = useMemo(
    () => visibleItems.filter((it) => selectedIds.has(it.id)),
    [visibleItems, selectedIds],
  )

  const allSelected = visibleItems.length > 0 && selectedIds.size === visibleItems.length
  const someSelected = selectedIds.size > 0 && !allSelected

  // Indeterminate "select all" checkbox
  const selectAllRef = useRef<HTMLInputElement | null>(null)
  useEffect(() => {
    if (selectAllRef.current) {
      selectAllRef.current.indeterminate = someSelected
    }
  }, [someSelected])

  const toggleSelectOne = (id: number) => {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const toggleSelectAll = () => {
    if (allSelected) {
      setSelectedIds(new Set())
    } else {
      setSelectedIds(new Set(visibleItems.map((i) => i.id)))
    }
  }

  const clearSelection = () => setSelectedIds(new Set())

  const handleBulkCopy = async () => {
    const text = selectedItems.map((it) => it.generated_text).join('\n\n---\n\n')
    try {
      await navigator.clipboard.writeText(text)
      toast.success(t('toast.copiedToClipboard'))
    } catch {
      toast.error(t('marketingHub.failedToCopyToClipboard'))
    }
  }

  const handleBulkExport = () => {
    const lines = selectedItems.map((it) => {
      return [
        `Title: ${it.title ?? '(untitled)'}`,
        `Type: ${getContentTypeLabel(it.content_type)}`,
        `Prompt: ${it.user_prompt}`,
        `Generated:\n${it.generated_text}`,
      ].join('\n')
    })
    const body = lines.join('\n\n---\n\n')
    const blob = new Blob([body], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `marketing-history-${formatDateForFilename(new Date())}.txt`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const handleBulkFavorite = async () => {
    const allFavorited = selectedItems.every((it) => it.is_favorite)
    // If all favorited -> unfavorite all. Otherwise -> favorite all not-yet-favorited.
    const targets = allFavorited ? selectedItems : selectedItems.filter((it) => !it.is_favorite)
    try {
      await Promise.all(targets.map((it) => toggleFavorite(token, it.id)))
      queryClient.invalidateQueries({ queryKey: ['marketing-hub-history'] })
      toast.success(
        allFavorited
          ? `Removed ${targets.length} from favorites`
          : `Added ${targets.length} to favorites`,
      )
      clearSelection()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Bulk favorite failed')
    }
  }

  const handleBulkDelete = async () => {
    setBulkDeleting(true)
    try {
      await Promise.all(selectedItems.map((it) => deleteSavedContent(token, it.id)))
      queryClient.invalidateQueries({ queryKey: ['marketing-hub-history'] })
      toast.success(`Deleted ${selectedItems.length} saved drafts`)
      clearSelection()
      setBulkDeleteConfirm(false)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Bulk delete failed')
    } finally {
      setBulkDeleting(false)
    }
  }

  const allFavoritedInSelection =
    selectedItems.length > 0 && selectedItems.every((it) => it.is_favorite)

  const canLoadMore = allItems.length < total
  const remaining = Math.max(total - allItems.length, 0)

  const emptyMessage = debouncedSearch
    ? `No matches for "${debouncedSearch}"`
    : favoritesOnly
      ? 'No favorite content yet'
      : 'No saved content yet. Generate some content and save it.'

  return (
    <div className="space-y-6">
      {/* Search */}
      <div className="relative">
        <label htmlFor="marketing-history-search" className="sr-only">
          Search saved drafts
        </label>
        <Search
          aria-hidden="true"
          className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-lsc-dark/60 dark:text-lsc-cream/70 motion-safe:transition-colors"
        />
        <input
          id="marketing-history-search"
          type="search"
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          placeholder="Search title, prompt, or text…"
          aria-label="Search saved drafts by title, prompt, or generated text"
          className="w-full pl-9 pr-10 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream placeholder:text-lsc-dark/50 dark:placeholder:text-lsc-cream/60 focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
        />
        {searchInput && (
          <button
            type="button"
            onClick={() => setSearchInput('')}
            aria-label="Clear search"
            className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 rounded-lg text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-earth-700 focus:outline-none focus:ring-2 focus:ring-lsc-rose motion-safe:transition-colors"
          >
            <X aria-hidden="true" className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Filters */}
      <div className="flex flex-col md:flex-row gap-4 items-start md:items-center">
        <div className="flex gap-3">
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            aria-label="Filter by content type"
            className="px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
          >
            <option value="all">All Types</option>
            {CONTENT_TYPE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
          <button
            type="button"
            onClick={() => setFavoritesOnly(!favoritesOnly)}
            aria-pressed={favoritesOnly}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg border motion-safe:transition-colors focus:outline-none focus:ring-2 focus:ring-lsc-rose ${
              favoritesOnly
                ? 'bg-status-warning-100 dark:bg-status-warning-900/30 border-status-warning-300 dark:border-status-warning-700 text-status-warning-800 dark:text-status-warning-300'
                : 'border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark/70 dark:text-lsc-cream/70'
            }`}
          >
            <Star aria-hidden="true" className={`w-4 h-4 ${favoritesOnly ? 'fill-current' : ''}`} />
            Favorites
          </button>
        </div>
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
          {total} saved drafts{debouncedSearch ? ` · ${visibleItems.length} match search` : ''}
        </p>
      </div>

      {/* Bulk action bar (announced via aria-live) */}
      <div
        role="region"
        aria-label="Bulk actions"
        aria-live="polite"
        className={selectedIds.size > 0 ? 'block' : 'sr-only'}
      >
        {selectedIds.size > 0 && (
          <div className="sticky top-2 z-10 flex flex-wrap items-center gap-2 p-3 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 shadow-sm">
            <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream mr-2">
              {selectedIds.size} {selectedIds.size === 1 ? 'draft' : 'drafts'} selected
            </span>
            <button
              type="button"
              onClick={handleBulkFavorite}
              className="inline-flex items-center gap-2 min-h-[44px] px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-700 focus:outline-none focus:ring-2 focus:ring-lsc-rose motion-safe:transition-colors"
            >
              <Star
                aria-hidden="true"
                className={`w-4 h-4 ${allFavoritedInSelection ? 'fill-current text-status-warning-500' : ''}`}
              />
              {allFavoritedInSelection ? 'Unfavorite all' : 'Favorite all'}
            </button>
            <button
              type="button"
              onClick={handleBulkCopy}
              className="inline-flex items-center gap-2 min-h-[44px] px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-700 focus:outline-none focus:ring-2 focus:ring-lsc-rose motion-safe:transition-colors"
            >
              <Copy aria-hidden="true" className="w-4 h-4" />
              Copy all
            </button>
            <button
              type="button"
              onClick={handleBulkExport}
              className="inline-flex items-center gap-2 min-h-[44px] px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-700 focus:outline-none focus:ring-2 focus:ring-lsc-rose motion-safe:transition-colors"
            >
              <Download aria-hidden="true" className="w-4 h-4" />
              Export as text
            </button>
            <button
              type="button"
              onClick={() => setBulkDeleteConfirm(true)}
              className="inline-flex items-center gap-2 min-h-[44px] px-4 py-2 rounded-lg bg-status-danger-600 text-lsc-cream hover:bg-status-danger-700 focus:outline-none focus:ring-2 focus:ring-status-danger-500 motion-safe:transition-colors"
            >
              <Trash2 aria-hidden="true" className="w-4 h-4" />
              Delete selected
            </button>
            <button
              type="button"
              onClick={clearSelection}
              className="inline-flex items-center gap-2 min-h-[44px] px-4 py-2 rounded-lg text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-earth-700 focus:outline-none focus:ring-2 focus:ring-lsc-rose motion-safe:transition-colors"
            >
              Clear selection
            </button>
          </div>
        )}
      </div>

      {/* Content List */}
      {isLoading ? (
        <div className="flex justify-center py-12" role="status" aria-live="polite">
          <Loader2 aria-hidden="true" className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
          <span className="sr-only">Loading saved content…</span>
        </div>
      ) : visibleItems.length === 0 ? (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-8 text-center border border-lsc-border dark:border-earth-700">
          <Clock
            aria-hidden="true"
            className="w-12 h-12 text-lsc-dark/30 dark:text-lsc-cream/60 mx-auto mb-4 opacity-50"
          />
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{emptyMessage}</p>
        </div>
      ) : (
        <>
          {/* Select all */}
          <div className="flex items-center gap-2 px-1">
            <input
              ref={selectAllRef}
              id="marketing-history-select-all"
              type="checkbox"
              className="w-4 h-4 accent-lsc-rose focus:outline-none focus:ring-2 focus:ring-lsc-rose rounded"
              checked={allSelected}
              aria-checked={someSelected ? 'mixed' : allSelected}
              onChange={toggleSelectAll}
            />
            <label
              htmlFor="marketing-history-select-all"
              className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 select-none"
            >
              Select all visible drafts
            </label>
          </div>

          <ul
            className="space-y-4 list-none p-0"
            aria-busy={isFetching && allItems.length > 0 ? 'true' : 'false'}
          >
            {visibleItems.map((item) => {
              const isSelected = selectedIds.has(item.id)
              const itemLabel = item.title || getContentTypeLabel(item.content_type)
              return (
                <li
                  key={item.id}
                  className={`bg-lsc-white dark:bg-earth-800 rounded-xl border overflow-hidden motion-safe:transition-colors ${
                    isSelected
                      ? 'border-lsc-rose border-l-4'
                      : 'border-lsc-border dark:border-earth-700'
                  }`}
                >
                  <div className="flex items-center justify-between px-4 py-3 bg-lsc-cream/50 dark:bg-lsc-brown/30 border-b border-lsc-border dark:border-earth-700">
                    <div className="flex items-center gap-3">
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => toggleSelectOne(item.id)}
                        aria-label={`Select ${itemLabel}`}
                        className="w-4 h-4 accent-lsc-rose focus:outline-none focus:ring-2 focus:ring-lsc-rose rounded"
                      />
                      <span className="px-2.5 py-1 rounded-full text-xs font-medium bg-lsc-rose/10 text-lsc-rose">
                        {getContentTypeLabel(item.content_type)}
                      </span>
                      {item.title && (
                        <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                          {item.title}
                        </span>
                      )}
                      <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                        {new Date(item.created_at).toLocaleDateString(getCurrentLocale(), {
                          month: 'short',
                          day: 'numeric',
                          hour: 'numeric',
                          minute: '2-digit',
                        })}
                      </span>
                    </div>
                    <div className="flex items-center gap-1">
                      <button
                        type="button"
                        onClick={() => favoriteMutation.mutate(item.id)}
                        aria-pressed={item.is_favorite}
                        aria-label={item.is_favorite ? 'Remove from favorites' : 'Add to favorites'}
                        className="p-2 hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-lg motion-safe:transition-colors focus:outline-none focus:ring-2 focus:ring-lsc-rose"
                      >
                        <Star
                          aria-hidden="true"
                          className={`w-4 h-4 ${
                            item.is_favorite
                              ? 'text-status-warning-500 fill-current'
                              : 'text-lsc-dark/70 dark:text-lsc-cream/70'
                          }`}
                        />
                      </button>
                      <button
                        type="button"
                        onClick={() => handleCopy(item.generated_text)}
                        aria-label="Copy content to clipboard"
                        title="Copy to clipboard"
                        className="p-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-lg motion-safe:transition-colors focus:outline-none focus:ring-2 focus:ring-lsc-rose"
                      >
                        <Copy aria-hidden="true" className="w-4 h-4" />
                      </button>
                      <button
                        type="button"
                        onClick={() => setDeleteConfirm(item)}
                        aria-label="Delete saved content"
                        title="Delete"
                        className="p-2 text-status-danger-700 dark:text-status-danger-400 hover:bg-status-danger-100 dark:hover:bg-status-danger-900/30 rounded-lg motion-safe:transition-colors focus:outline-none focus:ring-2 focus:ring-status-danger-500"
                      >
                        <Trash2 aria-hidden="true" className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                  <div className="p-4">
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
                      Prompt:{' '}
                      {item.user_prompt.length > 120
                        ? item.user_prompt.slice(0, 120) + '…'
                        : item.user_prompt}
                    </p>
                    <div className="whitespace-pre-wrap text-lsc-dark dark:text-lsc-cream leading-relaxed text-sm">
                      {item.generated_text}
                    </div>
                  </div>
                </li>
              )
            })}
          </ul>

          {/* Load more — only when not search-filtering (search runs over already-loaded items;
              loading more brings in more rows from the server, which is what we want regardless) */}
          {canLoadMore && (
            <div className="flex justify-center pt-2">
              <button
                type="button"
                onClick={() => setLimit((l) => l + PAGE_SIZE)}
                disabled={isFetching}
                aria-label={`Load ${PAGE_SIZE} more saved drafts`}
                className="inline-flex items-center gap-2 min-h-[44px] px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-700 focus:outline-none focus:ring-2 focus:ring-lsc-rose motion-safe:transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
              >
                {isFetching ? (
                  <>
                    <Loader2
                      aria-hidden="true"
                      className="w-4 h-4 motion-safe:animate-spin text-lsc-rose"
                    />
                    <span className="sr-only">Loading more saved drafts…</span>
                    <span aria-hidden="true">Loading…</span>
                  </>
                ) : (
                  <>Load more ({PAGE_SIZE} of {remaining} remaining)</>
                )}
              </button>
            </div>
          )}
        </>
      )}

      <ConfirmDialog
        isOpen={!!deleteConfirm}
        title="Delete Content?"
        message="This will permanently delete this saved content. This action cannot be undone."
        confirmText="Delete"
        confirmVariant="danger"
        onConfirm={() => {
          if (deleteConfirm) deleteMutation.mutate(deleteConfirm.id)
        }}
        onCancel={() => setDeleteConfirm(null)}
        loading={deleteMutation.isPending}
      />

      <ConfirmDialog
        isOpen={bulkDeleteConfirm}
        title="Delete selected drafts?"
        message={`This will permanently delete ${selectedIds.size} saved ${
          selectedIds.size === 1 ? 'draft' : 'drafts'
        }. This action cannot be undone.`}
        confirmText="Delete all"
        confirmVariant="danger"
        onConfirm={handleBulkDelete}
        onCancel={() => setBulkDeleteConfirm(false)}
        loading={bulkDeleting}
      />
    </div>
  )
}

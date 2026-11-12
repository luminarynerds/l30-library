/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import toast from 'react-hot-toast'
import { ChevronDown, ChevronRight, Play, Pencil, Trash2, Bell, BellOff } from 'lucide-react'
import { useTranslation } from '@/i18n/I18nContext'
import { useUnifiedAccessibility } from '@/features/accessibility/hooks/useUnifiedAccessibility'
import { type SavedSearch, useSavedSearches } from '../hooks/useSavedSearches'

interface SavedSearchesPanelProps {
  /** Patron-facing "run" callback. Implementation pushes ?saved=<id> to the URL. */
  onRun: (id: string) => void
  /** Default open/collapsed. Defaults to open since the panel is empty-state when there's nothing to show. */
  defaultOpen?: boolean
}

export default function SavedSearchesPanel({
  onRun,
  defaultOpen = true,
}: SavedSearchesPanelProps): React.ReactElement {
  const { t } = useTranslation()
  const { announceToScreenReader } = useUnifiedAccessibility()
  const [isOpen, setIsOpen] = useState(defaultOpen)
  const [renameId, setRenameId] = useState<string | null>(null)
  const [renameValue, setRenameValue] = useState('')

  const { savedSearches, isLoading, isError, update, remove } = useSavedSearches()

  const handleRunClick = (s: SavedSearch) => {
    onRun(s.id)
    announceToScreenReader(`Running saved search ${s.name}`)
  }

  const handleStartRename = (s: SavedSearch) => {
    setRenameId(s.id)
    setRenameValue(s.name)
  }

  const handleCancelRename = () => {
    setRenameId(null)
    setRenameValue('')
  }

  const handleSubmitRename = async (s: SavedSearch) => {
    const trimmed = renameValue.trim()
    if (!trimmed || trimmed === s.name) {
      handleCancelRename()
      return
    }
    try {
      await update.mutateAsync({ id: s.id, input: { name: trimmed } })
      toast.success(t('catalog.savedSearches.dialog.saved', 'Saved.'))
      handleCancelRename()
    } catch {
      toast.error(t('catalog.savedSearches.dialog.saveError', 'Could not save this search. Please try again.'))
    }
  }

  const handleDelete = async (s: SavedSearch) => {
    const confirmText = t('catalog.savedSearches.panel.confirmDelete', 'Delete "{{name}}"?').replace(
      '{{name}}',
      s.name,
    )
    // window.confirm is the most accessible cross-browser confirmation that
    // doesn't require us to ship a second focus-trapped modal for what is a
    // single destructive click. Matches other delete flows on the site.
    if (!window.confirm(confirmText)) return
    try {
      await remove.mutateAsync(s.id)
      announceToScreenReader(`Deleted saved search ${s.name}`)
    } catch {
      toast.error(t('catalog.savedSearches.panel.loadError', 'Could not load your saved searches.'))
    }
  }

  const handleToggleNotify = async (s: SavedSearch) => {
    const next = !s.notify_on_new
    try {
      await update.mutateAsync({ id: s.id, input: { notify_on_new: next } })
    } catch {
      toast.error(t('catalog.savedSearches.dialog.saveError', 'Could not save this search. Please try again.'))
    }
  }

  return (
    <section
      aria-label={t('catalog.savedSearches.panel.title', 'Saved searches')}
      className="mb-4 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800"
      data-testid="saved-searches-panel"
    >
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        aria-expanded={isOpen}
        aria-controls="saved-searches-panel-body"
        className="flex w-full items-center justify-between px-3 py-2 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream/50 dark:hover:bg-earth-700/50 focus:outline-none focus:ring-2 focus:ring-lsc-rose rounded-t-lg"
      >
        <span className="flex items-center gap-2">
          {isOpen ? <ChevronDown className="h-4 w-4" aria-hidden /> : <ChevronRight className="h-4 w-4" aria-hidden />}
          {t('catalog.savedSearches.panel.title', 'Saved searches')}
          {savedSearches.length > 0 && (
            <span className="ml-1 rounded-full bg-lsc-rose/10 px-2 py-0.5 text-xs font-medium text-lsc-rose">
              {savedSearches.length}
            </span>
          )}
        </span>
      </button>

      {isOpen && (
        <div id="saved-searches-panel-body" className="border-t border-lsc-border dark:border-earth-700 p-3 text-sm">
          {isLoading && (
            <p className="text-lsc-dark/60 dark:text-lsc-cream/60">{t('common.loading', 'Loading...')}</p>
          )}
          {isError && (
            <p role="alert" className="text-red-700 dark:text-red-300">
              {t('catalog.savedSearches.panel.loadError', 'Could not load your saved searches.')}
            </p>
          )}
          {!isLoading && !isError && savedSearches.length === 0 && (
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70" data-testid="saved-searches-empty">
              {t('catalog.savedSearches.panel.empty', 'No saved searches yet.')}
            </p>
          )}
          {!isLoading && !isError && savedSearches.length > 0 && (
            <ul className="flex flex-col gap-2">
              {savedSearches.map((s) => (
                <li
                  key={s.id}
                  className="rounded-lg border border-lsc-border/60 dark:border-earth-700/60 bg-lsc-cream/40 dark:bg-earth-900/30 p-2"
                  data-testid={`saved-search-row-${s.id}`}
                >
                  {renameId === s.id ? (
                    <form
                      onSubmit={(e) => {
                        e.preventDefault()
                        handleSubmitRename(s)
                      }}
                      className="flex items-center gap-2"
                    >
                      <input
                        type="text"
                        value={renameValue}
                        onChange={(e) => setRenameValue(e.target.value)}
                        maxLength={120}
                        autoFocus
                        aria-label={t('catalog.savedSearches.dialog.nameLabel', 'Name')}
                        className="flex-1 rounded border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-800 px-2 py-1 text-sm text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"
                      />
                      <button
                        type="submit"
                        disabled={update.isPending}
                        className="rounded bg-lsc-rose px-2 py-1 text-xs font-semibold text-white hover:bg-lsc-rose/90 focus:outline-none focus:ring-2 focus:ring-lsc-rose disabled:opacity-60"
                      >
                        {t('catalog.savedSearches.dialog.save', 'Save')}
                      </button>
                      <button
                        type="button"
                        onClick={handleCancelRename}
                        className="rounded px-2 py-1 text-xs text-lsc-dark/70 dark:text-lsc-cream/70 hover:underline"
                      >
                        {t('catalog.savedSearches.dialog.cancel', 'Cancel')}
                      </button>
                    </form>
                  ) : (
                    <>
                      <div className="flex items-start justify-between gap-2">
                        <span className="break-words font-medium text-lsc-dark dark:text-lsc-cream">
                          {s.name}
                        </span>
                        <button
                          type="button"
                          onClick={() => handleRunClick(s)}
                          className="flex shrink-0 items-center gap-1 rounded bg-lsc-rose px-2 py-1 text-xs font-semibold text-white hover:bg-lsc-rose/90 focus:outline-none focus:ring-2 focus:ring-lsc-rose"
                          data-testid={`saved-search-run-${s.id}`}
                        >
                          <Play className="h-3 w-3" aria-hidden />
                          {t('catalog.savedSearches.panel.run', 'Run')}
                        </button>
                      </div>
                      <div className="mt-1 flex flex-wrap items-center gap-3 text-xs text-lsc-dark/60 dark:text-lsc-cream/60">
                        <button
                          type="button"
                          onClick={() => handleStartRename(s)}
                          className="inline-flex items-center gap-1 hover:underline focus:outline-none focus:ring-2 focus:ring-lsc-rose rounded"
                        >
                          <Pencil className="h-3 w-3" aria-hidden />
                          {t('catalog.savedSearches.panel.rename', 'Rename')}
                        </button>
                        <button
                          type="button"
                          onClick={() => handleDelete(s)}
                          className="inline-flex items-center gap-1 text-red-700 dark:text-red-300 hover:underline focus:outline-none focus:ring-2 focus:ring-lsc-rose rounded"
                          data-testid={`saved-search-delete-${s.id}`}
                        >
                          <Trash2 className="h-3 w-3" aria-hidden />
                          {t('catalog.savedSearches.panel.delete', 'Delete')}
                        </button>
                        <button
                          type="button"
                          onClick={() => handleToggleNotify(s)}
                          aria-pressed={s.notify_on_new}
                          className="inline-flex items-center gap-1 hover:underline focus:outline-none focus:ring-2 focus:ring-lsc-rose rounded"
                        >
                          {s.notify_on_new ? (
                            <Bell className="h-3 w-3" aria-hidden />
                          ) : (
                            <BellOff className="h-3 w-3" aria-hidden />
                          )}
                          {s.notify_on_new
                            ? t('catalog.savedSearches.dialog.notifyInApp', 'Notify me in the app when new items match')
                            : t('catalog.savedSearches.dialog.notifyInApp', 'Notify me in the app when new items match')}
                        </button>
                      </div>
                    </>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </section>
  )
}

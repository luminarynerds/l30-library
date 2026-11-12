/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowDown, ArrowUp, Loader2, Plus, Search, Trash2, X } from 'lucide-react'
import toast from 'react-hot-toast'

import FocusTrap from 'focus-trap-react'
import { useTranslation } from '@/i18n'
import { useAuth } from '@/contexts/AuthContext'
import {
  addProgramBooklistItem,
  deleteProgramBooklistItem,
  getProgramBooklist,
  reorderProgramBooklist,
  updateProgramBooklistItem,
  type ProgramBooklistItem,
} from '@/api/domains/content/reading-programs-api'
import { searchCatalog } from '@/api/domains/catalog/catalog-api'

interface Props {
  programId: number
  programName: string
  onClose: () => void
}

export default function AdminProgramBooklistManager({
  programId,
  programName,
  onClose,
}: Props): React.ReactElement {
  const { t } = useTranslation()
  const { token } = useAuth()
  const queryClient = useQueryClient()
  const [searchTerm, setSearchTerm] = useState('')
  const [editingNoteId, setEditingNoteId] = useState<number | null>(null)
  const [editingNoteVal, setEditingNoteVal] = useState('')

  const booklistKey = ['admin-program-booklist', programId]

  const { data, isLoading } = useQuery({
    queryKey: booklistKey,
    queryFn: () => getProgramBooklist(programId),
  })
  const items = data?.items ?? []

  const searchKey = ['admin-program-booklist-search', searchTerm]
  const { data: searchResults } = useQuery({
    queryKey: searchKey,
    queryFn: () => searchCatalog({ query: searchTerm, per_page: 10 }),
    enabled: searchTerm.trim().length >= 2,
  })

  const addMutation = useMutation({
    mutationFn: (catalogItemId: number) =>
      addProgramBooklistItem(token!, programId, {
        catalog_item_id: catalogItemId,
        display_order: items.length,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: booklistKey })
      toast.success(t('admin.programs.booklist.added') || 'Added to booklist')
    },
    onError: (err: Error) => toast.error(err.message),
  })

  const deleteMutation = useMutation({
    mutationFn: (itemId: number) => deleteProgramBooklistItem(token!, programId, itemId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: booklistKey })
    },
    onError: (err: Error) => toast.error(err.message),
  })

  const updateMutation = useMutation({
    mutationFn: ({ itemId, note }: { itemId: number; note: string }) =>
      updateProgramBooklistItem(token!, programId, itemId, { note }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: booklistKey })
      setEditingNoteId(null)
    },
    onError: (err: Error) => toast.error(err.message),
  })

  const reorderMutation = useMutation({
    mutationFn: (order: { item_id: number; display_order: number }[]) =>
      reorderProgramBooklist(token!, programId, order),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: booklistKey })
    },
    onError: (err: Error) => toast.error(err.message),
  })

  const move = (index: number, direction: -1 | 1) => {
    const target = index + direction
    if (target < 0 || target >= items.length) return
    const a = items[index]
    const b = items[target]
    if (!a || !b) return
    reorderMutation.mutate([
      { item_id: a.id, display_order: b.display_order },
      { item_id: b.id, display_order: a.display_order },
    ])
  }

  const startEditNote = (it: ProgramBooklistItem) => {
    setEditingNoteId(it.id)
    setEditingNoteVal(it.note ?? '')
  }

  const saveEditNote = (itemId: number) => {
    updateMutation.mutate({ itemId, note: editingNoteVal })
  }

  return (
    <div
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
      onClick={onClose}
      onKeyDown={(e) => { if (e.key === 'Escape') onClose() }}
      role="presentation"
    >
      <FocusTrap
        focusTrapOptions={{
          escapeDeactivates: false,
          allowOutsideClick: true,
          returnFocusOnDeactivate: true,
          fallbackFocus: () => document.body,
        }}
      >
      {/* eslint-disable-next-line jsx-a11y/click-events-have-key-events */}
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="booklist-manager-title"
        className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-3xl w-full max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="sticky top-0 bg-lsc-white dark:bg-earth-800 border-b border-lsc-border dark:border-earth-700 p-4 flex items-center justify-between">
          <h2
            id="booklist-manager-title"
            className="text-lg font-serif font-semibold text-lsc-dark dark:text-lsc-cream"
          >
            {t('admin.programs.booklist.title') || 'Manage booklist'}: {programName}
          </h2>
          <button
            onClick={onClose}
            className="p-2 min-w-[44px] min-h-[44px] flex items-center justify-center hover:bg-lsc-cream dark:hover:bg-lsc-brown rounded-full"
            aria-label={t('aria.authModals.close') || 'Close'}
          >
            <X className="w-5 h-5" aria-hidden="true" />
          </button>
        </div>

        <div className="p-6 space-y-6">
          <section>
            <label
              htmlFor="booklist-search"
              className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2"
            >
              {t('admin.programs.booklist.search') || 'Search catalog'}
            </label>
            <div className="flex gap-2">
              <div className="relative flex-1">
                <Search
                  className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70"
                  aria-hidden="true"
                />
                <input
                  id="booklist-search"
                  type="search"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  placeholder={t('admin.programs.booklist.searchPlaceholder') || 'Title, author, ISBN…'}
                  className="w-full pl-9 pr-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
                />
              </div>
            </div>
            {searchResults?.items?.length ? (
              <ul className="mt-3 space-y-1 border border-lsc-border dark:border-earth-700 rounded-lg overflow-hidden">
                {searchResults.items.slice(0, 10).map((res) => (
                  <li
                    key={res.id}
                    className="flex items-center justify-between px-3 py-2 hover:bg-lsc-cream/40 dark:hover:bg-lsc-brown/30"
                  >
                    <span className="text-sm text-lsc-dark dark:text-lsc-cream truncate">
                      {res.title}
                      {res.author ? ` — ${res.author}` : ''}
                    </span>
                    <button
                      type="button"
                      onClick={() => addMutation.mutate(res.id)}
                      disabled={addMutation.isPending}
                      className="text-sm px-2 py-1 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg flex items-center gap-1 disabled:opacity-50"
                    >
                      <Plus className="w-3 h-3" aria-hidden="true" />
                      {t('admin.programs.booklist.add') || 'Add'}
                    </button>
                  </li>
                ))}
              </ul>
            ) : null}
          </section>

          <section>
            <h3 className="text-base font-semibold text-lsc-dark dark:text-lsc-cream mb-3">
              {t('admin.programs.booklist.currentList') || 'Current booklist'} ({items.length})
            </h3>
            {isLoading ? (
              <Loader2 className="w-6 h-6 motion-safe:animate-spin text-lsc-rose" />
            ) : items.length === 0 ? (
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                {t('admin.programs.booklist.empty') || 'No items on this booklist yet.'}
              </p>
            ) : (
              <ol className="space-y-2">
                {items.map((it, idx) => (
                  <li
                    key={it.id}
                    className="flex items-start gap-3 p-3 bg-lsc-cream/40 dark:bg-lsc-brown/20 rounded-lg"
                  >
                    <div className="flex flex-col gap-1">
                      <button
                        type="button"
                        onClick={() => move(idx, -1)}
                        disabled={idx === 0 || reorderMutation.isPending}
                        className="p-1 rounded hover:bg-lsc-cream dark:hover:bg-lsc-brown/50 disabled:opacity-30"
                        aria-label={t('admin.programs.booklist.moveUp') || 'Move up'}
                      >
                        <ArrowUp className="w-4 h-4" aria-hidden="true" />
                      </button>
                      <button
                        type="button"
                        onClick={() => move(idx, 1)}
                        disabled={idx === items.length - 1 || reorderMutation.isPending}
                        className="p-1 rounded hover:bg-lsc-cream dark:hover:bg-lsc-brown/50 disabled:opacity-30"
                        aria-label={t('admin.programs.booklist.moveDown') || 'Move down'}
                      >
                        <ArrowDown className="w-4 h-4" aria-hidden="true" />
                      </button>
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="font-medium text-lsc-dark dark:text-lsc-cream truncate">
                        {it.catalog_item.title}
                      </div>
                      {it.catalog_item.author && (
                        <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 truncate">
                          {it.catalog_item.author}
                        </div>
                      )}
                      {editingNoteId === it.id ? (
                        <div className="mt-2 flex gap-2">
                          <input
                            type="text"
                            value={editingNoteVal}
                            onChange={(e) => setEditingNoteVal(e.target.value)}
                            maxLength={500}
                            placeholder={
                              t('admin.programs.booklist.notePlaceholder') || 'Curator note (optional)'
                            }
                            className="flex-1 px-2 py-1 text-sm border border-lsc-border dark:border-earth-700 rounded bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
                          />
                          <button
                            type="button"
                            onClick={() => saveEditNote(it.id)}
                            className="text-sm px-2 py-1 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded"
                          >
                            {t('admin.programs.booklist.save') || 'Save'}
                          </button>
                        </div>
                      ) : (
                        <button
                          type="button"
                          onClick={() => startEditNote(it)}
                          className="mt-1 text-sm italic text-lsc-dark/80 dark:text-lsc-cream/80 hover:underline text-left"
                        >
                          {it.note ||
                            (t('admin.programs.booklist.notePlaceholder') || 'Add a note…')}
                        </button>
                      )}
                    </div>
                    <button
                      type="button"
                      onClick={() => deleteMutation.mutate(it.id)}
                      disabled={deleteMutation.isPending}
                      className="p-2 text-status-danger-600 dark:text-status-danger-400 hover:bg-status-danger-100 dark:hover:bg-status-danger-900/30 rounded-lg"
                      aria-label={t('admin.programs.booklist.remove') || 'Remove'}
                    >
                      <Trash2 className="w-4 h-4" aria-hidden="true" />
                    </button>
                  </li>
                ))}
              </ol>
            )}
          </section>
        </div>
      </div>
      </FocusTrap>
    </div>
  )
}

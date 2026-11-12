/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Shelf list with up/down reorder buttons (no @dnd-kit in this codebase).
 */
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Pencil, Trash2, ArrowUp, ArrowDown, Eye, EyeOff } from 'lucide-react'
import toast from 'react-hot-toast'
import { useTranslation } from '@/i18n'
import {
  deleteShelf,
  listShelves,
  ShelfAdminRead,
  updateShelf,
} from '@/api/home'
import { ShelfEditor } from './ShelfEditor'

export function ShelfList() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [editingId, setEditingId] = useState<number | 'new' | null>(null)

  const { data: shelves = [], isLoading, error } = useQuery({
    queryKey: ['home-admin-shelves'],
    queryFn: listShelves,
  })

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['home-admin-shelves'] })

  const reorderMutation = useMutation({
    mutationFn: ({ id, sort_order }: { id: number; sort_order: number }) =>
      updateShelf(id, { sort_order }),
    onSuccess: () => invalidate(),
    onError: (e: Error) =>
      toast.error(e.message || t('admin.adminHomePage.toasts.reorderFailed', 'Reorder failed')),
  })

  const toggleMutation = useMutation({
    mutationFn: ({ id, is_active }: { id: number; is_active: boolean }) =>
      updateShelf(id, { is_active }),
    onSuccess: () => invalidate(),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteShelf(id),
    onSuccess: () => {
      invalidate()
      toast.success(t('admin.adminHomePage.toasts.shelfDeleted', 'Shelf deleted'))
    },
    onError: (e: Error) =>
      toast.error(e.message || t('admin.adminHomePage.toasts.deleteFailed', 'Delete failed')),
  })

  const move = (idx: number, dir: -1 | 1) => {
    const a = shelves[idx]
    const b = shelves[idx + dir]
    if (!a || !b) return
    reorderMutation.mutate({ id: a.id, sort_order: b.sort_order })
    reorderMutation.mutate({ id: b.id, sort_order: a.sort_order })
  }

  if (editingId !== null) {
    return (
      <ShelfEditor
        shelfId={editingId === 'new' ? null : editingId}
        initial={editingId === 'new' ? null : shelves.find((s) => s.id === editingId) ?? null}
        onDone={() => setEditingId(null)}
      />
    )
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <p className="text-sm text-earth-600 dark:text-earth-400">
          {t(
            'admin.adminHomePage.shelves.help',
            'Each active shelf resolves at request time via its query kind. Empty shelves are skipped.'
          )}
        </p>
        <button
          onClick={() => setEditingId('new')}
          className="inline-flex items-center gap-1.5 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg text-sm font-medium"
        >
          <Plus className="w-4 h-4" aria-hidden="true" />
          {t('admin.adminHomePage.shelves.newButton', 'New shelf')}
        </button>
      </div>

      {isLoading ? (
        <div className="text-center py-12 text-earth-600">{t('common.loading', 'Loading...')}</div>
      ) : error ? (
        <div className="text-center py-12 text-status-danger-600">{(error as Error).message}</div>
      ) : shelves.length === 0 ? (
        <div className="text-center py-12 text-earth-600">
          {t('admin.adminHomePage.shelves.empty', 'No shelves yet. Create one to populate the home page.')}
        </div>
      ) : (
        <ul className="space-y-2">
          {shelves.map((s: ShelfAdminRead, idx: number) => (
            <li
              key={s.id}
              className="flex items-center gap-3 p-3 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800"
            >
              <div className="flex flex-col">
                <button
                  type="button"
                  disabled={idx === 0}
                  onClick={() => move(idx, -1)}
                  className="p-0.5 text-earth-600 hover:text-lsc-rose disabled:opacity-30"
                  aria-label={t('admin.adminHomePage.shelves.moveUp', 'Move up')}
                >
                  <ArrowUp className="w-3.5 h-3.5" />
                </button>
                <button
                  type="button"
                  disabled={idx === shelves.length - 1}
                  onClick={() => move(idx, 1)}
                  className="p-0.5 text-earth-600 hover:text-lsc-rose disabled:opacity-30"
                  aria-label={t('admin.adminHomePage.shelves.moveDown', 'Move down')}
                >
                  <ArrowDown className="w-3.5 h-3.5" />
                </button>
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-lsc-dark dark:text-lsc-cream truncate">
                  {s.heading || s.slug}
                </div>
                <div className="text-xs text-earth-600 dark:text-earth-400 truncate">
                  {s.query_kind} · max {s.max_items}
                </div>
              </div>
              <button
                type="button"
                onClick={() => toggleMutation.mutate({ id: s.id, is_active: !s.is_active })}
                className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${
                  s.is_active
                    ? 'bg-status-success-100 text-status-success-700 dark:bg-status-success-900/30 dark:text-status-success-400'
                    : 'bg-earth-100 text-earth-600 dark:bg-earth-700 dark:text-earth-300'
                }`}
              >
                {s.is_active ? <Eye className="w-3 h-3" /> : <EyeOff className="w-3 h-3" />}
                {s.is_active
                  ? t('admin.adminHomePage.status.active', 'Active')
                  : t('admin.adminHomePage.shelves.inactive', 'Hidden')}
              </button>
              <button
                onClick={() => setEditingId(s.id)}
                className="inline-flex items-center justify-center min-w-[44px] min-h-[44px] p-1.5 rounded hover:bg-earth-100 dark:hover:bg-earth-700 text-earth-600"
                aria-label={t('common.edit', 'Edit')}
              >
                <Pencil className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => {
                  if (
                    window.confirm(
                      t(
                        'admin.adminHomePage.shelves.confirmDelete',
                        'Delete this shelf? This cannot be undone.'
                      )
                    )
                  ) {
                    deleteMutation.mutate(s.id)
                  }
                }}
                className="inline-flex items-center justify-center min-w-[44px] min-h-[44px] p-1.5 rounded hover:bg-status-danger-50 dark:hover:bg-status-danger-900/20 text-status-danger-400"
                aria-label={t('common.delete', 'Delete')}
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

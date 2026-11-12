/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Hero picks list + create button. Editor lives in HeroPickEditor.tsx.
 *
 * Status pills compare active_from / active_to to now():
 *   - active    : active_from <= now AND (active_to is null OR active_to > now)
 *   - scheduled : now < active_from
 *   - expired   : active_to <= now
 */
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Pencil, Trash2, BookOpen } from 'lucide-react'
import toast from 'react-hot-toast'
import { useTranslation } from '@/i18n'
import {
  deleteHeroPick,
  HeroPickRead,
  listHeroPicks,
} from '@/api/home'
import { HeroPickEditor } from './HeroPickEditor'

function statusOf(p: HeroPickRead): 'active' | 'scheduled' | 'expired' {
  const now = Date.now()
  const from = new Date(p.active_from).getTime()
  const to = p.active_to ? new Date(p.active_to).getTime() : null
  if (now < from) return 'scheduled'
  if (to !== null && to <= now) return 'expired'
  return 'active'
}

function StatusPill({ status }: { status: 'active' | 'scheduled' | 'expired' }) {
  const { t } = useTranslation()
  const styles: Record<typeof status, string> = {
    active:
      'bg-status-success-100 text-status-success-700 dark:bg-status-success-900/30 dark:text-status-success-400',
    scheduled:
      'bg-status-info-100 text-status-info-700 dark:bg-status-info-900/30 dark:text-status-info-400',
    expired:
      'bg-earth-100 text-earth-600 dark:bg-earth-700 dark:text-earth-300',
  }
  const label: Record<typeof status, string> = {
    active: t('admin.adminHomePage.status.active', 'Active'),
    scheduled: t('admin.adminHomePage.status.scheduled', 'Scheduled'),
    expired: t('admin.adminHomePage.status.expired', 'Expired'),
  }
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${styles[status]}`}>
      {label[status]}
    </span>
  )
}

export function HeroPickList() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [editingId, setEditingId] = useState<number | 'new' | null>(null)

  const { data: picks = [], isLoading, error } = useQuery({
    queryKey: ['home-admin-hero-picks'],
    queryFn: listHeroPicks,
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteHeroPick(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['home-admin-hero-picks'] })
      toast.success(t('admin.adminHomePage.toasts.heroDeleted', 'Hero pick deleted'))
    },
    onError: (e: Error) =>
      toast.error(e.message || t('admin.adminHomePage.toasts.deleteFailed', 'Delete failed')),
  })

  if (editingId !== null) {
    return (
      <HeroPickEditor
        pickId={editingId === 'new' ? null : editingId}
        initial={editingId === 'new' ? null : picks.find((p) => p.id === editingId) ?? null}
        onDone={() => setEditingId(null)}
      />
    )
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="sr-only">{t('admin.adminHomePage.hero.heading', 'Hero picks')}</h2>
        <p className="text-sm text-earth-600 dark:text-earth-400">
          {t(
            'admin.adminHomePage.hero.help',
            'One hero pick shows at the top of the home page. Pick scheduling is by active window.'
          )}
        </p>
        <button
          onClick={() => setEditingId('new')}
          className="inline-flex items-center gap-1.5 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg text-sm font-medium"
        >
          <Plus className="w-4 h-4" aria-hidden="true" />
          {t('admin.adminHomePage.hero.newButton', 'New hero pick')}
        </button>
      </div>

      {isLoading ? (
        <div className="text-center py-12 text-earth-600">
          {t('common.loading', 'Loading...')}
        </div>
      ) : error ? (
        <div className="text-center py-12 text-status-danger-600">
          {(error as Error).message}
        </div>
      ) : picks.length === 0 ? (
        <div className="text-center py-12 text-earth-600">
          {t('admin.adminHomePage.hero.empty', 'No hero picks yet. Create one to feature on the home page.')}
        </div>
      ) : (
        <ul className="space-y-2">
          {picks.map((p) => {
            const status = statusOf(p)
            return (
              <li
                key={p.id}
                className="flex items-center gap-3 p-3 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800"
              >
                <div className="w-8 h-12 bg-earth-200 dark:bg-earth-700 rounded flex items-center justify-center shrink-0">
                  <BookOpen className="w-4 h-4 text-earth-600" aria-hidden="true" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-lsc-dark dark:text-lsc-cream truncate">
                    {p.item.title}
                  </div>
                  <div className="text-xs text-earth-600 dark:text-earth-400 truncate">
                    {p.item.author ||
                      t('admin.adminHomePage.unknownAuthor', 'Unknown author')}
                    {' · '}
                    {new Date(p.active_from).toLocaleDateString()}
                    {p.active_to ? ` – ${new Date(p.active_to).toLocaleDateString()}` : ''}
                  </div>
                </div>
                <StatusPill status={status} />
                <button
                  onClick={() => setEditingId(p.id)}
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
                          'admin.adminHomePage.hero.confirmDelete',
                          'Delete this hero pick? This cannot be undone.'
                        )
                      )
                    ) {
                      deleteMutation.mutate(p.id)
                    }
                  }}
                  className="inline-flex items-center justify-center min-w-[44px] min-h-[44px] p-1.5 rounded hover:bg-status-danger-50 dark:hover:bg-status-danger-900/20 text-status-danger-400"
                  aria-label={t('common.delete', 'Delete')}
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}

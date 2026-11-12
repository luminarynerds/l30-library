/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useState, useCallback } from 'react'
import { BookOpen, Plus, Search, Edit3, X } from 'lucide-react'
import * as Sentry from "@/lib/sentry-lazy"
import toast from 'react-hot-toast'
import { AdminShell } from '../components/shells'
import {
  listSerialTitles,
  createSerialTitle,
  updateSerialTitle,
  type SerialTitle,
  type SerialTitleCreateData,
  type SerialTitleUpdateData,
} from '../api/domains/admin/serials-api'

import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

const FREQUENCIES = [
  'daily',
  'weekly',
  'biweekly',
  'monthly',
  'bimonthly',
  'quarterly',
  'semiannual',
  'annual',
  'irregular',
] as const

const PER_PAGE = 25

export default function SerialTitlesPage(): React.ReactElement {
  const [titles, setTitles] = useState<SerialTitle[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [activeFilter, setActiveFilter] = useState<'all' | 'active' | 'inactive'>('active')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [editing, setEditing] = useState<SerialTitle | null>(null)
  const [creating, setCreating] = useState(false)
  const [refreshKey, setRefreshKey] = useState(0)

  const refresh = useCallback(() => setRefreshKey((k) => k + 1), [])

  useEffect(() => {
    let cancelled = false
    // eslint-disable-next-line react-hooks/set-state-in-effect -- data-fetching effect
    setLoading(true)
    setError(null)
    listSerialTitles({
      page,
      per_page: PER_PAGE,
      ...(search ? { search } : {}),
      ...(activeFilter !== 'all' ? { is_active: activeFilter === 'active' } : {}),
    })
      .then((res) => {
        if (cancelled) return
        setTitles(res.items)
        setTotal(res.total)
      })
      .catch((e: unknown) => {
        Sentry.captureException(e instanceof Error ? e : new Error(String(e)))
        if (!cancelled) setError(e instanceof Error ? e.message : 'Failed to load titles')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [page, search, activeFilter, refreshKey])

  const totalPages = Math.max(1, Math.ceil(total / PER_PAGE))

  return (
    <AdminShell
      title="Serial Titles"
      subtitle={`${total} title${total === 1 ? '' : 's'}`}
      icon={<BookOpen className="w-7 h-7 text-lsc-rose" />}
      actions={
        <button
          onClick={() => setCreating(true)}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-lsc-rose text-white hover:bg-lsc-rose/90 transition-colors text-sm font-medium"
        >
          <Plus className="w-4 h-4" />
          New title
        </button>
      }
      error={error}
    >
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[240px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-lsc-dark/70" />
          <input
            type="text"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value)
              setPage(1)
            }}
            placeholder="Search by title or ISSN"
            className="w-full pl-10 pr-4 py-2 rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose/50"
          />
        </div>
        <select
          value={activeFilter}
          onChange={(e) => {
            setActiveFilter(e.target.value as typeof activeFilter)
            setPage(1)
          }}
          className="px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
        >
          <option value="active">Active only</option>
          <option value="inactive">Inactive only</option>
          <option value="all">All</option>
        </select>
      </div>

      <div className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-lsc-cream/30 dark:bg-earth-700/30">
              <tr className="border-b border-lsc-border dark:border-earth-700">
                <th className="px-4 py-3 text-left font-semibold text-lsc-dark dark:text-lsc-cream">Title</th>
                <th className="px-4 py-3 text-left font-semibold text-lsc-dark dark:text-lsc-cream">ISSN</th>
                <th className="px-4 py-3 text-left font-semibold text-lsc-dark dark:text-lsc-cream">Publisher</th>
                <th className="px-4 py-3 text-left font-semibold text-lsc-dark dark:text-lsc-cream">Frequency</th>
                <th className="px-4 py-3 text-left font-semibold text-lsc-dark dark:text-lsc-cream">Subs</th>
                <th className="px-4 py-3 text-left font-semibold text-lsc-dark dark:text-lsc-cream">Status</th>
                <th className="px-4 py-3 text-right font-semibold text-lsc-dark dark:text-lsc-cream">Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={7} className="px-4 py-12 text-center text-lsc-dark/70 dark:text-lsc-cream/60">
                    Loading...
                  </td>
                </tr>
              ) : titles.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-4 py-12 text-center text-lsc-dark/70 dark:text-lsc-cream/60">
                    No titles found.
                  </td>
                </tr>
              ) : (
                titles.map((title) => (
                  <tr
                    key={title.id}
                    className="border-b border-lsc-border/50 dark:border-earth-700/50 hover:bg-lsc-cream/20 dark:hover:bg-earth-700/20"
                  >
                    <td className="px-4 py-3 font-medium text-lsc-dark dark:text-lsc-cream">{title.title}</td>
                    <td className="px-4 py-3 text-lsc-dark/70 dark:text-lsc-cream/70 font-mono text-xs">
                      {title.issn_print || title.issn_electronic || '—'}
                    </td>
                    <td className="px-4 py-3 text-lsc-dark/70 dark:text-lsc-cream/70">
                      {title.publisher || '—'}
                    </td>
                    <td className="px-4 py-3 text-lsc-dark/70 dark:text-lsc-cream/70 capitalize">
                      {title.frequency}
                    </td>
                    <td className="px-4 py-3 text-lsc-dark/70 dark:text-lsc-cream/70 tabular-nums">
                      {title.active_subscription_count ?? 0}
                    </td>
                    <td className="px-4 py-3">
                      {title.is_active ? (
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full bg-status-success-100 dark:bg-status-success-900/30 text-status-success-800 dark:text-status-success-200 text-xs font-medium">
                          Active
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 text-xs font-medium">
                          Ceased
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        onClick={() => setEditing(title)}
                        className="inline-flex items-center gap-1 px-2 py-1 rounded text-lsc-rose hover:bg-lsc-rose/10 text-sm"
                      >
                        <Edit3 className="w-3 h-3" />
                        Edit
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {totalPages > 1 && (
          <div className="px-4 py-3 border-t border-lsc-border dark:border-earth-700 flex items-center justify-between text-sm">
            <span className="text-lsc-dark/70 dark:text-lsc-cream/70">
              Page {page} of {totalPages}
            </span>
            <div className="flex gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-3 py-1 rounded border border-lsc-border dark:border-earth-600 disabled:opacity-50 hover:bg-lsc-cream/30 dark:hover:bg-earth-700/30"
              >
                Previous
              </button>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="px-3 py-1 rounded border border-lsc-border dark:border-earth-600 disabled:opacity-50 hover:bg-lsc-cream/30 dark:hover:bg-earth-700/30"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>

      {creating && (
        <TitleFormModal
          mode="create"
          onClose={() => setCreating(false)}
          onSaved={() => {
            setCreating(false)
            refresh()
          }}
        />
      )}
      {editing && (
        <TitleFormModal
          mode="edit"
          title={editing}
          onClose={() => setEditing(null)}
          onSaved={() => {
            setEditing(null)
            refresh()
          }}
        />
      )}
    </AdminShell>
  )
}

interface ModalProps {
  mode: 'create' | 'edit'
  title?: SerialTitle
  onClose: () => void
  onSaved: () => void
}

function TitleFormModal({ mode, title, onClose, onSaved }: ModalProps): React.ReactElement {
  const [form, setForm] = useState({
    title: title?.title ?? '',
    issn_print: title?.issn_print ?? '',
    issn_electronic: title?.issn_electronic ?? '',
    publisher: title?.publisher ?? '',
    country_of_publication: title?.country_of_publication ?? '',
    language: title?.language ?? 'eng',
    frequency: title?.frequency ?? 'monthly',
    notes: title?.notes ?? '',
    is_active: title?.is_active ?? true,
  })
  const [saving, setSaving] = useState(false)

  const update = <K extends keyof typeof form>(key: K, value: (typeof form)[K]) => {
    setForm((f) => ({ ...f, [key]: value }))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.title.trim()) {
      toast.error('Title is required')
      return
    }
    setSaving(true)
    try {
      const payload = {
        title: form.title.trim(),
        issn_print: form.issn_print.trim() || null,
        issn_electronic: form.issn_electronic.trim() || null,
        publisher: form.publisher.trim() || null,
        country_of_publication: form.country_of_publication.trim() || null,
        language: form.language.trim() || null,
        frequency: form.frequency,
        notes: form.notes.trim() || null,
      }
      if (mode === 'create') {
        await createSerialTitle(payload as SerialTitleCreateData)
        toast.success('Title created')
      } else if (title) {
        await updateSerialTitle(title.id, { ...payload, is_active: form.is_active } as SerialTitleUpdateData)
        toast.success('Title updated')
      }
      onSaved()
    } catch (e: unknown) {
      Sentry.captureException(e instanceof Error ? e : new Error(String(e)))
      toast.error(e instanceof Error ? e.message : 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  return (
<ModalBackdrop onClose={onClose} title={mode === 'create' ? 'New Serial Title' : 'Edit Serial Title'}>
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className="px-6 py-4 border-b border-lsc-border dark:border-earth-700 flex items-center justify-between">
          <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
            {mode === 'create' ? 'New Serial Title' : `Edit: ${title?.title}`}
          </h2>
          <button
            onClick={onClose}
            className="p-1 rounded hover:bg-lsc-cream/30 dark:hover:bg-earth-700/30"
            aria-label="Close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <Field label="Title" required>
            <input
              type="text"
              value={form.title}
              onChange={(e) => update('title', e.target.value)}
              required
              className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
            />
          </Field>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Field label="ISSN (print)">
              <input
                type="text"
                value={form.issn_print}
                onChange={(e) => update('issn_print', e.target.value)}
                placeholder="0000-0000"
                className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream font-mono"
              />
            </Field>
            <Field label="ISSN (electronic)">
              <input
                type="text"
                value={form.issn_electronic}
                onChange={(e) => update('issn_electronic', e.target.value)}
                placeholder="0000-0000"
                className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream font-mono"
              />
            </Field>
          </div>
          <Field label="Publisher">
            <input
              type="text"
              value={form.publisher}
              onChange={(e) => update('publisher', e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
            />
          </Field>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Field label="Country">
              <input
                type="text"
                maxLength={3}
                value={form.country_of_publication}
                onChange={(e) => update('country_of_publication', e.target.value.toUpperCase())}
                placeholder="USA"
                className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream font-mono uppercase"
              />
            </Field>
            <Field label="Language">
              <input
                type="text"
                maxLength={10}
                value={form.language}
                onChange={(e) => update('language', e.target.value)}
                placeholder="eng"
                className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream font-mono"
              />
            </Field>
            <Field label="Frequency">
              <select
                value={form.frequency}
                onChange={(e) => update('frequency', e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream capitalize"
              >
                {FREQUENCIES.map((f) => (
                  <option key={f} value={f}>
                    {f}
                  </option>
                ))}
              </select>
            </Field>
          </div>
          <Field label="Notes">
            <textarea
              value={form.notes}
              onChange={(e) => update('notes', e.target.value)}
              rows={3}
              className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
            />
          </Field>
          {mode === 'edit' && (
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={form.is_active}
                onChange={(e) => update('is_active', e.target.checked)}
                className="w-4 h-4"
              />
              <span className="text-sm text-lsc-dark dark:text-lsc-cream">Active subscription</span>
            </label>
          )}
          <div className="flex justify-end gap-2 pt-4 border-t border-lsc-border dark:border-earth-700">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-600 hover:bg-lsc-cream/30 dark:hover:bg-earth-700/30 text-lsc-dark dark:text-lsc-cream"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="px-4 py-2 rounded-lg bg-lsc-rose text-white hover:bg-lsc-rose/90 disabled:opacity-50"
            >
              {saving ? 'Saving...' : mode === 'create' ? 'Create' : 'Save'}
            </button>
          </div>
        </form>
      </div>
    </ModalBackdrop>
  )
}

function Field({
  label,
  required,
  children,
}: {
  label: string
  required?: boolean
  children: React.ReactNode
}): React.ReactElement {
  return (
    <label className="block">
      <span className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
        {label}
        {required && <span className="text-status-danger-500 ml-0.5">*</span>}
      </span>
      {children}
    </label>
  )
}

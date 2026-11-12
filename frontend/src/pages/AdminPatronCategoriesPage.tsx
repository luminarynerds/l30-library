/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus, Pencil, Trash2, X, Eye, EyeOff } from 'lucide-react'
import { AdminShell } from '@/components/shells/AdminShell'
import {
  listPatronCategories,
  createPatronCategory,
  updatePatronCategory,
  removePatronCategory,
  type PatronCategory,
  type PatronCategoryCreatePayload,
  type PatronCategoryUpdatePayload,
} from '@/api/admin/patron-categories-api'

// ─── query key ───────────────────────────────────────────────────────────────

const QK = (includeInactive: boolean) =>
  ['patron-categories', { includeInactive }] as const

// ─── form types ──────────────────────────────────────────────────────────────

interface FormState {
  code: string
  label: string
  is_active: boolean
}

const EMPTY_FORM: FormState = { code: '', label: '', is_active: true }

function toForm(cat: PatronCategory): FormState {
  return { code: cat.code, label: cat.label, is_active: cat.is_active }
}

// ─── page ─────────────────────────────────────────────────────────────────────

export default function AdminPatronCategoriesPage(): React.ReactElement {
  const [includeInactive, setIncludeInactive] = useState(false)
  const [editing, setEditing] = useState<PatronCategory | null>(null)
  const [creating, setCreating] = useState(false)
  const [notice, setNotice] = useState<string | null>(null)

  const qc = useQueryClient()
  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ['patron-categories'] })
  }

  const { data: categories, isLoading, error } = useQuery({
    queryKey: QK(includeInactive),
    queryFn: () => listPatronCategories(includeInactive),
    staleTime: 30_000,
  })

  const createMut = useMutation({
    mutationFn: createPatronCategory,
    onSuccess: () => {
      invalidate()
      setCreating(false)
      setNotice('Category created')
    },
  })

  const updateMut = useMutation({
    mutationFn: (vars: { id: number; payload: PatronCategoryUpdatePayload }) =>
      updatePatronCategory(vars.id, vars.payload),
    onSuccess: () => {
      invalidate()
      setEditing(null)
      setNotice('Category updated')
    },
  })

  const deleteMut = useMutation({
    mutationFn: removePatronCategory,
    onSuccess: () => {
      invalidate()
      setNotice('Category deactivated')
    },
  })

  const handleDelete = (cat: PatronCategory) => {
    if (!window.confirm(`Deactivate "${cat.label}"?`)) return
    deleteMut.mutate(cat.id)
  }

  const mutationError =
    (createMut.error as Error | null)?.message ||
    (updateMut.error as Error | null)?.message ||
    (deleteMut.error as Error | null)?.message ||
    null

  return (
    <AdminShell
      title="Patron categories"
      subtitle="Canonical patron type codes used for circulation policy and reporting"
      loading={isLoading}
      error={error ? String(error) : null}
      actions={
        <div className="flex items-center gap-2">
          <label className="flex items-center gap-1.5 text-sm text-lsc-dark dark:text-lsc-cream cursor-pointer select-none">
            <input
              type="checkbox"
              checked={includeInactive}
              onChange={(e) => setIncludeInactive(e.target.checked)}
              className="w-4 h-4"
            />
            Show inactive
          </label>
          <button
            onClick={() => setCreating(true)}
            className="inline-flex items-center gap-1 px-3 py-2 bg-lsc-rose text-white text-sm font-medium rounded-lg hover:bg-lsc-rose/90"
          >
            <Plus className="w-4 h-4" aria-hidden="true" /> Add patron category
          </button>
        </div>
      }
    >
      {notice && (
        <div role="status" aria-live="polite" className="mb-4 text-sm text-status-success-700 dark:text-status-success-200 bg-status-success-100 dark:bg-status-success-900 px-3 py-2 rounded">
          {notice}
        </div>
      )}
      {mutationError && (
        <div role="alert" className="mb-4 text-sm text-status-danger-700 dark:text-status-danger-200 bg-status-danger-100 dark:bg-status-danger-900 px-3 py-2 rounded">
          {mutationError}
        </div>
      )}

      <div className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-lsc-cream/40 dark:bg-earth-900 text-left text-xs uppercase tracking-wide text-lsc-dark/60 dark:text-lsc-cream/60">
            <tr>
              <th className="px-3 py-2">Code</th>
              <th className="px-3 py-2">Label</th>
              <th className="px-3 py-2 w-28">Active</th>
              <th className="px-3 py-2 w-32 text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {(categories ?? []).map((cat) => (
              <tr
                key={cat.id}
                className="border-t border-lsc-border dark:border-earth-700"
              >
                <td className="px-3 py-2 font-mono text-lsc-dark dark:text-lsc-cream">
                  {cat.code}
                </td>
                <td className="px-3 py-2 text-lsc-dark dark:text-lsc-cream">{cat.label}</td>
                <td className="px-3 py-2">
                  {cat.is_active ? (
                    <span className="inline-flex items-center gap-1 text-status-success-700 dark:text-status-success-200 text-xs">
                      <Eye className="w-3.5 h-3.5" aria-hidden="true" /> Active
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 text-lsc-dark/50 dark:text-lsc-cream/50 text-xs">
                      <EyeOff className="w-3.5 h-3.5" aria-hidden="true" /> Inactive
                    </span>
                  )}
                </td>
                <td className="px-3 py-2 text-right">
                  <button
                    onClick={() => setEditing(cat)}
                    className="inline-flex items-center gap-1 px-2 py-1 text-xs rounded hover:bg-lsc-cream dark:hover:bg-earth-700"
                    aria-label={`Edit ${cat.label}`}
                  >
                    <Pencil className="w-3.5 h-3.5" aria-hidden="true" /> Edit
                  </button>
                  <button
                    onClick={() => handleDelete(cat)}
                    disabled={deleteMut.isPending}
                    className="ml-1 inline-flex items-center gap-1 px-2 py-1 text-xs rounded text-status-danger-700 dark:text-status-danger-200 hover:bg-status-danger-100 dark:hover:bg-status-danger-900 disabled:opacity-50"
                    aria-label={`Deactivate ${cat.label}`}
                  >
                    <Trash2 className="w-3.5 h-3.5" aria-hidden="true" /> Delete
                  </button>
                </td>
              </tr>
            ))}
            {categories && categories.length === 0 && (
              <tr>
                <td
                  colSpan={4}
                  className="px-3 py-8 text-center text-lsc-dark/60 dark:text-lsc-cream/60 text-sm"
                >
                  No patron categories found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {(creating || editing) && (
        <EditModal
          initial={editing ? toForm(editing) : EMPTY_FORM}
          title={editing ? `Edit "${editing.label}"` : 'Add patron category'}
          pending={createMut.isPending || updateMut.isPending}
          onClose={() => {
            setCreating(false)
            setEditing(null)
          }}
          onSave={(f) => {
            if (editing) {
              updateMut.mutate({ id: editing.id, payload: f })
            } else {
              createMut.mutate(f as PatronCategoryCreatePayload)
            }
          }}
        />
      )}
    </AdminShell>
  )
}

// ─── modal ───────────────────────────────────────────────────────────────────

interface EditModalProps {
  initial: FormState
  title: string
  pending: boolean
  onClose: () => void
  onSave: (f: FormState) => void
}

function EditModal({ initial, title, pending, onClose, onSave }: EditModalProps) {
  const [form, setForm] = useState<FormState>(initial)

  const canSubmit = form.code.trim() && form.label.trim()

  // Close on Escape
  const handleKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if (e.key === 'Escape') onClose()
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="patron-cat-modal-title"
      className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4"
      onKeyDown={handleKeyDown}
    >
      <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-lg w-full max-w-md">
        <div className="flex items-center justify-between px-5 py-3 border-b border-lsc-border dark:border-earth-700">
          <h2
            id="patron-cat-modal-title"
            className="text-base font-semibold text-lsc-dark dark:text-lsc-cream"
          >
            {title}
          </h2>
          <button
            onClick={onClose}
            aria-label="Close"
            className="text-lsc-dark/60 dark:text-lsc-cream/60 hover:text-lsc-dark dark:hover:text-lsc-cream"
          >
            <X className="w-5 h-5" aria-hidden="true" />
          </button>
        </div>

        <div className="p-5 space-y-4">
          <div>
            <label
              htmlFor="patron-cat-code"
              className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1"
            >
              Code
            </label>
            <input
              id="patron-cat-code"
              type="text"
              value={form.code}
              onChange={(e) => setForm({ ...form, code: e.target.value })}
              placeholder="ADULT"
              className="w-full px-3 py-2 text-sm font-mono bg-lsc-cream/30 dark:bg-earth-900 border border-lsc-border dark:border-earth-700 rounded focus:outline-none focus:ring-2 focus:ring-lsc-rose"
              maxLength={30}
              autoFocus
            />
          </div>

          <div>
            <label
              htmlFor="patron-cat-label"
              className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1"
            >
              Label
            </label>
            <input
              id="patron-cat-label"
              type="text"
              value={form.label}
              onChange={(e) => setForm({ ...form, label: e.target.value })}
              placeholder="Adult"
              className="w-full px-3 py-2 text-sm bg-lsc-cream/30 dark:bg-earth-900 border border-lsc-border dark:border-earth-700 rounded focus:outline-none focus:ring-2 focus:ring-lsc-rose"
              maxLength={100}
            />
          </div>

          <label className="flex items-center gap-2 text-sm text-lsc-dark dark:text-lsc-cream">
            <input
              type="checkbox"
              checked={form.is_active}
              onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
              className="w-4 h-4"
            />
            Active
          </label>
        </div>

        <div className="flex items-center justify-end gap-2 px-5 py-3 border-t border-lsc-border dark:border-earth-700">
          <button
            onClick={onClose}
            className="px-3 py-2 text-sm text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-700 rounded"
          >
            Cancel
          </button>
          <button
            onClick={() => onSave(form)}
            disabled={!canSubmit || pending}
            className="px-3 py-2 text-sm bg-lsc-rose text-white rounded hover:bg-lsc-rose/90 disabled:opacity-50"
          >
            {pending ? 'Saving...' : 'Save'}
          </button>
        </div>
      </div>
    </div>
  )
}

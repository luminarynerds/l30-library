/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useMemo, useState } from 'react'
import { Modal } from '@/components/ui/Modal'
import {
  BOOK_BINDINGS,
  CIRCULATION_POLICY_ITEM_TYPES,
  CIRCULATION_POLICY_ROLES,
  bindingLabel,
  itemTypeLabel,
  roleLabel,
  type BookBinding,
  type CirculationPolicyCreate,
  type CirculationPolicyResponse,
  type CirculationPolicyRole,
  type CirculationPolicyUpdate,
} from '@/api/domains/admin/circulation-policy-api'
import type { ItemType } from '@/api/domains/catalog/catalog-api'

export type PolicyMode = 'format' | 'audience'

interface EditCirculationPolicyModalProps {
  isOpen: boolean
  librarySystemId: number
  initial?: CirculationPolicyResponse | null
  saving?: boolean
  onClose: () => void
  onSave: (mode: 'create' | 'update', payload: CirculationPolicyCreate | CirculationPolicyUpdate) => Promise<void> | void
}

interface FormState {
  mode: PolicyMode
  role: CirculationPolicyRole | ''
  item_type: ItemType | ''
  binding: BookBinding | ''
  collection_id: string  // string in UI; parsed on submit
  loan_period_days: string
  max_renewals: string
  overdue_fine_per_day: string
  max_fine: string
  grace_period_days: string
  hold_pickup_days: string
  fine_free: boolean | null  // null = inherit
  active: boolean
  notes: string
}

const EMPTY_FORM: FormState = {
  mode: 'format',
  role: '',
  item_type: '',
  binding: '',
  collection_id: '',
  loan_period_days: '',
  max_renewals: '',
  overdue_fine_per_day: '',
  max_fine: '',
  grace_period_days: '',
  hold_pickup_days: '',
  fine_free: null,
  active: true,
  notes: '',
}

function modeFromPolicy(p: CirculationPolicyResponse): PolicyMode {
  return p.role !== null || p.collection_id !== null ? 'audience' : 'format'
}

function policyToForm(p: CirculationPolicyResponse): FormState {
  return {
    mode: modeFromPolicy(p),
    role: p.role ?? '',
    item_type: p.item_type ?? '',
    binding: p.binding ?? '',
    collection_id: p.collection_id !== null ? String(p.collection_id) : '',
    loan_period_days: p.loan_period_days !== null ? String(p.loan_period_days) : '',
    max_renewals: p.max_renewals !== null ? String(p.max_renewals) : '',
    overdue_fine_per_day: p.overdue_fine_per_day ?? '',
    max_fine: p.max_fine ?? '',
    grace_period_days: p.grace_period_days !== null ? String(p.grace_period_days) : '',
    hold_pickup_days: p.hold_pickup_days !== null ? String(p.hold_pickup_days) : '',
    fine_free: p.fine_free,
    active: p.active,
    notes: p.notes ?? '',
  }
}

function intOrNull(v: string): number | null {
  if (v.trim() === '') return null
  const n = parseInt(v, 10)
  return Number.isNaN(n) ? null : n
}

function decOrNull(v: string): string | null {
  if (v.trim() === '') return null
  const n = parseFloat(v)
  if (Number.isNaN(n)) return null
  return v.trim()
}

interface ValidationResult {
  ok: boolean
  error?: string
}

function validate(form: FormState): ValidationResult {
  // At least one knob must be set.
  const knobsSet =
    form.loan_period_days.trim() !== '' ||
    form.max_renewals.trim() !== '' ||
    form.overdue_fine_per_day.trim() !== '' ||
    form.max_fine.trim() !== '' ||
    form.grace_period_days.trim() !== '' ||
    form.hold_pickup_days.trim() !== '' ||
    form.fine_free !== null
  if (!knobsSet) {
    return { ok: false, error: 'Set at least one circulation knob (loan period, fine, etc.). An empty override is meaningless.' }
  }
  // binding requires item_type=book or null
  if (form.binding !== '' && form.item_type !== '' && form.item_type !== 'book') {
    return { ok: false, error: 'Binding only applies when item type is "book" or left blank (any type).' }
  }
  // collection_id must parse if provided
  if (form.collection_id.trim() !== '') {
    const n = parseInt(form.collection_id, 10)
    if (Number.isNaN(n) || n <= 0) {
      return { ok: false, error: 'Collection ID must be a positive integer.' }
    }
  }
  return { ok: true }
}

export function EditCirculationPolicyModal({
  isOpen,
  librarySystemId,
  initial,
  saving = false,
  onClose,
  onSave,
}: EditCirculationPolicyModalProps) {
  const [form, setForm] = useState<FormState>(() => (initial ? policyToForm(initial) : EMPTY_FORM))
  const [error, setError] = useState<string | null>(null)

  // Reset form when the modal opens for a different policy (or transitions closed -> open).
  // Storing prior open/initial-id and resetting during render avoids cascading effects.
  const initialKey = isOpen ? (initial?.id ?? 'new') : 'closed'
  const [lastKey, setLastKey] = useState<string | number>(initialKey)
  if (lastKey !== initialKey) {
    setLastKey(initialKey)
    setForm(initial ? policyToForm(initial) : EMPTY_FORM)
    setError(null)
  }

  const isEdit = !!initial
  const isFormatMode = form.mode === 'format'

  const validation = useMemo(() => validate(form), [form])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!validation.ok) {
      setError(validation.error || 'Invalid form state.')
      return
    }
    setError(null)

    // In format mode, role and collection are forced to null.
    const role: CirculationPolicyRole | null =
      isFormatMode ? null : form.role === '' ? null : form.role
    const collection_id: number | null =
      isFormatMode ? null : intOrNull(form.collection_id)
    const item_type: ItemType | null = form.item_type === '' ? null : form.item_type
    const binding: BookBinding | null = form.binding === '' ? null : form.binding

    const payload: CirculationPolicyCreate | CirculationPolicyUpdate = {
      role,
      item_type,
      binding,
      collection_id,
      loan_period_days: intOrNull(form.loan_period_days),
      max_renewals: intOrNull(form.max_renewals),
      overdue_fine_per_day: decOrNull(form.overdue_fine_per_day),
      max_fine: decOrNull(form.max_fine),
      grace_period_days: intOrNull(form.grace_period_days),
      hold_pickup_days: intOrNull(form.hold_pickup_days),
      fine_free: form.fine_free,
      active: form.active,
      notes: form.notes.trim() === '' ? null : form.notes.trim(),
    }

    try {
      if (isEdit) {
        await onSave('update', payload)
      } else {
        await onSave('create', { ...payload, library_system_id: librarySystemId } as CirculationPolicyCreate)
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Save failed.'
      setError(message)
    }
  }

  const inputCls =
    'w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose/50'
  const labelCls = 'block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1'

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={isEdit ? 'Edit circulation policy' : 'Add circulation policy'}
      size="2xl"
      dismissible={!saving}
    >
      <form onSubmit={handleSubmit} className="space-y-5">
        {/* Mode selector */}
        <fieldset>
          <legend className="text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">Scope mode</legend>
          <div className="flex flex-col sm:flex-row gap-2">
            <label className={`flex-1 flex items-start gap-3 p-3 border rounded-lg cursor-pointer ${isFormatMode ? 'border-lsc-rose bg-lsc-rose/5' : 'border-lsc-border dark:border-earth-700'}`}>
              <input
                type="radio"
                name="policy-mode"
                value="format"
                checked={isFormatMode}
                onChange={() => setForm({ ...form, mode: 'format', role: '', collection_id: '' })}
                className="mt-1"
              />
              <span>
                <span className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream">Format default</span>
                <span className="block text-xs text-lsc-dark/60 dark:text-lsc-cream/60">Applies to all patrons. Set by item type and/or binding.</span>
              </span>
            </label>
            <label className={`flex-1 flex items-start gap-3 p-3 border rounded-lg cursor-pointer ${!isFormatMode ? 'border-lsc-rose bg-lsc-rose/5' : 'border-lsc-border dark:border-earth-700'}`}>
              <input
                type="radio"
                name="policy-mode"
                value="audience"
                checked={!isFormatMode}
                onChange={() => setForm({ ...form, mode: 'audience' })}
                className="mt-1"
              />
              <span>
                <span className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream">Audience override</span>
                <span className="block text-xs text-lsc-dark/60 dark:text-lsc-cream/60">Targets a role and/or collection in addition to format.</span>
              </span>
            </label>
          </div>
        </fieldset>

        {/* Scope axes */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label htmlFor="cp-role" className={labelCls}>Role {isFormatMode && <span className="text-xs text-lsc-dark/50 dark:text-lsc-cream/50">(locked)</span>}</label>
            <select
              id="cp-role"
              className={inputCls}
              value={form.role}
              disabled={isFormatMode}
              onChange={(e) => setForm({ ...form, role: e.target.value as CirculationPolicyRole | '' })}
            >
              <option value="">— Any role —</option>
              {CIRCULATION_POLICY_ROLES.map((r) => (
                <option key={r} value={r}>{roleLabel(r)}</option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="cp-item-type" className={labelCls}>Item type</label>
            <select
              id="cp-item-type"
              className={inputCls}
              value={form.item_type}
              onChange={(e) => {
                const next = e.target.value as ItemType | ''
                // Clear binding if item_type changes to non-book.
                setForm({
                  ...form,
                  item_type: next,
                  binding: next !== '' && next !== 'book' ? '' : form.binding,
                })
              }}
            >
              <option value="">— Any item type —</option>
              {CIRCULATION_POLICY_ITEM_TYPES.map((t) => (
                <option key={t} value={t}>{itemTypeLabel(t)}</option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="cp-binding" className={labelCls}>
              Binding{' '}
              <span className="text-xs text-lsc-dark/50 dark:text-lsc-cream/50">(books only)</span>
            </label>
            <select
              id="cp-binding"
              className={inputCls}
              value={form.binding}
              disabled={form.item_type !== '' && form.item_type !== 'book'}
              onChange={(e) => setForm({ ...form, binding: e.target.value as BookBinding | '' })}
            >
              <option value="">— Any binding —</option>
              {BOOK_BINDINGS.map((b) => (
                <option key={b} value={b}>{bindingLabel(b)}</option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="cp-collection" className={labelCls}>Collection ID {isFormatMode && <span className="text-xs text-lsc-dark/50 dark:text-lsc-cream/50">(locked)</span>}</label>
            <input
              id="cp-collection"
              type="number"
              min="1"
              className={inputCls}
              value={form.collection_id}
              disabled={isFormatMode}
              placeholder="e.g. 42"
              onChange={(e) => setForm({ ...form, collection_id: e.target.value })}
            />
          </div>
        </div>

        {/* Knobs */}
        <div className="bg-lsc-cream/40 dark:bg-earth-900/40 border border-lsc-border dark:border-earth-700 rounded-lg p-4 space-y-3">
          <p className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60">Leave a field blank to inherit from the next-broader policy. At least one must be set.</p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label htmlFor="cp-loan" className={labelCls}>Loan period (days)</label>
              <input id="cp-loan" type="number" min="0" className={inputCls} value={form.loan_period_days} onChange={(e) => setForm({ ...form, loan_period_days: e.target.value })} />
            </div>
            <div>
              <label htmlFor="cp-renewals" className={labelCls}>Max renewals</label>
              <input id="cp-renewals" type="number" min="0" className={inputCls} value={form.max_renewals} onChange={(e) => setForm({ ...form, max_renewals: e.target.value })} />
            </div>
            <div>
              <label htmlFor="cp-fine-day" className={labelCls}>Overdue fine / day ($)</label>
              <input id="cp-fine-day" type="number" min="0" step="0.01" className={inputCls} value={form.overdue_fine_per_day} onChange={(e) => setForm({ ...form, overdue_fine_per_day: e.target.value })} />
            </div>
            <div>
              <label htmlFor="cp-max-fine" className={labelCls}>Max fine ($)</label>
              <input id="cp-max-fine" type="number" min="0" step="0.01" className={inputCls} value={form.max_fine} onChange={(e) => setForm({ ...form, max_fine: e.target.value })} />
            </div>
            <div>
              <label htmlFor="cp-grace" className={labelCls}>Grace period (days)</label>
              <input id="cp-grace" type="number" min="0" className={inputCls} value={form.grace_period_days} onChange={(e) => setForm({ ...form, grace_period_days: e.target.value })} />
            </div>
            <div>
              <label htmlFor="cp-hold" className={labelCls}>Hold pickup days</label>
              <input id="cp-hold" type="number" min="0" className={inputCls} value={form.hold_pickup_days} onChange={(e) => setForm({ ...form, hold_pickup_days: e.target.value })} />
            </div>
          </div>
          <div>
            <label htmlFor="cp-fine-free" className={labelCls}>Fine-free</label>
            <select
              id="cp-fine-free"
              className={inputCls}
              value={form.fine_free === null ? '' : form.fine_free ? 'true' : 'false'}
              onChange={(e) => {
                const v = e.target.value
                setForm({ ...form, fine_free: v === '' ? null : v === 'true' })
              }}
            >
              <option value="">— Inherit —</option>
              <option value="true">Yes (no fines)</option>
              <option value="false">No (fines apply)</option>
            </select>
          </div>
        </div>

        {/* Active + notes */}
        <div className="flex items-center gap-3">
          <button
            type="button"
            role="switch"
            aria-checked={form.active}
            aria-label="Policy active"
            onClick={() => setForm({ ...form, active: !form.active })}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-lsc-rose/50 ${form.active ? 'bg-lsc-rose' : 'bg-earth-200 dark:bg-earth-700'}`}
          >
            <span className={`inline-block h-4 w-4 transform rounded-full bg-lsc-white dark:bg-earth-800 transition-transform ${form.active ? 'translate-x-6' : 'translate-x-1'}`} />
          </button>
          <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Active (inactive policies are not applied)</span>
        </div>

        <div>
          <label htmlFor="cp-notes" className={labelCls}>Notes (staff-visible)</label>
          <textarea
            id="cp-notes"
            rows={2}
            className={inputCls}
            value={form.notes}
            onChange={(e) => setForm({ ...form, notes: e.target.value })}
            placeholder="Why does this rule exist? Optional."
          />
        </div>

        {error && (
          <div role="alert" className="bg-status-warning-50 dark:bg-status-warning-900/20 border border-status-warning-200 dark:border-status-warning-800 rounded-lg p-3 text-sm text-status-warning-800 dark:text-status-warning-200">
            {error}
          </div>
        )}

        <div className="flex justify-end gap-2 pt-2">
          <button
            type="button"
            onClick={onClose}
            disabled={saving}
            className="px-4 py-2 text-sm font-medium text-lsc-dark dark:text-lsc-cream border border-lsc-border dark:border-earth-700 rounded-lg hover:bg-lsc-cream dark:hover:bg-earth-700 focus:outline-none focus:ring-2 focus:ring-lsc-rose/50 disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={saving || !validation.ok}
            className="px-4 py-2 text-sm font-semibold text-white bg-lsc-rose rounded-lg hover:bg-lsc-rose/90 focus:outline-none focus:ring-2 focus:ring-lsc-rose/50 disabled:opacity-50"
          >
            {saving ? 'Saving...' : isEdit ? 'Save changes' : 'Create policy'}
          </button>
        </div>
      </form>
    </Modal>
  )
}

export default EditCirculationPolicyModal

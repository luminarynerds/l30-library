/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { XCircle, Loader2 } from 'lucide-react'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'
import { ROLE_CATEGORY_LABELS } from '@/api/domains/admin/volunteer-api'
import type { StaffShift, ShiftCreateData, ShiftUpdateData } from '@/api/domains/admin/volunteer-api'

const ROLE_CATEGORY_OPTIONS = Object.entries(ROLE_CATEGORY_LABELS)

interface ShiftFormModalProps<T extends ShiftCreateData | ShiftUpdateData = ShiftCreateData> {
  onClose: () => void
  onSave: (data: T) => void
  saving: boolean
  initial?: StaffShift
}

export function ShiftFormModal<T extends ShiftCreateData | ShiftUpdateData = ShiftCreateData>({
  onClose,
  onSave,
  saving,
  initial,
}: ShiftFormModalProps<T>) {
  const isEdit = Boolean(initial)
  const [form, setForm] = useState({
    title: initial?.title ?? '',
    role_category: initial?.role_category ?? '',
    shift_date: initial?.shift_date ?? '',
    start_time: initial?.start_time ?? '',
    end_time: initial?.end_time ?? '',
    // Not returned by the staff shift list, so it can only be set on create.
    duration_hours: '' as number | '',
    description: initial?.description ?? '',
    location: initial?.location ?? '',
    volunteers_needed: initial?.volunteers_needed ?? 1,
  })

  const titleText = isEdit ? 'Edit Shift' : 'New Shift'

  const isValid =
    form.title.trim() !== '' &&
    form.role_category !== '' &&
    form.shift_date !== '' &&
    form.start_time !== '' &&
    form.end_time !== '' &&
    form.volunteers_needed >= 1 &&
    (isEdit || Number(form.duration_hours) > 0)

  const handleSave = () => {
    const base = {
      title: form.title.trim(),
      role_category: form.role_category,
      shift_date: form.shift_date,
      start_time: form.start_time,
      end_time: form.end_time,
      description: form.description.trim() || undefined,
      location: form.location.trim() || undefined,
      volunteers_needed: form.volunteers_needed,
    }
    // The generic T is fixed per call site (create vs. edit never share an
    // instance), so this is the one place that has to assert it -- the
    // isEdit branch below is what actually keeps the two shapes honest.
    if (isEdit) {
      onSave(base as T)
    } else {
      onSave({ ...base, duration_hours: Number(form.duration_hours) } as T)
    }
  }

  return (
    <ModalBackdrop onClose={onClose} title={titleText}>
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-6 border-b border-lsc-border dark:border-earth-700">
          <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-earth-50">{titleText}</h2>
          <button
            onClick={onClose}
            aria-label="Close shift form"
            className="p-2 hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-lg"
          >
            <XCircle className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
          </button>
        </div>
        <div className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-earth-50 mb-1">Title *</label>
            <input
              type="text"
              aria-label="Shift title"
              value={form.title}
              onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-earth-50"
              placeholder="e.g. Saturday Shelving"
            />
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-lsc-dark dark:text-earth-50 mb-1">Role Category *</label>
              <select
                aria-label="Role category"
                value={form.role_category}
                onChange={e => setForm(f => ({ ...f, role_category: e.target.value }))}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-earth-50"
              >
                <option value="">Select category...</option>
                {ROLE_CATEGORY_OPTIONS.map(([value, label]) => (
                  <option key={value} value={value}>{label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-lsc-dark dark:text-earth-50 mb-1">Volunteers Needed</label>
              <input
                type="number"
                aria-label="Volunteers needed"
                value={form.volunteers_needed}
                onChange={e => setForm(f => ({ ...f, volunteers_needed: Number(e.target.value) }))}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-earth-50"
                min={1}
              />
              {form.volunteers_needed < 1 && (
                <p className="text-sm text-status-danger-600 dark:text-status-danger-400 mt-1">Needs at least 1 volunteer.</p>
              )}
            </div>
          </div>
          <div className={`grid grid-cols-1 gap-4 ${isEdit ? 'sm:grid-cols-2' : 'sm:grid-cols-3'}`}>
            <div>
              <label className="block text-sm font-medium text-lsc-dark dark:text-earth-50 mb-1">Date *</label>
              <input
                type="date"
                aria-label="Shift date"
                value={form.shift_date}
                onChange={e => setForm(f => ({ ...f, shift_date: e.target.value }))}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-earth-50"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-lsc-dark dark:text-earth-50 mb-1">Start Time *</label>
              <input
                type="time"
                aria-label="Start time"
                value={form.start_time}
                onChange={e => setForm(f => ({ ...f, start_time: e.target.value }))}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-earth-50"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-lsc-dark dark:text-earth-50 mb-1">End Time *</label>
              <input
                type="time"
                aria-label="End time"
                value={form.end_time}
                onChange={e => setForm(f => ({ ...f, end_time: e.target.value }))}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-earth-50"
              />
            </div>
          </div>
          {isEdit ? (
            <p className="text-sm text-lsc-dark/70 dark:text-earth-50/70">
              Duration is set when the shift is created.
            </p>
          ) : (
            <div>
              <label className="block text-sm font-medium text-lsc-dark dark:text-earth-50 mb-1">Duration (hours) *</label>
              <input
                type="number"
                step="0.25"
                aria-label="Duration in hours"
                value={form.duration_hours}
                onChange={e => setForm(f => ({ ...f, duration_hours: e.target.value === '' ? '' : Number(e.target.value) }))}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-earth-50"
                min={0.25}
              />
              {form.duration_hours !== '' && Number(form.duration_hours) <= 0 && (
                <p className="text-sm text-status-danger-600 dark:text-status-danger-400 mt-1">Duration must be greater than 0.</p>
              )}
            </div>
          )}
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-earth-50 mb-1">Location</label>
            <input
              type="text"
              aria-label="Location"
              value={form.location}
              onChange={e => setForm(f => ({ ...f, location: e.target.value }))}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-earth-50"
              placeholder="e.g. Main Library"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-earth-50 mb-1">Description</label>
            <textarea
              aria-label="Description"
              value={form.description}
              onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
              rows={3}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-earth-50"
              placeholder="What will volunteers be doing?"
            />
          </div>
        </div>
        <div className="flex justify-end gap-3 p-6 border-t border-lsc-border dark:border-earth-700">
          <button onClick={onClose} className="px-4 py-2 border border-lsc-border dark:border-earth-700 rounded-lg text-lsc-dark dark:text-earth-50 hover:bg-lsc-cream dark:hover:bg-earth-700 text-sm">
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving || !isValid}
            className="px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 text-sm font-medium disabled:opacity-50 flex items-center gap-2"
          >
            {saving && <Loader2 className="w-4 h-4 motion-safe:animate-spin" />}
            {isEdit ? 'Save Changes' : 'Create Shift'}
          </button>
        </div>
      </div>
    </ModalBackdrop>
  )
}

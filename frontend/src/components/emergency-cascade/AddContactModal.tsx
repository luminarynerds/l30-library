/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Users, X, Plus, Loader2 } from "lucide-react"
import { useTranslation } from "@/i18n"
import type { CascadeData, ContactFormState } from "./types"
import { CONTACT_METHODS } from "./types"
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

interface Props {
  cascade: CascadeData
  form: ContactFormState
  isSaving: boolean
  onChange: (form: ContactFormState) => void
  onCancel: () => void
  onSubmit: () => void
}

export function AddContactModal({ cascade, form, isSaving, onChange, onCancel, onSubmit }: Props): React.ReactElement {
  const { t } = useTranslation()

  return (
    <ModalBackdrop onClose={onCancel} title="Add Contact to Cascade">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-lg max-w-lg w-full mx-4 p-6 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-2xl font-serif font-bold flex items-center gap-2">
            <Users className="w-6 h-6 text-category-600" />
            Add Contact to Cascade
          </h2>
          <button onClick={onCancel}>
            <X className="w-6 h-6" />
          </button>
        </div>

        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block font-semibold mb-2">Level *</label>
              <input
                type="number"
                min="1"
                max={cascade.max_contact_levels}
                value={form.level}
                onChange={(e) => onChange({ ...form, level: parseInt(e.target.value) })}
                className="w-full p-2 border-2 border-lsc-border dark:border-earth-700 rounded-lg focus:border-category-500 outline-none"
              />
            </div>

            <div>
              <label className="block font-semibold mb-2">Contact Method</label>
              <select
                value={form.contact_method}
                onChange={(e) => onChange({ ...form, contact_method: e.target.value })}
                className="w-full p-2 border-2 border-lsc-border dark:border-earth-700 rounded-lg focus:border-category-500 outline-none"
              >
                {CONTACT_METHODS.map((method) => (
                  <option key={method.id} value={method.id}>
                    {method.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label className="block font-semibold mb-2">Role *</label>
            <input
              type="text"
              value={form.contact_role}
              onChange={(e) => onChange({ ...form, contact_role: e.target.value })}
              placeholder={t('placeholder.emergencyOperationsCascade.egLibraryDirectorEmergency')}
              className="w-full p-3 border-2 border-lsc-border dark:border-earth-700 rounded-lg focus:border-category-500 outline-none"
            />
          </div>

          <div>
            <label className="block font-semibold mb-2">Name *</label>
            <input
              type="text"
              value={form.contact_name}
              onChange={(e) => onChange({ ...form, contact_name: e.target.value })}
              placeholder={t('placeholder.guestPassForm.fullName')}
              className="w-full p-3 border-2 border-lsc-border dark:border-earth-700 rounded-lg focus:border-category-500 outline-none"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block font-semibold mb-2">Email</label>
              <input
                type="email"
                value={form.contact_email}
                onChange={(e) => onChange({ ...form, contact_email: e.target.value })}
                placeholder={t('placeholder.guestPassForm.emailexamplecom')}
                className="w-full p-2 border-2 border-lsc-border dark:border-earth-700 rounded-lg focus:border-category-500 outline-none"
              />
            </div>

            <div>
              <label className="block font-semibold mb-2">Phone</label>
              <input
                type="tel"
                value={form.contact_phone}
                onChange={(e) => onChange({ ...form, contact_phone: e.target.value })}
                className="w-full p-2 border-2 border-lsc-border dark:border-earth-700 rounded-lg focus:border-category-500 outline-none"
              />
            </div>
          </div>

          <div className="flex gap-3 mt-6">
            <button
              onClick={onCancel}
              disabled={isSaving}
              className="flex-1 px-4 py-2 border-2 border-lsc-border dark:border-earth-700 rounded-lg hover:bg-earth-50 dark:bg-earth-900 dark:hover:bg-earth-800 font-semibold disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              onClick={onSubmit}
              disabled={isSaving}
              className="flex-1 px-4 py-2 bg-category-600 text-white rounded-lg hover:bg-category-700 font-semibold disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {isSaving ? <Loader2 className="w-4 h-4 motion-safe:animate-spin" /> : <Plus className="w-4 h-4" />}
              Add Contact
            </button>
          </div>
        </div>
      </div>
    </ModalBackdrop>
  )
}

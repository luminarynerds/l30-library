/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Phone, X, Plus, Loader2 } from "lucide-react"
import { useTranslation } from "@/i18n"
import type { CascadeFormState } from "./types"
import { TRIGGER_EVENTS } from "./types"
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

interface Props {
  form: CascadeFormState
  isSaving: boolean
  onChange: (form: CascadeFormState) => void
  onCancel: () => void
  onSubmit: () => void
}

export function CreateCascadeModal({ form, isSaving, onChange, onCancel, onSubmit }: Props): React.ReactElement {
  const { t } = useTranslation()

  const toggleTriggerEvent = (eventId: string, checked: boolean) => {
    onChange({
      ...form,
      auto_trigger_events: checked
        ? [...form.auto_trigger_events, eventId]
        : form.auto_trigger_events.filter((ev) => ev !== eventId),
    })
  }

  return (
    <ModalBackdrop onClose={onCancel} title="Create Cascade">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-lg max-w-lg w-full mx-4 p-6 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-2xl font-serif font-bold flex items-center gap-2">
            <Phone className="w-6 h-6 text-category-600" />
            Create Cascade
          </h2>
          <button onClick={onCancel}>
            <X className="w-6 h-6" />
          </button>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block font-semibold mb-2">Cascade Name *</label>
            <input
              type="text"
              value={form.cascade_name}
              onChange={(e) => onChange({ ...form, cascade_name: e.target.value })}
              placeholder={t('placeholder.emergencyOperationsCascade.egCriticalIncidentResponse')}
              className="w-full p-3 border-2 border-lsc-border dark:border-earth-700 rounded-lg focus:border-category-500 outline-none"
            />
          </div>

          <div>
            <label className="block font-semibold mb-2">Description</label>
            <textarea
              value={form.cascade_description}
              onChange={(e) => onChange({ ...form, cascade_description: e.target.value })}
              placeholder={t('emergencyOperationsCascade.describeThePurposeOfThis')}
              className="w-full p-3 border-2 border-lsc-border dark:border-earth-700 rounded-lg focus:border-category-500 outline-none"
              rows={2}
            />
          </div>

          <div>
            <label className="block font-semibold mb-2">Max Contact Levels</label>
            <input
              type="number"
              min="1"
              max="10"
              value={form.max_contact_levels}
              onChange={(e) => onChange({ ...form, max_contact_levels: parseInt(e.target.value) })}
              className="w-full p-2 border-2 border-lsc-border dark:border-earth-700 rounded-lg focus:border-category-500 outline-none"
            />
          </div>

          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="approval_required"
              checked={form.manual_approval_required}
              onChange={(e) => onChange({ ...form, manual_approval_required: e.target.checked })}
            />
            <label htmlFor="approval_required" className="font-semibold">
              Require manual approval before executing
            </label>
          </div>

          <div>
            <label className="block font-semibold mb-2">Auto-Trigger Events</label>
            <div className="space-y-2 max-h-40 overflow-y-auto">
              {TRIGGER_EVENTS.map((event) => (
                <label key={event.id} className="flex items-center gap-2 p-2 hover:bg-earth-50 dark:bg-earth-900 dark:hover:bg-earth-800">
                  <input
                    type="checkbox"
                    checked={form.auto_trigger_events.includes(event.id)}
                    onChange={(e) => toggleTriggerEvent(event.id, e.target.checked)}
                  />
                  <span>{event.label}</span>
                </label>
              ))}
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
              Create Cascade
            </button>
          </div>
        </div>
      </div>
    </ModalBackdrop>
  )
}

/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Loader2, Plus, PlusCircle, X } from "lucide-react"
import {
  LIFECYCLE_EVENT_LABELS,
  LIFECYCLE_STAGES,
  type LifecycleEventCreate,
  type LifecycleEventType,
  type LifecycleTimeline,
} from "../../api/lifecycle-api"
import { useTranslation } from "@/i18n"
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

interface Props {
  timeline: LifecycleTimeline
  draft: Partial<LifecycleEventCreate>
  isLoading: boolean
  onChange: (next: Partial<LifecycleEventCreate>) => void
  onClose: () => void
  onSubmit: () => void
}

export function LifecycleAddEventModal({ timeline, draft, isLoading, onChange, onClose, onSubmit }: Props): React.ReactElement {
  const { t } = useTranslation()
  return (
    <ModalBackdrop onClose={onClose} title="Add Lifecycle Event">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-md w-full">
        <div className="p-4 border-b border-lsc-border dark:border-earth-700 flex items-center justify-between">
          <h3 className="font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
            <PlusCircle className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
            Add Lifecycle Event
          </h3>
          <button
            onClick={onClose}
            className="p-1 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="p-4 space-y-4">
          <div>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
              Adding event for: <span className="font-medium">{timeline.item_title}</span>
            </p>
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
              Copy ID: {timeline.item_copy_id} | Barcode: {timeline.item_copy_barcode || "N/A"}
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
              Event Type *
            </label>
            <select
              value={draft.event_type || ""}
              onChange={(e) => onChange({ ...draft, event_type: e.target.value as LifecycleEventType })}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
              required
            >
              <option value="">Select event type...</option>
              {Object.entries(LIFECYCLE_STAGES).map(([stageKey, stage]) => (
                <optgroup key={stageKey} label={stage.label}>
                  {stage.events.map((eventType) => (
                    <option key={eventType} value={eventType}>
                      {LIFECYCLE_EVENT_LABELS[eventType]}
                    </option>
                  ))}
                </optgroup>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
              Description
            </label>
            <textarea
              value={draft.description || ""}
              onChange={(e) => onChange({ ...draft, description: e.target.value })}
              placeholder={t('staffLifecycleManagement.optionalDescriptionOrNotes')}
              rows={3}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent resize-none"
            />
          </div>
        </div>
        <div className="p-4 border-t border-lsc-border dark:border-earth-700 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-lsc-brown/30 rounded-xl transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={onSubmit}
            disabled={!draft.event_type || isLoading}
            className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-xl hover:bg-lsc-rose/90 transition-colors disabled:opacity-50"
          >
            {isLoading ? (
              <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
            ) : (
              <Plus className="w-4 h-4" />
            )}
            Add Event
          </button>
        </div>
      </div>
    </ModalBackdrop>
  )
}

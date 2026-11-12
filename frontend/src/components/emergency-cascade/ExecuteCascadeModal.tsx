/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { AlertTriangle, X, Loader2, Send } from "lucide-react"
import { useTranslation } from "@/i18n"
import type { CascadeData } from "./types"
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

interface Props {
  cascade: CascadeData
  triggerReason: string
  isSaving: boolean
  onChangeReason: (reason: string) => void
  onCancel: () => void
  onSubmit: () => void
}

export function ExecuteCascadeModal({
  cascade,
  triggerReason,
  isSaving,
  onChangeReason,
  onCancel,
  onSubmit,
}: Props): React.ReactElement {
  const { t } = useTranslation()

  return (
    <ModalBackdrop onClose={onCancel} title="Execute Cascade">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-lg max-w-md w-full mx-4 p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-2xl font-serif font-bold flex items-center gap-2">
            <AlertTriangle className="w-6 h-6 text-status-danger-600" />
            Execute Cascade
          </h2>
          <button onClick={onCancel}>
            <X className="w-6 h-6" />
          </button>
        </div>

        <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
          This will immediately notify all contacts in the <strong>{cascade.cascade_name}</strong> cascade.
        </p>

        <div className="space-y-4">
          <div>
            <label className="block font-semibold mb-2">Reason for Emergency *</label>
            <textarea
              value={triggerReason}
              onChange={(e) => onChangeReason(e.target.value)}
              placeholder={t('emergencyOperationsCascade.describeTheEmergencySituation')}
              className="w-full p-3 border-2 border-lsc-border dark:border-earth-700 rounded-lg focus:border-status-danger-500 outline-none"
              rows={3}
            />
          </div>

          <div className="bg-status-warning-50 dark:bg-status-warning-900/20 border-2 border-status-warning-200 dark:border-status-warning-800 rounded-lg p-4">
            <p className="text-sm text-status-warning-900 dark:text-status-warning-200">
              <strong>Warning:</strong> All contacts will be notified immediately. This action cannot be undone.
            </p>
          </div>

          <div className="flex gap-3">
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
              className="flex-1 px-4 py-2 bg-status-danger-600 text-white rounded-lg hover:bg-status-danger-700 font-semibold disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {isSaving ? <Loader2 className="w-4 h-4 motion-safe:animate-spin" /> : <Send className="w-4 h-4" />}
              Execute Now
            </button>
          </div>
        </div>
      </div>
    </ModalBackdrop>
  )
}

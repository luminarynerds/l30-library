/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Check, CheckCircle, X } from "lucide-react"
import { getSeverityColor, type LinkHealthAlert } from "@/api/link-health-api"
import { useTranslation } from "@/i18n"
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

interface Props {
  alert: LinkHealthAlert
  alertNotes: string
  onNotesChange: (value: string) => void
  onAcknowledge: () => void
  onResolve: () => void
  onClose: () => void
}

export function AlertModal({ alert, alertNotes, onNotesChange, onAcknowledge, onResolve, onClose }: Props) {
  const { t } = useTranslation()

  return (
    <ModalBackdrop onClose={onClose} title="Manage Alert">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-lg w-full">
        <div className="p-4 border-b border-lsc-border dark:border-earth-700 flex items-center justify-between">
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">Manage Alert</h3>
          <button
            onClick={onClose}
            className="p-1"
            aria-label={t("admin.adminLinkHealth.close")}
          >
            <X className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" aria-hidden="true" />
          </button>
        </div>
        <div className="p-4 space-y-4">
          <div className={`p-3 rounded-lg ${getSeverityColor(alert.severity)}`}>
            <div className="flex items-center gap-2 mb-1">
              <span className="font-medium">{alert.severity.toUpperCase()}</span>
              <span className="text-sm">- {alert.alert_type}</span>
            </div>
            <p className="text-sm">{alert.message}</p>
          </div>

          <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
            <p>URL: <a href={alert.url} target="_blank" rel="noopener noreferrer" className="text-lsc-rose hover:underline">{alert.url}</a></p>
            <p>Created: {new Date(alert.created_at).toLocaleString()}</p>
            <p>Status: {alert.status}</p>
          </div>

          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
              Notes (optional)
            </label>
            <textarea
              value={alertNotes}
              onChange={(e) => onNotesChange(e.target.value)}
              rows={3}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
              placeholder={t('admin.adminLinkHealth.addNotesAboutThisAlert')}
            />
          </div>
        </div>
        <div className="p-4 border-t border-lsc-border dark:border-earth-700 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70"
          >
            Cancel
          </button>
          {alert.status === "open" && (
            <button
              onClick={onAcknowledge}
              className="flex items-center gap-2 px-4 py-2 bg-status-warning-500 text-white rounded-lg hover:bg-status-warning-600"
            >
              <Check className="w-4 h-4" />
              Acknowledge
            </button>
          )}
          <button
            onClick={onResolve}
            className="flex items-center gap-2 px-4 py-2 bg-status-success-600 text-white rounded-lg hover:bg-status-success-700"
          >
            <CheckCircle className="w-4 h-4" />
            Resolve
          </button>
        </div>
      </div>
    </ModalBackdrop>
  )
}

/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { AlertTriangle } from "lucide-react"
import * as rfidSimulatorApi from "../../api/rfid-simulator-api"
import { useTranslation } from "@/i18n"
import type { RFIDReader } from "./types"
import type { SecurityAlertResult } from "../../api/rfid-simulator-api"

interface SecurityTabProps {
  readers: RFIDReader[]
  selectedReader: number
  onSelectReader: (id: number) => void
  securityForm: { tag_id: string; use_registered_tag: boolean }
  onSetSecurityForm: (form: { tag_id: string; use_registered_tag: boolean }) => void
  securityAlerts: SecurityAlertResult[]
  onSimulateSecurityAlert: () => void
}

export function SecurityTab({
  readers,
  selectedReader,
  onSelectReader,
  securityForm,
  onSetSecurityForm,
  securityAlerts,
  onSimulateSecurityAlert,
}: SecurityTabProps) {
  const { t } = useTranslation()

  return (
    <div className="space-y-6">
      <div className="border border-lsc-border dark:border-earth-700 rounded-xl p-4">
        <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-3 flex items-center gap-2">
          <AlertTriangle className="w-4 h-4" />Simulate Security Gate Alert
        </h3>
        <div className="grid md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Security Gate Reader *</label>
            <select
              value={selectedReader}
              onChange={(e) => onSelectReader(parseInt(e.target.value))}
              className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
            >
              <option value={0}>-- Select Reader --</option>
              {readers.map(r => (
                <option key={r.id} value={r.id}>{r.name} ({rfidSimulatorApi.getReaderTypeLabel(r.reader_type as rfidSimulatorApi.RFIDReaderType)})</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Tag ID (optional)</label>
            <input
              type="text"
              value={securityForm.tag_id}
              onChange={(e) => onSetSecurityForm({ ...securityForm, tag_id: e.target.value })}
              placeholder={t('rFIDSimulator.leaveEmptyForRandomTag')}
              className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream font-mono"
            />
          </div>
          <div className="flex items-center">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={securityForm.use_registered_tag}
                onChange={(e) => onSetSecurityForm({ ...securityForm, use_registered_tag: e.target.checked })}
                className="w-4 h-4 rounded border-lsc-border"
              />
              <span className="text-sm text-lsc-dark dark:text-lsc-cream">{t('rFIDSimulator.useRegisteredTagLinkedTo')}</span>
            </label>
          </div>
        </div>
        <div className="mt-4 flex justify-end">
          <button
            onClick={onSimulateSecurityAlert}
            disabled={!selectedReader}
            className="px-6 py-2 bg-status-danger-600 hover:bg-status-danger-700 disabled:bg-earth-300 disabled:cursor-not-allowed text-white rounded-xl font-medium flex items-center gap-2"
          >
            <AlertTriangle className="w-4 h-4" />Trigger Alert
          </button>
        </div>
      </div>

      {securityAlerts.length > 0 && (
        <div>
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-3">Recent Simulated Alerts</h3>
          <div className="space-y-2">
            {securityAlerts.slice(0, 10).map((alert, idx) => (
              <div key={idx} className="border border-status-danger-200 dark:border-status-danger-800 bg-status-danger-50 dark:bg-status-danger-900/20 rounded-xl p-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 text-status-danger-600" />
                    <span className="font-medium text-status-danger-700 dark:text-status-danger-300">{alert.alert_type.replace(/_/g, " ")}</span>
                  </div>
                  <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{new Date(alert.timestamp).toLocaleString()}</span>
                </div>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                  {alert.item_title || alert.tag_id || "Unknown item"} - Reader #{alert.reader_id}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

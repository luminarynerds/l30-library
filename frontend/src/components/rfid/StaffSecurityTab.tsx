/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Shield, RefreshCw, CheckCircle, AlertTriangle } from "lucide-react"
import { useTranslation } from "@/i18n"
import type { SecurityAlert } from "./staff-rfid-types"

interface Props {
  alerts: SecurityAlert[]
  onRefresh: () => void
  onResolve: (alertId: number) => void
}

export function StaffSecurityTab({ alerts, onRefresh, onResolve }: Props) {
  const { t } = useTranslation()

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
          <Shield className="w-5 h-5" />Security Alerts
        </h2>
        <button onClick={onRefresh} className="flex items-center gap-2 text-sm text-lsc-rose hover:underline">
          <RefreshCw className="w-4 h-4" />Refresh
        </button>
      </div>

      {alerts.length === 0 ? (
        <div className="text-center py-12">
          <CheckCircle className="w-12 h-12 text-status-success-500 mx-auto mb-3" />
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('staffRFID.noUnresolvedSecurityAlerts')}</p>
        </div>
      ) : (
        <div className="space-y-3">
          {alerts.map((alert) => (
            <div key={alert.id} className="border border-status-danger-200 dark:border-status-danger-800 bg-status-danger-50 dark:bg-status-danger-900/20 rounded-xl p-4">
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-3">
                  <AlertTriangle className="w-5 h-5 text-status-danger-600 mt-0.5" />
                  <div>
                    <p className="font-semibold text-status-danger-700 dark:text-status-danger-300">{alert.alert_type.replace(/_/g, " ").toUpperCase()}</p>
                    <p className="text-sm text-lsc-dark dark:text-lsc-cream">{alert.item_title || `Tag: ${alert.tag_id}`}</p>
                    {alert.item_barcode && <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Barcode: {alert.item_barcode}</p>}
                    <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                      {alert.reader_name} • {alert.reader_location} • {new Date(alert.created_at).toLocaleString()}
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => onResolve(alert.id)}
                  className="px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl font-medium text-sm"
                >
                  Resolve
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

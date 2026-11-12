/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useRef, useState } from "react"
import { Bell } from "lucide-react"
import { getSeverityColor, ALERT_SEVERITIES, type LinkHealthAlert, type AlertSeverity } from "@/api/link-health-api"
import { ErrorAlert } from "@/components/ui/ErrorAlert"
import { useTranslation } from "@/i18n"

interface Props {
  alerts: LinkHealthAlert[]
  severityFilter: AlertSeverity | ""
  hasError: boolean
  onSeverityFilter: (value: AlertSeverity | "") => void
  onManageAlert: (alert: LinkHealthAlert) => void
  onRetry: () => void
}

export function AlertsView({ alerts, severityFilter, hasError, onSeverityFilter, onManageAlert, onRetry }: Props) {
  const { t } = useTranslation()

  // Enhancement 5: polite live region — announce on transition
  const prevStateRef = useRef<"loading" | "error" | "empty" | "data">("loading")
  const [announcement, setAnnouncement] = useState("")

  useEffect(() => {
    const next = hasError ? "error" : alerts.length === 0 ? "empty" : "data"
    if (next !== prevStateRef.current) {
      prevStateRef.current = next
      const msg = next === "error"
        ? t("admin.adminLinkHealth.announceCouldntLoadAlerts")
        : next === "empty"
          ? t("admin.adminLinkHealth.announceNoAlerts")
          : t("admin.adminLinkHealth.announceAlertCount", { count: alerts.length })

      setAnnouncement(msg)
    }
  }, [hasError, alerts.length, t])

  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm overflow-hidden">
      {/* Enhancement 5: visually-hidden polite live region */}
      <div aria-live="polite" aria-atomic="true" className="sr-only">{announcement}</div>

      <div className="p-4 border-b border-lsc-border dark:border-earth-700">
        <div className="flex items-center gap-3">
          <select
            value={severityFilter}
            onChange={(e) => onSeverityFilter(e.target.value as AlertSeverity | "")}
            aria-label={t("admin.adminLinkHealth.filterBySeverity")}
            className="px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
          >
            <option value="">All Severities</option>
            {ALERT_SEVERITIES.map((severity) => (
              <option key={severity} value={severity}>
                {severity.charAt(0).toUpperCase() + severity.slice(1)}
              </option>
            ))}
          </select>
          {!hasError && (
            <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
              {alerts.length} open alerts
            </span>
          )}
        </div>
      </div>

      {/* Enhancement 1: inline error banner with retry */}
      {hasError ? (
        <div className="p-4">
          <ErrorAlert
            title={t("admin.adminLinkHealth.errorLoadingAlerts")}
            message={t("admin.adminLinkHealth.errorLoadingAlertsMessage")}
            variant="error"
            onRetry={onRetry}
            retryText={t("admin.adminLinkHealth.retry")}
          />
        </div>
      ) : alerts.length === 0 ? (
        <div className="p-8 text-center">
          <Bell className="w-12 h-12 mx-auto text-status-success-500 mb-4" />
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">No open alerts</p>
        </div>
      ) : (
        <div className="divide-y divide-lsc-border dark:divide-earth-700">
          {alerts.map((alert) => (
            <div key={alert.id} className="p-4">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${getSeverityColor(alert.severity)}`}>
                      {alert.severity.toUpperCase()}
                    </span>
                    <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${
                      alert.status === "open"
                        ? "bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-700 dark:text-status-danger-400"
                        : "bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-700 dark:text-status-warning-400"
                    }`}>
                      {alert.status}
                    </span>
                  </div>
                  <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                    {alert.message}
                  </p>
                  <div className="flex flex-wrap gap-2 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                    <span>Type: {alert.alert_type}</span>
                    <span>Created: {new Date(alert.created_at).toLocaleString()}</span>
                    {alert.acknowledged_at && (
                      <span>Acknowledged: {new Date(alert.acknowledged_at).toLocaleString()}</span>
                    )}
                  </div>
                  <a
                    href={alert.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-lsc-rose hover:underline truncate block mt-1"
                  >
                    {alert.url}
                  </a>
                </div>
                <button
                  onClick={() => onManageAlert(alert)}
                  className="px-3 py-1.5 text-sm bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90"
                >
                  Manage
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

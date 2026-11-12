/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useRef, useState } from "react"
import { Loader2, CheckCircle, Bell, History, Play, Server } from "lucide-react"
import { getSeverityColor, getStatusColor, formatResponseTime, type LinkHealthSummary, type LinkHealthAlert, type PlatformStatus } from "@/api/link-health-api"
import { ErrorAlert } from "@/components/ui/ErrorAlert"
import { useTranslation } from "@/i18n"

interface Props {
  isAdmin: boolean
  isRunningCheck: boolean
  brokenLinks: LinkHealthSummary[]
  alerts: LinkHealthAlert[]
  platformStatus: PlatformStatus | null
  hasError: boolean
  onBulkCheck: (type: "external" | "lesson" | "platforms" | "catalog") => void
  onViewBroken: () => void
  onViewAlerts: () => void
  onViewHistory: (url: string) => void
  onManageAlert: (alert: LinkHealthAlert) => void
  onRetry: () => void
  getStatusIcon: (status: string) => React.ReactElement
}

export function OverviewView({
  isAdmin,
  isRunningCheck,
  brokenLinks,
  alerts,
  platformStatus,
  hasError,
  onBulkCheck,
  onViewBroken,
  onViewAlerts,
  onViewHistory,
  onManageAlert,
  onRetry,
  getStatusIcon,
}: Props) {
  const { t } = useTranslation()

  // Enhancement 5: polite live region — announce on transition
  const prevStateRef = useRef<"loading" | "error" | "empty" | "data">("loading")
  const [announcement, setAnnouncement] = useState("")

  useEffect(() => {
    const next = hasError ? "error" : (brokenLinks.length === 0 && alerts.length === 0) ? "empty" : "data"
    if (next !== prevStateRef.current) {
      prevStateRef.current = next
      const msg = next === "error"
        ? t("admin.adminLinkHealth.announceCouldntLoadOverview")
        : next === "empty"
          ? t("admin.adminLinkHealth.announceOverviewClean")
          : t("admin.adminLinkHealth.announceOverviewSummary", { broken: brokenLinks.length, alerts: alerts.length })

      setAnnouncement(msg)
    }
  }, [hasError, brokenLinks.length, alerts.length, t])

  return (
    <div className="space-y-6">
      {/* Enhancement 5: visually-hidden polite live region */}
      <div aria-live="polite" aria-atomic="true" className="sr-only">{announcement}</div>

      {/* Enhancement 1: overview-level error banner when any slice failed */}
      {hasError && (
        <ErrorAlert
          title={t("admin.adminLinkHealth.errorLoadingOverview")}
          message={t("admin.adminLinkHealth.errorLoadingOverviewMessage")}
          variant="error"
          onRetry={onRetry}
          retryText={t("admin.adminLinkHealth.retry")}
        />
      )}

      {/* Quick Actions */}
      {isAdmin && (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4">Bulk Validation</h3>
          <div className="flex flex-wrap gap-3">
            <button
              onClick={() => onBulkCheck("external")}
              disabled={isRunningCheck}
              className="flex items-center gap-2 px-4 py-2 bg-earth-100 dark:bg-earth-800/30 text-lsc-rose dark:text-lsc-rose-light rounded-lg hover:bg-earth-200 dark:hover:bg-earth-800/50 transition-colors disabled:opacity-50"
            >
              <Play className="w-4 h-4" />
              Check External Resources
            </button>
            <button
              onClick={() => onBulkCheck("lesson")}
              disabled={isRunningCheck}
              className="flex items-center gap-2 px-4 py-2 bg-category-100 dark:bg-category-900/30 text-category-700 dark:text-category-400 rounded-lg hover:bg-category-200 dark:hover:bg-category-900/50 transition-colors disabled:opacity-50"
            >
              <Play className="w-4 h-4" />
              Check Lesson Resources
            </button>
            <button
              onClick={() => onBulkCheck("platforms")}
              disabled={isRunningCheck}
              className="flex items-center gap-2 px-4 py-2 bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-400 rounded-lg hover:bg-status-success-200 dark:hover:bg-status-success-900/50 transition-colors disabled:opacity-50"
            >
              <Server className="w-4 h-4" />
              Check Digital Platforms
            </button>
            <button
              onClick={() => onBulkCheck("catalog")}
              disabled={isRunningCheck}
              className="flex items-center gap-2 px-4 py-2 bg-category-100 dark:bg-category-900/30 text-category-700 dark:text-category-400 rounded-lg hover:bg-category-200 dark:hover:bg-category-900/50 transition-colors disabled:opacity-50"
            >
              <Play className="w-4 h-4" />
              Check Catalog Links
            </button>
          </div>
          {isRunningCheck && (
            <div
              role="status"
              aria-live="polite"
              aria-label={t("admin.adminLinkHealth.validationRunning")}
              className="mt-4 flex items-center gap-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70"
            >
              <Loader2 className="w-4 h-4 motion-safe:animate-spin" aria-hidden="true" />
              Running validation...
            </div>
          )}
        </div>
      )}

      {/* Platform Status */}
      {platformStatus && (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4">Digital Platform Status</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {Object.entries(platformStatus.platforms).map(([platform, status]) => (
              <div key={platform} className="flex items-center justify-between p-3 bg-lsc-cream/50 dark:bg-earth-700/50 rounded-lg">
                <div className="flex items-center gap-2">
                  {getStatusIcon(status.status)}
                  <span className="font-medium text-lsc-dark dark:text-lsc-cream capitalize">
                    {platform.replace(/_/g, " ")}
                  </span>
                </div>
                <span className={`text-sm px-2 py-0.5 rounded-full ${getStatusColor(status.status)}`}>
                  {status.response_time_ms ? formatResponseTime(status.response_time_ms) : status.status}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent Broken Links */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">Recent Broken Links</h3>
          <button
            onClick={onViewBroken}
            className="text-sm text-lsc-rose hover:underline"
          >
            View all
          </button>
        </div>
        {brokenLinks.length === 0 ? (
          <div className="text-center py-8 text-lsc-dark/70 dark:text-lsc-cream/70">
            <CheckCircle className="w-12 h-12 mx-auto text-status-success-500 mb-2" />
            <p>{t('admin.adminLinkHealth.noBrokenLinksDetected')}</p>
          </div>
        ) : (
          <div className="space-y-2">
            {brokenLinks.slice(0, 5).map((link) => (
              <div key={link.id} className="flex items-center justify-between p-3 bg-status-danger-50 dark:bg-status-danger-900/20 rounded-lg">
                <div className="flex-1 min-w-0 mr-4">
                  <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream truncate" title={link.url}>
                    {link.url}
                  </p>
                  <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                    {link.last_error_message || `HTTP ${link.last_http_status}`}
                  </p>
                </div>
                <button
                  onClick={() => onViewHistory(link.url)}
                  className="p-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-white dark:bg-earth-800 dark:hover:bg-earth-700 rounded-lg"
                >
                  <History className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Open Alerts */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">Open Alerts</h3>
          <button
            onClick={onViewAlerts}
            className="text-sm text-lsc-rose hover:underline"
          >
            View all
          </button>
        </div>
        {alerts.length === 0 ? (
          <div className="text-center py-8 text-lsc-dark/70 dark:text-lsc-cream/70">
            <Bell className="w-12 h-12 mx-auto text-status-success-500 mb-2" />
            <p>No open alerts</p>
          </div>
        ) : (
          <div className="space-y-2">
            {alerts.slice(0, 5).map((alert) => (
              <div
                key={alert.id}
                className={`flex items-center justify-between p-3 rounded-lg ${getSeverityColor(alert.severity)}`}
              >
                <div className="flex-1 min-w-0 mr-4">
                  <p className="text-sm font-medium truncate" title={alert.message}>{alert.message}</p>
                  <p className="text-xs opacity-70">
                    {new Date(alert.created_at).toLocaleString()}
                  </p>
                </div>
                <button
                  onClick={() => onManageAlert(alert)}
                  className="px-3 py-1 text-sm bg-lsc-white/50 dark:bg-black/20 rounded-lg hover:bg-lsc-white/80 dark:hover:bg-black/40"
                >
                  Manage
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

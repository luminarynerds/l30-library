/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Settings, Trash2 } from "lucide-react"
import type { LinkHealthConfig } from "@/api/link-health-api"
import { ErrorAlert } from "@/components/ui/ErrorAlert"
import { useTranslation } from "@/i18n"

interface Props {
  config: LinkHealthConfig | null
  hasError: boolean
  onEditConfig: () => void
  onCleanup: () => void
  onRetry: () => void
}

export function ConfigView({ config, hasError, onEditConfig, onCleanup, onRetry }: Props) {
  const { t } = useTranslation()

  if (hasError || !config) {
    return (
      <div className="space-y-4">
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm">
          {/* Enhancement 1: inline error banner with retry */}
          <ErrorAlert
            title={t("admin.adminLinkHealth.errorLoadingConfig")}
            message={t("admin.adminLinkHealth.errorLoadingConfigMessage")}
            variant="error"
            onRetry={onRetry}
            retryText={t("admin.adminLinkHealth.retry")}
          />
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm">
        <div className="flex items-center justify-between mb-6">
          <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
            Monitoring Configuration
          </h3>
          <button
            onClick={onEditConfig}
            className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90"
          >
            <Settings className="w-4 h-4" />
            Edit Config
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <div className="p-4 bg-lsc-cream/50 dark:bg-earth-700/50 rounded-lg">
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Monitoring Status</p>
            <p className="text-lg font-medium text-lsc-dark dark:text-lsc-cream">
              {config.monitoring_enabled ? (
                <span className="text-status-success-600 dark:text-status-success-400">Enabled</span>
              ) : (
                <span className="text-status-danger-600 dark:text-status-danger-400">Disabled</span>
              )}
            </p>
          </div>
          <div className="p-4 bg-lsc-cream/50 dark:bg-earth-700/50 rounded-lg">
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Check Interval</p>
            <p className="text-lg font-medium text-lsc-dark dark:text-lsc-cream">
              {config.default_check_interval_minutes} minutes
            </p>
          </div>
          <div className="p-4 bg-lsc-cream/50 dark:bg-earth-700/50 rounded-lg">
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Timeout</p>
            <p className="text-lg font-medium text-lsc-dark dark:text-lsc-cream">
              {config.default_timeout_seconds} seconds
            </p>
          </div>
          <div className="p-4 bg-lsc-cream/50 dark:bg-earth-700/50 rounded-lg">
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Alert After Failures</p>
            <p className="text-lg font-medium text-lsc-dark dark:text-lsc-cream">
              {config.alert_on_consecutive_failures}
            </p>
          </div>
          <div className="p-4 bg-lsc-cream/50 dark:bg-earth-700/50 rounded-lg">
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Degraded Threshold</p>
            <p className="text-lg font-medium text-lsc-dark dark:text-lsc-cream">
              {config.degraded_response_time_ms}ms
            </p>
          </div>
          <div className="p-4 bg-lsc-cream/50 dark:bg-earth-700/50 rounded-lg">
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">History Retention</p>
            <p className="text-lg font-medium text-lsc-dark dark:text-lsc-cream">
              {config.keep_history_days} days
            </p>
          </div>
          <div className="p-4 bg-lsc-cream/50 dark:bg-earth-700/50 rounded-lg">
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">SSL Check</p>
            <p className="text-lg font-medium text-lsc-dark dark:text-lsc-cream">
              {config.ssl_check_enabled ? "Enabled" : "Disabled"}
            </p>
          </div>
          <div className="p-4 bg-lsc-cream/50 dark:bg-earth-700/50 rounded-lg">
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Max Redirects</p>
            <p className="text-lg font-medium text-lsc-dark dark:text-lsc-cream">
              {config.max_redirects}
            </p>
          </div>
          <div className="p-4 bg-lsc-cream/50 dark:bg-earth-700/50 rounded-lg">
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Concurrent Checks</p>
            <p className="text-lg font-medium text-lsc-dark dark:text-lsc-cream">
              {config.max_concurrent_checks}
            </p>
          </div>
        </div>

        <div className="mt-6 pt-6 border-t border-lsc-border dark:border-earth-700">
          <h4 className="font-medium text-lsc-dark dark:text-lsc-cream mb-3">Notification Settings</h4>
          <div className="flex flex-wrap gap-4 text-sm">
            <span className={`px-3 py-1 rounded-full ${
              config.notify_on_broken
                ? "bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-400"
                : "bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70"
            }`}>
              Notify on broken: {config.notify_on_broken ? "Yes" : "No"}
            </span>
            <span className={`px-3 py-1 rounded-full ${
              config.notify_on_recovered
                ? "bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-400"
                : "bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70"
            }`}>
              Notify on recovery: {config.notify_on_recovered ? "Yes" : "No"}
            </span>
          </div>
          {config.notification_emails.length > 0 && (
            <div className="mt-3">
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Notification emails:</p>
              <div className="flex flex-wrap gap-2">
                {config.notification_emails.map((email) => (
                  <span key={email} className="px-2 py-1 bg-lsc-cream dark:bg-earth-700 rounded text-sm">
                    {email}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="mt-6 pt-6 border-t border-lsc-border dark:border-earth-700">
          <h4 className="font-medium text-lsc-dark dark:text-lsc-cream mb-3">Maintenance</h4>
          <button
            onClick={onCleanup}
            className="flex items-center gap-2 px-4 py-2 bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-700 dark:text-status-danger-400 rounded-lg hover:bg-status-danger-200 dark:hover:bg-status-danger-900/50"
          >
            <Trash2 className="w-4 h-4" />
            Cleanup Old Data
          </button>
        </div>
      </div>
    </div>
  )
}

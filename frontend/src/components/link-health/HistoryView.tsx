/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { History } from "lucide-react"
import { getStatusColor, formatResponseTime, type LinkHealthCheck } from "@/api/link-health-api"
import { useTranslation } from "@/i18n"

interface Props {
  searchUrl: string
  selectedUrl: string | null
  urlHistory: LinkHealthCheck[]
  onSearchChange: (value: string) => void
  onSearch: () => void
  getStatusIcon: (status: string) => React.ReactElement
}

export function HistoryView({ searchUrl, selectedUrl, urlHistory, onSearchChange, onSearch, getStatusIcon }: Props) {
  const { t } = useTranslation()

  return (
    <div className="space-y-4">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
        <form onSubmit={(e) => { e.preventDefault(); onSearch() }} className="flex items-center gap-3">
          <input
            type="text"
            value={searchUrl}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder={t('admin.adminLinkHealth.enterUrlToViewHistory')}
            aria-label={t('admin.adminLinkHealth.searchLinks')}
            className="flex-1 px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
          />
          <button
            type="submit"
            className="px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90"
          >
            Search
          </button>
        </form>
      </div>

      {selectedUrl && (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm overflow-hidden">
          <div className="p-4 border-b border-lsc-border dark:border-earth-700">
            <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
              History for: <span className="text-lsc-rose break-all">{selectedUrl}</span>
            </h3>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
              {urlHistory.length} checks in the last 30 days
            </p>
          </div>
          {urlHistory.length === 0 ? (
            <div className="p-8 text-center">
              <History className="w-12 h-12 mx-auto text-lsc-dark/70 dark:text-lsc-cream/70 mb-4" />
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('admin.adminLinkHealth.noHistoryFoundForThis')}</p>
            </div>
          ) : (
            <div className="divide-y divide-lsc-border dark:divide-earth-700">
              {urlHistory.map((check) => (
                <div key={check.id} className="p-4">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-2">
                      {getStatusIcon(check.status)}
                      <div>
                        <span className={`text-sm font-medium px-2 py-0.5 rounded ${getStatusColor(check.status)}`}>
                          {check.status.toUpperCase()}
                        </span>
                        {check.http_status_code && (
                          <span className="ml-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                            HTTP {check.http_status_code}
                          </span>
                        )}
                      </div>
                    </div>
                    <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                      {new Date(check.checked_at).toLocaleString()}
                    </span>
                  </div>
                  <div className="mt-2 flex flex-wrap gap-2 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                    {check.response_time_ms !== null && (
                      <span className="px-2 py-0.5 bg-lsc-cream dark:bg-earth-700 rounded">
                        {formatResponseTime(check.response_time_ms)}
                      </span>
                    )}
                    {check.redirect_count > 0 && (
                      <span className="px-2 py-0.5 bg-lsc-cream dark:bg-earth-700 rounded">
                        {check.redirect_count} redirect{check.redirect_count > 1 ? "s" : ""}
                      </span>
                    )}
                    {check.ssl_valid !== null && (
                      <span className={`px-2 py-0.5 rounded ${
                        check.ssl_valid
                          ? "bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-400"
                          : "bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-700 dark:text-status-danger-400"
                      }`}>
                        SSL {check.ssl_valid ? "Valid" : "Invalid"}
                      </span>
                    )}
                  </div>
                  {check.error_message && (
                    <p className="mt-1 text-xs text-status-danger-600 dark:text-status-danger-400">
                      {check.error_message}
                    </p>
                  )}
                  {check.final_url && check.final_url !== check.url && (
                    <p className="mt-1 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                      Redirected to: {check.final_url}
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

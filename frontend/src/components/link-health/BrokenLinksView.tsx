/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useRef, useState } from "react"
import { Link } from "react-router-dom"
import { CheckCircle, ExternalLink, History } from "lucide-react"
import { getSourceLabel, LINK_SOURCES, type LinkHealthSummary } from "@/api/link-health-api"
import { ErrorAlert } from "@/components/ui/ErrorAlert"
import { useTranslation } from "@/i18n"

interface Props {
  brokenLinks: LinkHealthSummary[]
  sourceFilter: string
  hasError: boolean
  onSourceFilter: (value: string) => void
  onViewHistory: (url: string) => void
  onRetry: () => void
  onMonitoringChange: (id: number, isMonitored: boolean) => void
  showUnmonitored: boolean
  onShowUnmonitoredChange: (value: boolean) => void
  getStatusIcon: (status: string) => React.ReactElement
  formatLastChecked: (iso: string | null | undefined) => string
}

export function BrokenLinksView({ brokenLinks, sourceFilter, hasError, onSourceFilter, onViewHistory, onRetry, onMonitoringChange, showUnmonitored, onShowUnmonitoredChange, getStatusIcon, formatLastChecked }: Props) {
  const { t } = useTranslation()

  // Enhancement 5: polite live region — announce on transition to loaded/empty/error only
  const prevStateRef = useRef<"loading" | "error" | "empty" | "data">("loading")
  const [announcement, setAnnouncement] = useState("")

  useEffect(() => {
    const next = hasError ? "error" : brokenLinks.length === 0 ? "empty" : "data"
    if (next !== prevStateRef.current) {
      prevStateRef.current = next
      const msg = next === "error"
        ? t("admin.adminLinkHealth.announceCouldntLoadBrokenLinks")
        : next === "empty"
          ? t("admin.adminLinkHealth.announceNoBrokenLinks")
          : t("admin.adminLinkHealth.announceBrokenLinkCount", { count: brokenLinks.length })

      setAnnouncement(msg)
    }
  }, [hasError, brokenLinks.length, t])

  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm overflow-hidden">
      {/* Enhancement 5: visually-hidden polite live region */}
      <div aria-live="polite" aria-atomic="true" className="sr-only">{announcement}</div>

      <div className="p-4 border-b border-lsc-border dark:border-earth-700">
        <div className="flex items-center gap-3 flex-wrap">
          <select
            value={sourceFilter}
            onChange={(e) => onSourceFilter(e.target.value)}
            aria-label={t("admin.adminLinkHealth.filterBySource")}
            className="px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
          >
            <option value="">All Sources</option>
            {LINK_SOURCES.map((source) => (
              <option key={source.value} value={source.value}>
                {source.label}
              </option>
            ))}
          </select>
          <label className="flex items-center gap-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 cursor-pointer">
            <input
              type="checkbox"
              checked={showUnmonitored}
              onChange={(e) => onShowUnmonitoredChange(e.target.checked)}
              className="rounded border-lsc-border dark:border-earth-600"
            />
            {t("admin.adminLinkHealth.showUnmonitored")}
          </label>
          {!hasError && (
            <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
              {brokenLinks.length} broken links
            </span>
          )}
        </div>
      </div>

      {/* Enhancement 1: inline error banner with retry */}
      {hasError ? (
        <div className="p-4">
          <ErrorAlert
            title={t("admin.adminLinkHealth.errorLoadingBrokenLinks")}
            message={t("admin.adminLinkHealth.errorLoadingBrokenLinksMessage")}
            variant="error"
            onRetry={onRetry}
            retryText={t("admin.adminLinkHealth.retry")}
          />
        </div>
      ) : brokenLinks.length === 0 ? (
        <div className="p-8 text-center">
          <CheckCircle className="w-12 h-12 mx-auto text-status-success-500 mb-4" />
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('admin.adminLinkHealth.noBrokenLinksFound')}</p>
        </div>
      ) : (
        <div className="divide-y divide-lsc-border dark:divide-earth-700">
          {brokenLinks.map((link) => (
            <div key={link.id} className="p-4">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    {getStatusIcon(link.current_status)}
                    <a
                      href={link.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm font-medium text-lsc-dark dark:text-lsc-cream hover:text-lsc-rose truncate block"
                    >
                      {link.url}
                      <ExternalLink className="w-3 h-3 inline ml-1" aria-hidden="true" />
                      <span className="sr-only">{t("admin.adminLinkHealth.opensInNewTab")}</span>
                    </a>
                    {!link.is_monitored && (
                      <span className="px-2 py-0.5 bg-earth-200 dark:bg-earth-600 text-earth-700 dark:text-earth-300 rounded text-xs">
                        {t("admin.adminLinkHealth.notMonitoredBadge")}
                      </span>
                    )}
                  </div>
                  <div className="flex flex-wrap gap-2 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                    <span className="px-2 py-0.5 bg-lsc-cream dark:bg-earth-700 rounded">
                      {getSourceLabel(link.source)}
                    </span>
                    {link.source_name && (
                      <span className="px-2 py-0.5 bg-lsc-cream dark:bg-earth-700 rounded">
                        {link.source_name}
                      </span>
                    )}
                    {link.last_http_status && (
                      <span className="px-2 py-0.5 bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-700 dark:text-status-danger-400 rounded">
                        HTTP {link.last_http_status}
                      </span>
                    )}
                    <span>
                      {link.consecutive_failures} consecutive failures
                    </span>
                    {/* Enhancement 4: per-row last checked */}
                    <span className="text-lsc-dark/50 dark:text-lsc-cream/50">
                      {t('admin.adminLinkHealth.lastCheckedLabel', { time: formatLastChecked(link.last_checked_at) })}
                    </span>
                  </div>
                  {link.last_error_message && (
                    <p className="mt-1 text-xs text-status-danger-600 dark:text-status-danger-400">
                      {link.last_error_message}
                    </p>
                  )}
                  <div className="flex items-center gap-2 mt-2 flex-wrap">
                    <button
                      onClick={() => onMonitoringChange(link.id, link.is_monitored)}
                      className="px-2 py-1 text-xs border border-lsc-border dark:border-earth-600 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-lg transition-colors"
                      aria-label={link.is_monitored ? t("admin.adminLinkHealth.stopMonitoring") : t("admin.adminLinkHealth.resumeMonitoring")}
                    >
                      {link.is_monitored ? t("admin.adminLinkHealth.stopMonitoring") : t("admin.adminLinkHealth.resumeMonitoring")}
                    </button>
                    {link.source === "catalog_link" && link.source_name != null && (
                      <Link
                        to={`/catalog?q=${encodeURIComponent(link.source_name)}`}
                        className="px-2 py-1 text-xs border border-lsc-border dark:border-earth-600 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-lg transition-colors"
                      >
                        {t("admin.adminLinkHealth.viewRecord")}
                      </Link>
                    )}
                  </div>
                </div>
                <button
                  onClick={() => onViewHistory(link.url)}
                  className="p-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-lg"
                  title="View history"
                >
                  <History className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

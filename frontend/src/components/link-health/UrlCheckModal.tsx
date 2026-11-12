/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Loader2, Search, X } from "lucide-react"
import { getStatusColor, formatResponseTime, type LinkHealthCheck } from "@/api/link-health-api"
import { useTranslation } from "@/i18n"
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

interface Props {
  urlToCheck: string
  checkResult: LinkHealthCheck | null
  isRunningCheck: boolean
  onUrlChange: (value: string) => void
  onCheck: () => void
  onClose: () => void
  getStatusIcon: (status: string) => React.ReactElement
}

export function UrlCheckModal({ urlToCheck, checkResult, isRunningCheck, onUrlChange, onCheck, onClose, getStatusIcon }: Props) {
  const { t } = useTranslation()

  return (
    <ModalBackdrop onClose={onClose} title="Check Single URL">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-lg w-full">
        <div className="p-4 border-b border-lsc-border dark:border-earth-700 flex items-center justify-between">
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">Check Single URL</h3>
          <button
            onClick={onClose}
            className="p-1"
            aria-label={t("admin.adminLinkHealth.close")}
          >
            <X className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" aria-hidden="true" />
          </button>
        </div>
        <div className="p-4 space-y-4">
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
              URL to check
            </label>
            <input
              type="url"
              value={urlToCheck}
              onChange={(e) => onUrlChange(e.target.value)}
              placeholder={t('placeholder.adminLinkHealth.httpsexamplecom')}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
            />
          </div>

          {checkResult && (
            <div className={`p-4 rounded-lg ${getStatusColor(checkResult.status)}`}>
              <div className="flex items-center gap-2 mb-2">
                {getStatusIcon(checkResult.status)}
                <span className="font-medium">{checkResult.status.toUpperCase()}</span>
                {checkResult.http_status_code && (
                  <span className="text-sm">HTTP {checkResult.http_status_code}</span>
                )}
              </div>
              <div className="text-sm space-y-1">
                {checkResult.response_time_ms !== null && (
                  <p>Response time: {formatResponseTime(checkResult.response_time_ms)}</p>
                )}
                {checkResult.redirect_count > 0 && (
                  <p>Redirects: {checkResult.redirect_count}</p>
                )}
                {checkResult.ssl_valid !== null && (
                  <p>SSL: {checkResult.ssl_valid ? "Valid" : "Invalid"}</p>
                )}
                {checkResult.error_message && (
                  <p className="text-status-danger-600 dark:text-status-danger-400">Error: {checkResult.error_message}</p>
                )}
                {checkResult.final_url && checkResult.final_url !== urlToCheck && (
                  <p>Final URL: {checkResult.final_url}</p>
                )}
              </div>
            </div>
          )}
        </div>
        <div className="p-4 border-t border-lsc-border dark:border-earth-700 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70"
          >
            Close
          </button>
          <button
            onClick={onCheck}
            disabled={!urlToCheck || isRunningCheck}
            className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 disabled:opacity-50"
          >
            {isRunningCheck ? (
              <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
            ) : (
              <Search className="w-4 h-4" />
            )}
            Check
          </button>
        </div>
      </div>
    </ModalBackdrop>
  )
}

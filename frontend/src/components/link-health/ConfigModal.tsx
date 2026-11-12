/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Shield, X } from "lucide-react"
import type { LinkHealthConfig } from "@/api/link-health-api"
import { useTranslation } from "@/i18n"
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

interface Props {
  config: LinkHealthConfig
  configForm: Partial<LinkHealthConfig>
  onFormChange: (form: Partial<LinkHealthConfig>) => void
  onSave: () => void
  onClose: () => void
}

export function ConfigModal({ config, configForm, onFormChange, onSave, onClose }: Props) {
  const { t } = useTranslation()

  return (
    <ModalBackdrop onClose={onClose} title="Edit Configuration">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-2xl w-full my-8">
        <div className="p-4 border-b border-lsc-border dark:border-earth-700 flex items-center justify-between">
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">Edit Configuration</h3>
          <button
            onClick={onClose}
            className="p-1"
            aria-label={t("admin.adminLinkHealth.close")}
          >
            <X className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" aria-hidden="true" />
          </button>
        </div>
        <div className="p-4 space-y-4 max-h-[60vh] overflow-y-auto">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                Check Interval (minutes)
              </label>
              <input
                type="number"
                value={configForm.default_check_interval_minutes || ""}
                onChange={(e) => onFormChange({ ...configForm, ...(!isNaN(parseInt(e.target.value)) ? { default_check_interval_minutes: parseInt(e.target.value) } : {}) })}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                Timeout (seconds)
              </label>
              <input
                type="number"
                value={configForm.default_timeout_seconds || ""}
                onChange={(e) => onFormChange({ ...configForm, ...(!isNaN(parseInt(e.target.value)) ? { default_timeout_seconds: parseInt(e.target.value) } : {}) })}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                Max Redirects
              </label>
              <input
                type="number"
                value={configForm.max_redirects || ""}
                onChange={(e) => onFormChange({ ...configForm, ...(!isNaN(parseInt(e.target.value)) ? { max_redirects: parseInt(e.target.value) } : {}) })}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                Alert After Failures
              </label>
              <input
                type="number"
                value={configForm.alert_on_consecutive_failures || ""}
                onChange={(e) => onFormChange({ ...configForm, ...(!isNaN(parseInt(e.target.value)) ? { alert_on_consecutive_failures: parseInt(e.target.value) } : {}) })}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                Degraded Threshold (ms)
              </label>
              <input
                type="number"
                value={configForm.degraded_response_time_ms || ""}
                onChange={(e) => onFormChange({ ...configForm, ...(!isNaN(parseInt(e.target.value)) ? { degraded_response_time_ms: parseInt(e.target.value) } : {}) })}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                History Retention (days)
              </label>
              <input
                type="number"
                value={configForm.keep_history_days || ""}
                onChange={(e) => onFormChange({ ...configForm, ...(!isNaN(parseInt(e.target.value)) ? { keep_history_days: parseInt(e.target.value) } : {}) })}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
              />
            </div>
          </div>

          <div className="space-y-3">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={configForm.monitoring_enabled ?? config.monitoring_enabled}
                onChange={(e) => onFormChange({ ...configForm, monitoring_enabled: e.target.checked })}
                className="w-4 h-4"
              />
              <span className="text-sm text-lsc-dark dark:text-lsc-cream">Enable Monitoring</span>
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={configForm.ssl_check_enabled ?? config.ssl_check_enabled}
                onChange={(e) => onFormChange({ ...configForm, ssl_check_enabled: e.target.checked })}
                className="w-4 h-4"
              />
              <span className="text-sm text-lsc-dark dark:text-lsc-cream">Enable SSL Check</span>
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={configForm.notify_on_broken ?? config.notify_on_broken}
                onChange={(e) => onFormChange({ ...configForm, notify_on_broken: e.target.checked })}
                className="w-4 h-4"
              />
              <span className="text-sm text-lsc-dark dark:text-lsc-cream">{t('admin.adminLinkHealth.notifyOnBrokenLinks')}</span>
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={configForm.notify_on_recovered ?? config.notify_on_recovered}
                onChange={(e) => onFormChange({ ...configForm, notify_on_recovered: e.target.checked })}
                className="w-4 h-4"
              />
              <span className="text-sm text-lsc-dark dark:text-lsc-cream">Notify on Recovery</span>
            </label>
          </div>
        </div>
        <div className="p-4 border-t border-lsc-border dark:border-earth-700 flex justify-end gap-3">
          <button onClick={onClose} className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70">
            Cancel
          </button>
          <button
            onClick={onSave}
            className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90"
          >
            <Shield className="w-4 h-4" />
            Save Changes
          </button>
        </div>
      </div>
    </ModalBackdrop>
  )
}

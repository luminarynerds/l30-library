/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useState, useEffect, useCallback } from 'react'
import toast from 'react-hot-toast'
import {
  MessageSquare,
  Settings,
  RefreshCw,
  Loader2,
  Save,
  CheckCircle,
  AlertTriangle,
  TestTube2,
  BarChart3,
  Phone,
  Send,
  Bell,
  FileText,
} from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import { API_BASE } from '@/api/types'
import api from '@/lib/api-client'
import { useTranslation } from '@/i18n'
import {
  StatCard,
  StatGrid,
  ToggleRow,
  NumberField,
} from '@/components/admin'
import { useConfigurationSection } from '@/hooks/useConfigurationSection'
import { SectionShell } from '../ai-settings/SectionShell'

interface SMSConfig extends Record<string, unknown> {
  provider: string
  provider_enabled: boolean
  from_number: string
  rate_limit_per_hour: number
  rate_limit_per_day: number
  opt_in_required: boolean
  allow_marketing: boolean
  quiet_hours_start: string
  quiet_hours_end: string
}

const DEFAULT_SMS_CONFIG: SMSConfig = {
  provider: '',
  provider_enabled: false,
  from_number: '',
  rate_limit_per_hour: 60,
  rate_limit_per_day: 500,
  opt_in_required: true,
  allow_marketing: false,
  quiet_hours_start: '21:00',
  quiet_hours_end: '08:00',
}

interface SMSStats {
  messages_sent_today: number
  messages_sent_this_month: number
  delivery_rate_percent: number
  opt_in_count: number
  opt_out_count: number
}

interface SMSTemplate {
  id: number
  name: string
  template_type: string
  content: string
  is_active: boolean
}

interface SMSSectionProps {
  onBack: () => void
}

export function SMSSection({ onBack }: SMSSectionProps) {
  const { t } = useTranslation()
  const { isAuthenticated } = useAuth()

  const {
    value: config,
    setField,
    loading: isLoading,
    saving: isSaving,
    save,
  } = useConfigurationSection<SMSConfig>('sms_settings', DEFAULT_SMS_CONFIG, {
    successMessage: t('toast.adminSMSSettings.configurationSaved'),
    errorMessage: t('admin.adminSMSSettings.failedToSaveConfiguration'),
    defaultReason: 'Admin update via SMS settings UI',
  })

  const [stats, setStats] = useState<SMSStats | null>(null)
  const [templates, setTemplates] = useState<SMSTemplate[]>([])
  const [testNumber, setTestNumber] = useState('')

  const fetchStats = useCallback(async () => {
    try {
      const data = await api.get<SMSStats>(`${API_BASE}/sms/staff/stats`)
      setStats(data)
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
    }
  }, [])

  const fetchTemplates = useCallback(async () => {
    try {
      const data = await api.get<{ templates?: SMSTemplate[] }>(`${API_BASE}/notifications/templates`)
      setTemplates(data.templates || (Array.isArray(data) ? data as unknown as SMSTemplate[] : []))
    } catch {
      // Templates endpoint may not exist yet -- show empty state
      setTemplates([])
    }
  }, [])

  useEffect(() => {
    if (isAuthenticated) {
      fetchStats()
      fetchTemplates()
    }
  }, [isAuthenticated, fetchStats, fetchTemplates])

  const handleSaveConfig = async () => {
    await save()
  }

  const handleTestSMS = async () => {
    if (!testNumber) {
      toast.error(t('admin.adminSMSSettings.pleaseEnterAPhoneNumber'))
      return
    }
    try {
      await api.post(`${API_BASE}/sms/staff/send`, { phone_number: testNumber, message: 'Test SMS from L30 library system.' })
      toast.success(t('toast.adminSMSSettings.testSmsSent'))
    } catch (_error: unknown) {
      toast.error(t('admin.adminSMSSettings.failedToSendTestSms'))
    }
  }

  const refreshAll = () => {
    fetchStats()
    fetchTemplates()
  }

  return (
    <SectionShell
      title="SMS Settings"
      description="Text message notifications for patrons who prefer texts. Includes quiet hours."
      tabs={[
        { id: 'config', label: 'Configuration', icon: Settings },
        { id: 'templates', label: 'Templates', icon: FileText },
        { id: 'stats', label: 'Statistics', icon: BarChart3 },
      ]}
      defaultTab="config"
      backLabel="Back to Outreach Dashboard"
      onBack={onBack}
    >
      {(activeTab) => (
        <div className="space-y-6">
          <div className="flex justify-end">
            <button
              type="button"
              onClick={refreshAll}
              className="flex items-center gap-2 px-4 py-2 text-lsc-rose dark:text-lsc-rose-light hover:bg-lsc-cream dark:hover:bg-lsc-brown/20 rounded-xl transition-colors"
            >
              <RefreshCw className="w-4 h-4" aria-hidden="true" />
              Refresh
            </button>
          </div>

          {activeTab === 'config' && (
            <>
              {isLoading ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" aria-hidden="true" />
                </div>
              ) : (
                <div className="space-y-6">
                  <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm p-6">
                    <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4">
                      Provider Status
                    </h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="flex items-center justify-between p-4 bg-lsc-cream/50 dark:bg-earth-700 rounded-lg">
                        <div>
                          <p className="font-medium text-lsc-dark dark:text-lsc-cream">
                            Provider: {config.provider || 'Not configured'}
                          </p>
                          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                            From: {config.from_number || 'Not set'}
                          </p>
                        </div>
                        <div
                          className={`flex items-center gap-2 ${
                            config.provider_enabled
                              ? 'text-status-success-600 dark:text-status-success-400'
                              : 'text-status-danger-600 dark:text-status-danger-400'
                          }`}
                        >
                          {config.provider_enabled ? (
                            <CheckCircle className="w-5 h-5" aria-hidden="true" />
                          ) : (
                            <AlertTriangle className="w-5 h-5" aria-hidden="true" />
                          )}
                          <span className="text-sm font-medium">
                            {config.provider_enabled ? 'Enabled' : 'Disabled'}
                          </span>
                        </div>
                      </div>
                      <div className="p-4 bg-lsc-cream/50 dark:bg-earth-700 rounded-lg">
                        <div className="flex items-center gap-2 mb-2">
                          <Phone className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" aria-hidden="true" />
                          <span className="font-medium text-lsc-dark dark:text-lsc-cream">Test SMS</span>
                        </div>
                        <div className="flex gap-2">
                          <input
                            type="tel"
                            value={testNumber}
                            onChange={(e) => setTestNumber(e.target.value)}
                            placeholder={t('placeholder.adminSMSSettings.1234567890')}
                            className="flex-1 px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
                          />
                          <button
                            type="button"
                            onClick={handleTestSMS}
                            className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90"
                          >
                            <TestTube2 className="w-4 h-4" aria-hidden="true" />
                            Test
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm p-6 space-y-4">
                    <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">Settings</h3>
                    <ToggleRow
                      label="SMS Enabled"
                      description="Enable or disable SMS notifications"
                      checked={config.provider_enabled}
                      onChange={(v) => setField('provider_enabled', v)}
                    />
                    <ToggleRow
                      label="Opt-In Required"
                      description="Require patrons to opt-in before receiving SMS"
                      checked={config.opt_in_required}
                      onChange={(v) => setField('opt_in_required', v)}
                    />
                    <ToggleRow
                      label="Marketing Messages"
                      description="Allow marketing and promotional messages"
                      checked={config.allow_marketing}
                      onChange={(v) => setField('allow_marketing', v)}
                    />
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <NumberField
                        label="Rate Limit (per hour)"
                        value={config.rate_limit_per_hour}
                        onChange={(v) => setField('rate_limit_per_hour', v)}
                      />
                      <NumberField
                        label="Rate Limit (per day)"
                        value={config.rate_limit_per_day}
                        onChange={(v) => setField('rate_limit_per_day', v)}
                      />
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                          Quiet Hours Start
                        </label>
                        <input
                          type="time"
                          value={config.quiet_hours_start || ''}
                          onChange={(e) => setField('quiet_hours_start', e.target.value)}
                          className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                          Quiet Hours End
                        </label>
                        <input
                          type="time"
                          value={config.quiet_hours_end || ''}
                          onChange={(e) => setField('quiet_hours_end', e.target.value)}
                          className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                        />
                      </div>
                    </div>
                    <div className="pt-4 border-t border-lsc-border dark:border-earth-700 flex justify-end">
                      <button
                        type="button"
                        onClick={handleSaveConfig}
                        disabled={isSaving}
                        className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 disabled:opacity-50"
                      >
                        {isSaving ? (
                          <Loader2 className="w-4 h-4 motion-safe:animate-spin" aria-hidden="true" />
                        ) : (
                          <Save className="w-4 h-4" aria-hidden="true" />
                        )}
                        Save Configuration
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}

          {activeTab === 'templates' && (
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm overflow-hidden">
              <div className="p-4 border-b border-lsc-border dark:border-earth-700">
                <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">SMS Templates</h3>
              </div>
              {templates.length === 0 ? (
                <div className="p-8 text-center">
                  <MessageSquare className="w-12 h-12 mx-auto text-lsc-dark/30 dark:text-lsc-cream/60 mb-4" aria-hidden="true" />
                  <p className="text-lsc-dark/70 dark:text-lsc-cream/70">No templates configured</p>
                </div>
              ) : (
                <div className="divide-y divide-lsc-border dark:divide-earth-700">
                  {templates.map((template) => (
                    <div key={template.id} className="p-4">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-lsc-dark dark:text-lsc-cream">
                            {template.name}
                          </span>
                          <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70">
                            {template.template_type}
                          </span>
                        </div>
                        <span
                          className={`px-2 py-0.5 text-xs font-medium rounded-full ${
                            template.is_active
                              ? 'bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-400'
                              : 'bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70'
                          }`}
                        >
                          {template.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </div>
                      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 bg-lsc-cream/50 dark:bg-earth-700 p-2 rounded">
                        {template.content}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {activeTab === 'stats' &&
            (stats ? (
              <StatGrid columns={5}>
                <StatCard title="Sent Today" value={stats.messages_sent_today} icon={Send} color="accent" />
                <StatCard
                  title="This Month"
                  value={stats.messages_sent_this_month}
                  icon={BarChart3}
                  color="accent"
                />
                <StatCard
                  title="Delivery Rate"
                  value={`${stats.delivery_rate_percent.toFixed(1)}%`}
                  icon={CheckCircle}
                  color="success"
                />
                <StatCard title="Opted In" value={stats.opt_in_count} icon={Bell} color="success" />
                <StatCard title="Opted Out" value={stats.opt_out_count} icon={AlertTriangle} color="amber" />
              </StatGrid>
            ) : (
              <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-8 text-center border border-lsc-border dark:border-earth-700">
                <BarChart3 className="w-12 h-12 text-lsc-dark/30 dark:text-lsc-cream/60 mx-auto mb-4" aria-hidden="true" />
                <p className="text-lsc-dark/70 dark:text-lsc-cream/70">No SMS statistics available yet</p>
              </div>
            ))}
        </div>
      )}
    </SectionShell>
  )
}

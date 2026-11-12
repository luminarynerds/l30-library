/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useState } from 'react'
import { fetchApi } from '@/api/fetchApi'
import { Key, Globe, Send, Save, RefreshCw, AlertTriangle } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useTranslation } from '@/i18n'
import {
  SettingsCard,
  SettingsGrid,
  TextField,
  NumberField,
  InfoBanner,
} from '@/components/admin'
import { useConfigurationSection } from '@/hooks/useConfigurationSection'
import { useOrganizationFeatures } from '@/contexts/OrganizationFeaturesContext'
import { SectionShell } from '../ai-settings/SectionShell'

interface EmailMarketingConfig extends Record<string, unknown> {
  email_domain: string
  sendgrid_api_key: string
  from_email: string
  email_daily_send_cap: number
  email_dedup_window_hours: number
  email_alert_threshold: number
}

type EmailKeySource = 'env' | 'db' | 'none'

const DEFAULT_EMAIL_MARKETING_CONFIG: EmailMarketingConfig = {
  email_domain: '',
  sendgrid_api_key: '',
  from_email: '',
  email_daily_send_cap: 500,
  email_dedup_window_hours: 24,
  email_alert_threshold: 100,
}

interface EmailStats {
  daily_count: number
  daily_cap: number
  hourly_count?: number
  cap_skipped_today?: number
  status?: string
}

function EmailSafeguardStatusBanner() {
  const [stats, setStats] = useState<EmailStats | null>(null)

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      try {
        const data = await fetchApi('/health/detailed', { credentials: 'include' })
        if (!cancelled && data?.checks?.email) {
          setStats(data.checks.email as EmailStats)
        }
      } catch {
        // ignore -- banner is best-effort
      }
    }
    void load()
    return () => {
      cancelled = true
    }
  }, [])

  if (!stats) return null
  const skipped = stats.cap_skipped_today ?? 0
  if (skipped <= 0) {
    return (
      <InfoBanner tone="info">
        Today: {stats.daily_count} of {stats.daily_cap} emails sent. No daily-cap
        suppressions.
      </InfoBanner>
    )
  }
  return (
    <div
      role="alert"
      className="rounded-lg border border-amber-300 bg-amber-50 p-4 dark:border-amber-700 dark:bg-amber-950"
    >
      <div className="flex items-start gap-3">
        <AlertTriangle className="w-5 h-5 mt-0.5 text-amber-700 dark:text-amber-300" aria-hidden="true" />
        <div className="text-sm text-amber-900 dark:text-amber-100">
          <strong>{skipped} email{skipped === 1 ? '' : 's'} suppressed by daily cap today.</strong>{' '}
          {stats.daily_count} of {stats.daily_cap} sent. Suppressed messages are recorded in the
          notification dead-letter queue but are NOT automatically re-delivered (content is not
          stored). Raise the cap below and re-send affected notifications manually if needed.
        </div>
      </div>
    </div>
  )
}

interface EmailMarketingSectionProps {
  onBack: () => void
}

export function EmailMarketingSection({ onBack }: EmailMarketingSectionProps) {
  const { t } = useTranslation()
  const { value: config, setField, loading, saving, save } =
    useConfigurationSection<EmailMarketingConfig>('email_marketing', DEFAULT_EMAIL_MARKETING_CONFIG, {
      successMessage: t('admin.adminMailchimpSettings.emailMarketingSettingsUpdatedSuccessfully'),
      errorMessage: t('toast.adminMailchimpSettings.failedToUpdateEmailMarketing'),
      defaultReason: 'Admin update via email marketing settings UI',
    })

  // The backend redacts the raw SendGrid key from the GET response and instead
  // returns `sendgrid_api_key_source` ('env' | 'db' | 'none'). When env is the
  // source, this admin form can't change it -- env is canonical.
  const { features } = useOrganizationFeatures()
  const emailMarketingMeta = (features?.configuration as Record<string, unknown> | null | undefined)
    ?.email_marketing as Record<string, unknown> | undefined
  const emailKeySource = (emailMarketingMeta?.sendgrid_api_key_source as EmailKeySource | undefined) ?? 'none'
  const isEnvManaged = emailKeySource === 'env'

  if (loading) {
    return (
      <SectionShell
        title="Email Delivery"
        description="Transactional email (Resend), sender identity, and send safeguards."
        tabs={[{ id: 'settings', label: 'Email Settings', icon: Send }]}
        defaultTab="settings"
        backLabel="Back to Outreach Dashboard"
        onBack={onBack}
      >
        {() => (
          <div className="flex items-center justify-center h-64">
            <RefreshCw className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" aria-hidden="true" />
          </div>
        )}
      </SectionShell>
    )
  }

  return (
    <SectionShell
      title="Email Delivery"
      description="Transactional email (Resend), sender identity, and send safeguards."
      tabs={[{ id: 'settings', label: 'Email Settings', icon: Send }]}
      defaultTab="settings"
      backLabel="Back to Outreach Dashboard"
      onBack={onBack}
    >
      {() => (
        <div className="space-y-6">
          <InfoBanner tone="info">
            Configure the transactional email key and send safeguards. API keys are stored
            securely and never displayed in full after saving.
          </InfoBanner>

          <SettingsCard title="Transactional Email (Resend)" icon={Key}>
            <TextField
              label="Resend API Key"
              type={isEnvManaged ? 'text' : 'password'}
              value={isEnvManaged ? '' : config.sendgrid_api_key}
              onChange={isEnvManaged ? () => {} : (v) => setField('sendgrid_api_key', v)}
              placeholder={
                isEnvManaged
                  ? '<set via environment variable>'
                  : 're_...'
              }
              disabled={isEnvManaged}
              help={
                isEnvManaged ? (
                  <>
                    Configured via environment variable. Contact your system administrator to
                    change it.{' '}
                    <Link to="/staff/admin/integrations" className="underline">
                      Test connection
                    </Link>
                  </>
                ) : undefined
              }
            />
            <SettingsGrid cols={2}>
              <TextField
                label="From Email"
                type="email"
                value={config.from_email}
                onChange={(v) => setField('from_email', v)}
              />
              <TextField
                label="Email Domain"
                value={config.email_domain}
                onChange={(v) => setField('email_domain', v)}
              />
            </SettingsGrid>
          </SettingsCard>

          <EmailSafeguardStatusBanner />

          <SettingsCard title="Email Safeguards" icon={Globe}>
            <SettingsGrid cols={3}>
              <NumberField
                label="Daily Send Cap"
                min={10}
                max={10000}
                value={config.email_daily_send_cap}
                onChange={(v) => setField('email_daily_send_cap', v)}
                help={t('admin.adminMailchimpSettings.maxEmailsPerDayTo')}
              />
              <NumberField
                label="Dedup Window"
                unit="hours"
                min={1}
                max={168}
                value={config.email_dedup_window_hours}
                onChange={(v) => setField('email_dedup_window_hours', v)}
                help={t('admin.adminMailchimpSettings.suppressDuplicateEmailsWithinThis')}
              />
              <NumberField
                label="Alert Threshold"
                unit="per hour"
                min={10}
                max={5000}
                value={config.email_alert_threshold}
                onChange={(v) => setField('email_alert_threshold', v)}
                help={t('admin.adminMailchimpSettings.alertAfterThisManyEmails')}
              />
            </SettingsGrid>
          </SettingsCard>

          <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm p-6 border border-lsc-border dark:border-earth-700">
            <button
              type="button"
              onClick={() => void save()}
              disabled={saving}
              className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-lg font-medium transition-colors bg-lsc-rose hover:bg-lsc-rose/90 text-white disabled:opacity-50"
            >
              {saving ? (
                <RefreshCw className="w-5 h-5 motion-safe:animate-spin" aria-hidden="true" />
              ) : (
                <Save className="w-5 h-5" aria-hidden="true" />
              )}
              {saving ? 'Saving...' : 'Save Email Settings'}
            </button>
          </div>
        </div>
      )}
    </SectionShell>
  )
}

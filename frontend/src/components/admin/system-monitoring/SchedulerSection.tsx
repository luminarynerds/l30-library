/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Clock, Timer, RotateCcw, Bell, AlertCircle } from 'lucide-react'
import { useTranslation } from '@/i18n'
import {
  SettingsFormPage,
  SettingsCard,
  SettingsGrid,
  NumberField,
  TextField,
  SelectField,
  ToggleRow,
  InfoBanner,
} from '@/components/admin'
import { useConfigurationSection } from '@/hooks/useConfigurationSection'
import { SectionShell } from '../ai-settings/SectionShell'

interface SchedulerConfig extends Record<string, unknown> {
  scheduler_enabled: boolean
  scheduler_timezone: string
  scheduler_job_store: string
  scheduler_retry_enabled: boolean
  scheduler_retry_max_attempts: number
  scheduler_retry_initial_delay: number
  scheduler_retry_max_delay: number
  overdue_notice_interval_days: number
  hold_expiry_days: number
  job_alert_enabled: boolean
  job_alert_email: string
  job_alert_warning_threshold: number
  job_alert_critical_threshold: number
  job_log_retention_days: number
}

const DEFAULT_SCHEDULER_CONFIG: SchedulerConfig = {
  scheduler_enabled: true,
  scheduler_timezone: 'UTC',
  scheduler_job_store: 'sqlalchemy',
  scheduler_retry_enabled: true,
  scheduler_retry_max_attempts: 3,
  scheduler_retry_initial_delay: 2.0,
  scheduler_retry_max_delay: 300.0,
  overdue_notice_interval_days: 7,
  hold_expiry_days: 7,
  job_alert_enabled: true,
  job_alert_email: '',
  job_alert_warning_threshold: 5.0,
  job_alert_critical_threshold: 15.0,
  job_log_retention_days: 90,
}

const TIMEZONE_OPTIONS = [
  { value: 'UTC', label: 'UTC' },
  { value: 'America/New_York', label: 'America/New_York' },
  { value: 'America/Chicago', label: 'America/Chicago' },
  { value: 'America/Denver', label: 'America/Denver' },
  { value: 'America/Los_Angeles', label: 'America/Los_Angeles' },
  { value: 'America/Anchorage', label: 'America/Anchorage' },
  { value: 'Pacific/Honolulu', label: 'Pacific/Honolulu' },
] as const

const JOB_STORE_OPTIONS = [
  { value: 'sqlalchemy', label: 'SQLAlchemy (Persistent)' },
  { value: 'memory', label: 'Memory (Non-persistent)' },
] as const

const TABS = [{ id: 'scheduler', label: 'Scheduler', icon: Clock }] as const

interface SchedulerSectionProps {
  onBack: () => void
}

export function SchedulerSection({ onBack }: SchedulerSectionProps) {
  const { t } = useTranslation()
  const { value: config, setField, loading, saving, save } = useConfigurationSection<SchedulerConfig>(
    'scheduler',
    DEFAULT_SCHEDULER_CONFIG,
    {
      successMessage: t('admin.adminSchedulerSettings.schedulerSettingsUpdatedSuccessfully'),
      errorMessage: t('toast.adminSchedulerSettings.failedToUpdateSchedulerSettings'),
      defaultReason: 'Admin update via scheduler settings UI',
    },
  )

  return (
    <SectionShell
      title="Scheduler"
      description="Background jobs that run automatically -- overdue notices, hold expiration, data cleanup. Controls when and how often they run."
      tabs={[...TABS]}
      backLabel="Back to System Dashboard"
      onBack={onBack}
    >
      {() => (
        <SettingsFormPage bare
          title="Scheduler Settings"
          icon={Clock}
          loading={loading}
          saving={saving}
          onSave={() => save()}
          banner={
            <InfoBanner tone="warning">
              The scheduler handles automated tasks like overdue notices, hold expiration, fine
              calculations, and data cleanup. Changes here affect when and how these background jobs run.
            </InfoBanner>
          }
        >
          <SettingsCard title="General" icon={Timer}>
            <SettingsGrid cols={2}>
              <ToggleRow
                label="Scheduler Enabled"
                description={t('admin.adminSchedulerSettings.enableOrDisableTheBackground')}
                checked={config.scheduler_enabled}
                onChange={(v) => setField('scheduler_enabled', v)}
              />
              <SelectField
                label="Timezone"
                value={config.scheduler_timezone}
                onChange={(v) => setField('scheduler_timezone', v)}
                options={TIMEZONE_OPTIONS}
              />
              <SelectField
                label="Job Store"
                value={config.scheduler_job_store}
                onChange={(v) => setField('scheduler_job_store', v)}
                options={JOB_STORE_OPTIONS}
                help={t('admin.adminSchedulerSettings.persistentStoreSurvivesRestarts')}
              />
              <NumberField
                label="Overdue Notice Interval"
                unit="days"
                min={1}
                max={30}
                value={config.overdue_notice_interval_days}
                onChange={(v) => setField('overdue_notice_interval_days', v)}
              />
              <NumberField
                label="Hold Expiry"
                unit="days"
                min={1}
                max={30}
                value={config.hold_expiry_days}
                onChange={(v) => setField('hold_expiry_days', v)}
                help={t('admin.adminSchedulerSettings.daysBeforeUnclaimedHoldsExpire')}
              />
              <NumberField
                label="Job Log Retention"
                unit="days"
                min={7}
                max={365}
                value={config.job_log_retention_days}
                onChange={(v) => setField('job_log_retention_days', v)}
              />
            </SettingsGrid>
          </SettingsCard>

          <SettingsCard title="Retry Policy" icon={RotateCcw}>
            <SettingsGrid cols={2}>
              <ToggleRow
                label="Retry Enabled"
                description={t('admin.adminSchedulerSettings.automaticallyRetryFailedJobs')}
                checked={config.scheduler_retry_enabled}
                onChange={(v) => setField('scheduler_retry_enabled', v)}
              />
              <NumberField
                label="Max Retry Attempts"
                min={1}
                max={10}
                value={config.scheduler_retry_max_attempts}
                onChange={(v) => setField('scheduler_retry_max_attempts', v)}
              />
              <NumberField
                label="Initial Delay"
                unit="seconds"
                min={0.5}
                max={60}
                step={0.5}
                value={config.scheduler_retry_initial_delay}
                onChange={(v) => setField('scheduler_retry_initial_delay', v)}
                help={t('admin.adminSchedulerSettings.waitTimeBeforeFirstRetry')}
              />
              <NumberField
                label="Max Delay"
                unit="seconds"
                min={10}
                max={3600}
                value={config.scheduler_retry_max_delay}
                onChange={(v) => setField('scheduler_retry_max_delay', v)}
                help={t('admin.adminSchedulerSettings.maximumWaitBetweenRetries')}
              />
            </SettingsGrid>
          </SettingsCard>

          <SettingsCard title="Job Alerting" icon={Bell}>
            <SettingsGrid cols={2}>
              <ToggleRow
                label="Alerts Enabled"
                description={t('admin.adminSchedulerSettings.sendAlertsWhenJobsFail')}
                checked={config.job_alert_enabled}
                onChange={(v) => setField('job_alert_enabled', v)}
              />
              <TextField
                label="Alert Email"
                type="email"
                value={config.job_alert_email}
                onChange={(v) => setField('job_alert_email', v)}
                placeholder={t('placeholder.adminSchedulerSettings.adminlibrarycom')}
                help={t('admin.adminSchedulerSettings.fallsBackToSystemFrom')}
              />
              <NumberField
                label="Warning Threshold"
                unit="%"
                min={1}
                max={50}
                step={0.5}
                value={config.job_alert_warning_threshold}
                onChange={(v) => setField('job_alert_warning_threshold', v)}
                help={
                  <>
                    <AlertCircle className="w-3 h-3 inline text-status-warning-500" aria-hidden="true" /> Alert
                    when failure rate exceeds this
                  </>
                }
              />
              <NumberField
                label="Critical Threshold"
                unit="%"
                min={5}
                max={100}
                step={0.5}
                value={config.job_alert_critical_threshold}
                onChange={(v) => setField('job_alert_critical_threshold', v)}
                help={
                  <>
                    <AlertCircle className="w-3 h-3 inline text-status-danger-500" aria-hidden="true" /> Critical
                    alert threshold
                  </>
                }
              />
            </SettingsGrid>
          </SettingsCard>
        </SettingsFormPage>
      )}
    </SectionShell>
  )
}

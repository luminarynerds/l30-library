/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Shield, Key, UserX, Lock, Info } from 'lucide-react'
import { useTranslation } from '@/i18n'
import {
  SettingsFormPage,
  SettingsCard,
  SettingsGrid,
  NumberField,
  ToggleRow,
  InfoBanner,
} from '@/components/admin'
import { useConfigurationSection } from '@/hooks/useConfigurationSection'
import { SectionShell } from '../ai-settings/SectionShell'

interface SecurityConfig extends Record<string, unknown> {
  access_token_expire_minutes: number
  refresh_token_expire_days: number
  max_login_attempts: number
  lockout_duration_minutes: number
  password_min_length: number
  token_blacklist_fail_closed: boolean
}

const DEFAULT_SECURITY_CONFIG: SecurityConfig = {
  access_token_expire_minutes: 15,
  refresh_token_expire_days: 3,
  max_login_attempts: 5,
  lockout_duration_minutes: 15,
  password_min_length: 10,
  token_blacklist_fail_closed: false,
}

const TABS = [{ id: 'security', label: 'Security', icon: Shield }] as const

interface SecuritySectionProps {
  onBack: () => void
}

export function SecuritySection({ onBack }: SecuritySectionProps) {
  const { t } = useTranslation()
  const { value: config, setField, loading, saving, save } = useConfigurationSection<SecurityConfig>(
    'security',
    DEFAULT_SECURITY_CONFIG,
    {
      successMessage: t('admin.adminSecuritySettings.securitySettingsUpdatedSuccessfully'),
      errorMessage: t('toast.adminSecuritySettings.failedToUpdateSecuritySettings'),
      defaultReason: 'Admin update via security settings UI',
    },
  )

  return (
    <SectionShell
      title="Security"
      description="Authentication and password rules. Controls how long sessions last and when accounts get locked."
      tabs={[...TABS]}
      backLabel="Back to System Dashboard"
      onBack={onBack}
    >
      {() => (
        <SettingsFormPage bare
          title="Security Settings"
          icon={Shield}
          loading={loading}
          saving={saving}
          onSave={() => save()}
          banner={
            <InfoBanner tone="danger">
              These settings control authentication and account security. Incorrect values can lock
              out users or weaken security. Changes take effect immediately for new sessions.
            </InfoBanner>
          }
        >
          <SettingsCard title="Token Configuration" icon={Key}>
            <SettingsGrid cols={2}>
              <NumberField
                label="Access Token Expiry"
                unit="minutes"
                min={5}
                max={1440}
                value={config.access_token_expire_minutes}
                onChange={(v) => setField('access_token_expire_minutes', v)}
                help={t('admin.adminSecuritySettings.howLongBeforeAnAccess')}
              />
              <NumberField
                label="Refresh Token Expiry"
                unit="days"
                min={1}
                max={90}
                value={config.refresh_token_expire_days}
                onChange={(v) => setField('refresh_token_expire_days', v)}
                help={t('admin.adminSecuritySettings.howLongAUserStays')}
              />
            </SettingsGrid>
            <ToggleRow
              label="Token Blacklist Fail-Closed"
              description={
                <>
                  When Redis is unavailable: <strong>ON</strong> = reject tokens (more secure, may cause
                  outages); <strong>OFF</strong> = allow tokens through (more available)
                </>
              }
              checked={config.token_blacklist_fail_closed}
              onChange={(v) => setField('token_blacklist_fail_closed', v)}
            />
          </SettingsCard>

          <SettingsCard title="Account Lockout" icon={UserX}>
            <SettingsGrid cols={3}>
              <NumberField
                label="Max Login Attempts"
                min={3}
                max={20}
                value={config.max_login_attempts}
                onChange={(v) => setField('max_login_attempts', v)}
                help={t('admin.adminSecuritySettings.failedAttemptsBeforeLockout')}
              />
              <NumberField
                label="Lockout Duration"
                unit="minutes"
                min={1}
                max={1440}
                value={config.lockout_duration_minutes}
                onChange={(v) => setField('lockout_duration_minutes', v)}
                help={t('admin.adminSecuritySettings.howLongAccountsAreLocked')}
              />
              <NumberField
                label="Minimum Password Length"
                min={8}
                max={128}
                value={config.password_min_length}
                onChange={(v) => setField('password_min_length', v)}
                help={t('admin.adminSecuritySettings.minimumCharactersRequiredForPasswords')}
              />
            </SettingsGrid>
          </SettingsCard>

          <SettingsCard title="Password Policy Summary" icon={Lock}>
            <div className="bg-earth-50 dark:bg-earth-700/50 rounded-lg p-4 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 space-y-2">
              <div className="flex items-center gap-2">
                <Info className="w-4 h-4 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
                <span>Minimum length: <strong>{config.password_min_length}</strong> characters</span>
              </div>
              <div className="flex items-center gap-2">
                <Info className="w-4 h-4 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
                <span>Account locks after <strong>{config.max_login_attempts}</strong> failed attempts for <strong>{config.lockout_duration_minutes}</strong> minutes</span>
              </div>
              <div className="flex items-center gap-2">
                <Info className="w-4 h-4 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
                <span>Sessions expire after <strong>{config.access_token_expire_minutes}</strong> minutes of inactivity</span>
              </div>
              <div className="flex items-center gap-2">
                <Info className="w-4 h-4 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
                <span>{t('admin.adminSecuritySettings.usersMustReLoginAfter')} <strong>{config.refresh_token_expire_days}</strong> days</span>
              </div>
            </div>
          </SettingsCard>
        </SettingsFormPage>
      )}
    </SectionShell>
  )
}

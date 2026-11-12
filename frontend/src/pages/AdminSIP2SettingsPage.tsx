/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Monitor, Wifi, Server, Shield, Settings } from 'lucide-react'
import { useTranslation } from '@/i18n'
import {
  SettingsFormPage,
  SettingsCard,
  SettingsGrid,
  TextField,
  NumberField,
  ToggleRow,
  InfoBanner,
} from '@/components/admin'
import { useConfigurationSection } from '@/hooks/useConfigurationSection'

interface SIP2Config extends Record<string, unknown> {
  sip2_enabled: boolean
  sip2_host: string
  sip2_port: number
  sip2_institution_id: string
  sip2_library_name: string
  sip2_require_checksum: boolean
  sip2_require_login: boolean
  sip2_use_tls: boolean
  sip2_tls_cert: string
  sip2_tls_key: string
  sip2_connection_timeout: number
  sip2_max_connections: number
}

// NOTE: sip2_institution_id default is still 'LSC' — pre-rebrand drift flagged
// by the audit. Changing it here would alter behavior for any installation that
// relies on the default; leaving it so this migration is behavior-preserving.
const DEFAULT_SIP2_CONFIG: SIP2Config = {
  sip2_enabled: false,
  sip2_host: '127.0.0.1',
  sip2_port: 6001,
  sip2_institution_id: 'LSC',
  sip2_library_name: 'L30 Community Library',
  sip2_require_checksum: true,
  sip2_require_login: true,
  sip2_use_tls: true,
  sip2_tls_cert: '',
  sip2_tls_key: '',
  sip2_connection_timeout: 300,
  sip2_max_connections: 100,
}

export default function AdminSIP2SettingsPage() {
  const { t } = useTranslation()
  const { value: config, setField, loading, saving, save } = useConfigurationSection<SIP2Config>(
    'sip2',
    DEFAULT_SIP2_CONFIG,
    {
      successMessage: t('admin.adminSIP2Settings.sipSettingsUpdatedSuccessfully'),
      errorMessage: t('toast.adminSIP2Settings.failedToUpdateSip2Settings'),
      defaultReason: 'Admin update via SIP2 settings UI',
    },
  )

  return (
      <SettingsFormPage
        title="SIP2 Self-Checkout Settings"
        icon={Monitor}
        loading={loading}
        saving={saving}
        onSave={() => save()}
        banner={
          <InfoBanner tone="info">
            SIP2 (Standard Interchange Protocol) enables communication between self-checkout kiosks
            and the library system. Configure connection details, security requirements, and capacity
            limits for kiosk integration.
          </InfoBanner>
        }
      >
        <SettingsCard title="Connection" icon={Wifi}>
          <ToggleRow
            label="SIP2 Enabled"
            description={t('admin.adminSIP2Settings.enableTheSipServerFor')}
            checked={config.sip2_enabled}
            onChange={(v) => setField('sip2_enabled', v)}
          />
          <SettingsGrid cols={2}>
            <TextField
              label="Host"
              value={config.sip2_host}
              onChange={(v) => setField('sip2_host', v)}
            />
            <NumberField
              label="Port"
              min={1}
              max={65535}
              value={config.sip2_port}
              onChange={(v) => setField('sip2_port', v)}
            />
            <TextField
              label="Institution ID"
              value={config.sip2_institution_id}
              onChange={(v) => setField('sip2_institution_id', v)}
            />
            <TextField
              label="Library Name"
              value={config.sip2_library_name}
              onChange={(v) => setField('sip2_library_name', v)}
            />
          </SettingsGrid>
        </SettingsCard>

        <SettingsCard title="Capacity" icon={Server}>
          <SettingsGrid cols={2}>
            <NumberField
              label="Connection Timeout"
              unit="seconds"
              min={30}
              max={3600}
              value={config.sip2_connection_timeout}
              onChange={(v) => setField('sip2_connection_timeout', v)}
              help={t('admin.adminSIP2Settings.idleTimeoutBeforeDisconnectingKiosk')}
            />
            <NumberField
              label="Max Connections"
              min={1}
              max={1000}
              value={config.sip2_max_connections}
              onChange={(v) => setField('sip2_max_connections', v)}
              help={t('admin.adminSIP2Settings.maximumSimultaneousKioskConnections')}
            />
          </SettingsGrid>
        </SettingsCard>

        <SettingsCard title="Security" icon={Shield}>
          <SettingsGrid cols={3}>
            <ToggleRow
              label="Require Login"
              description="Kiosks must authenticate"
              checked={config.sip2_require_login}
              onChange={(v) => setField('sip2_require_login', v)}
            />
            <ToggleRow
              label="Require Checksum"
              description="Validate message integrity"
              checked={config.sip2_require_checksum}
              onChange={(v) => setField('sip2_require_checksum', v)}
            />
            <ToggleRow
              label="Use TLS"
              description="Encrypt kiosk connections"
              checked={config.sip2_use_tls}
              onChange={(v) => setField('sip2_use_tls', v)}
            />
          </SettingsGrid>
          {config.sip2_use_tls && (
            <div className="pt-4 border-t border-lsc-border dark:border-earth-700">
              <SettingsGrid cols={2}>
                <TextField
                  label="TLS Certificate Path"
                  value={config.sip2_tls_cert}
                  onChange={(v) => setField('sip2_tls_cert', v)}
                  placeholder={t('placeholder.adminSIP2Settings.etcsslcertssip2crt')}
                />
                <TextField
                  label="TLS Key Path"
                  value={config.sip2_tls_key}
                  onChange={(v) => setField('sip2_tls_key', v)}
                  placeholder={t('placeholder.adminSIP2Settings.etcsslprivatesip2key')}
                />
              </SettingsGrid>
            </div>
          )}
        </SettingsCard>

        <SettingsCard title="Configuration Summary" icon={Settings}>
          <div className="bg-earth-50 dark:bg-earth-700/50 rounded-lg p-4 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 space-y-2">
            <div className="flex items-center gap-2">
              <span
                className={`w-2 h-2 rounded-full ${
                  config.sip2_enabled ? 'bg-status-success-500' : 'bg-status-danger-500'
                }`}
                aria-hidden="true"
              />
              <span>
                SIP2 Server: <strong>{config.sip2_enabled ? 'Enabled' : 'Disabled'}</strong>
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-earth-500" aria-hidden="true" />
              <span>
                Endpoint:{' '}
                <strong>
                  {config.sip2_host}:{config.sip2_port}
                </strong>
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span
                className={`w-2 h-2 rounded-full ${
                  config.sip2_use_tls ? 'bg-status-success-500' : 'bg-status-warning-500'
                }`}
                aria-hidden="true"
              />
              <span>
                Encryption: <strong>{config.sip2_use_tls ? 'TLS Enabled' : 'Unencrypted'}</strong>
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-earth-500" aria-hidden="true" />
              <span>
                Max Kiosks: <strong>{config.sip2_max_connections}</strong>
              </span>
            </div>
          </div>
        </SettingsCard>
      </SettingsFormPage>
  )
}

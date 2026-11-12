/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { ShieldCheck, Server } from 'lucide-react'
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
import { SectionShell } from '../ai-settings/SectionShell'

interface VirusScanConfig extends Record<string, unknown> {
  virus_scan_enabled: boolean
  virus_scan_fail_on_error: boolean
  clamav_socket: string
  clamav_host: string
  clamav_port: number
}

const DEFAULT_VIRUS_SCAN_CONFIG: VirusScanConfig = {
  virus_scan_enabled: true,
  virus_scan_fail_on_error: true,
  clamav_socket: '/var/run/clamav/clamd.sock',
  clamav_host: '',
  clamav_port: 3310,
}

const TABS = [{ id: 'virus-scan', label: 'Virus Scanning', icon: ShieldCheck }] as const

interface VirusScanSectionProps {
  onBack: () => void
}

export function VirusScanSection({ onBack }: VirusScanSectionProps) {
  const { t } = useTranslation()
  const { value: config, setField, loading, saving, save } =
    useConfigurationSection<VirusScanConfig>('virus_scan', DEFAULT_VIRUS_SCAN_CONFIG, {
      successMessage: t('admin.adminVirusScanSettings.virusScanningSettingsUpdatedSuccessfully'),
      errorMessage: t('toast.adminVirusScanSettings.failedToUpdateVirusScanning'),
      defaultReason: 'Admin update via virus scanning settings UI',
    })

  return (
    <SectionShell
      title="Virus Scanning"
      description="Scans uploaded files for malware using ClamAV before accepting them into the system."
      tabs={[...TABS]}
      backLabel="Back to System Dashboard"
      onBack={onBack}
    >
      {() => (
        <SettingsFormPage bare
          title="Virus Scanning Settings"
          icon={ShieldCheck}
          loading={loading}
          saving={saving}
          onSave={() => save()}
          banner={
            <InfoBanner tone="info">
              Virus scanning protects against malicious file uploads. Files uploaded by patrons and
              staff are scanned using ClamAV before being accepted into the system.
            </InfoBanner>
          }
        >
          <SettingsCard title="Scanning Policy" icon={ShieldCheck}>
            <SettingsGrid cols={2}>
              <ToggleRow
                label="Virus Scanning Enabled"
                description={t('admin.adminVirusScanSettings.scanAllUploadedFilesFor')}
                checked={config.virus_scan_enabled}
                onChange={(v) => setField('virus_scan_enabled', v)}
              />
              <ToggleRow
                label="Fail on Error"
                description={t('admin.adminVirusScanSettings.rejectUploadsIfScannerIs')}
                checked={config.virus_scan_fail_on_error}
                onChange={(v) => setField('virus_scan_fail_on_error', v)}
              />
            </SettingsGrid>
            {!config.virus_scan_fail_on_error && (
              <InfoBanner tone="danger">
                With fail-on-error disabled, files will be accepted even if the virus scanner is
                unavailable. This improves availability but may allow unscanned files through.
              </InfoBanner>
            )}
          </SettingsCard>

          <SettingsCard title="ClamAV Configuration" icon={Server}>
            <TextField
              label="Unix Socket Path"
              value={config.clamav_socket}
              onChange={(v) => setField('clamav_socket', v)}
              placeholder={t('placeholder.adminVirusScanSettings.varrunclamavclamdsock')}
              help={t('admin.adminVirusScanSettings.preferredConnectionMethodLeaveEmpty')}
            />
            <SettingsGrid cols={2}>
              <TextField
                label="TCP Host"
                value={config.clamav_host}
                onChange={(v) => setField('clamav_host', v)}
                placeholder={t('placeholder.adminVirusScanSettings.clamav')}
                help={t('admin.adminVirusScanSettings.usedWhenSocketPathIs')}
              />
              <NumberField
                label="TCP Port"
                min={1}
                max={65535}
                value={config.clamav_port}
                onChange={(v) => setField('clamav_port', v)}
              />
            </SettingsGrid>
          </SettingsCard>
        </SettingsFormPage>
      )}
    </SectionShell>
  )
}

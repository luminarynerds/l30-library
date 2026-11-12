/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { HardDrive, FolderOpen, Cloud, Lock } from 'lucide-react'
import { useTranslation } from '@/i18n'
import {
  SettingsFormPage,
  SettingsCard,
  SettingsGrid,
  SelectField,
  TextField,
  InfoBanner,
} from '@/components/admin'
import { useConfigurationSection } from '@/hooks/useConfigurationSection'
import { SectionShell } from '../ai-settings/SectionShell'
import { useAuth } from '@/contexts/AuthContext'

interface StorageConfig extends Record<string, unknown> {
  storage_backend: string
  storage_local_path: string
  s3_bucket: string
  s3_region: string
  s3_endpoint_url: string
}

const DEFAULT_STORAGE_CONFIG: StorageConfig = {
  storage_backend: 'local',
  storage_local_path: '/app/uploads',
  s3_bucket: '',
  s3_region: 'us-east-1',
  s3_endpoint_url: '',
}

const BACKEND_OPTIONS = [
  { value: 'local', label: 'Local Filesystem' },
  { value: 's3', label: 'Amazon S3 / S3-Compatible' },
] as const

const S3_REGION_OPTIONS = [
  { value: 'us-east-1', label: 'us-east-1' },
  { value: 'us-east-2', label: 'us-east-2' },
  { value: 'us-west-1', label: 'us-west-1' },
  { value: 'us-west-2', label: 'us-west-2' },
  { value: 'eu-west-1', label: 'eu-west-1' },
  { value: 'eu-central-1', label: 'eu-central-1' },
  { value: 'ap-southeast-1', label: 'ap-southeast-1' },
  { value: 'ap-northeast-1', label: 'ap-northeast-1' },
] as const

const TABS = [{ id: 'storage', label: 'Storage', icon: HardDrive }] as const

interface StorageSectionProps {
  onBack: () => void
}

const ADMIN_ROLES: ReadonlyArray<string> = ['super_admin', 'admin', 'director']

export function StorageSection({ onBack }: StorageSectionProps) {
  const { t } = useTranslation()
  const { user } = useAuth()
  const canEdit = user != null && ADMIN_ROLES.includes(user.role)
  const { value: config, setField, loading, saving, save } = useConfigurationSection<StorageConfig>(
    'storage',
    DEFAULT_STORAGE_CONFIG,
    {
      successMessage: t('admin.adminStorageSettings.storageSettingsUpdatedSuccessfully'),
      errorMessage: t('toast.adminStorageSettings.failedToUpdateStorageSettings'),
      defaultReason: 'Admin update via storage settings UI',
    },
  )

  return (
    <SectionShell
      title="Storage"
      description="Where uploaded files are stored. Choose between local disk or cloud storage (S3)."
      tabs={[...TABS]}
      backLabel="Back to System Dashboard"
      onBack={onBack}
    >
      {() => (
        <SettingsFormPage bare
          title="Storage Settings"
          icon={HardDrive}
          loading={loading}
          saving={saving}
          disabled={!canEdit}
          onSave={() => canEdit ? save() : undefined}
          banner={
            <>
              <InfoBanner tone="info">
                Configure where uploaded files (patron documents, cover images, digital assets) are stored.
                Local storage works for single-server deployments. S3 is required for horizontal scaling.
              </InfoBanner>
              {!canEdit && (
                <div className="flex items-center gap-2 p-3 bg-status-warning-50 dark:bg-status-warning-900/20 border border-status-warning-200 dark:border-status-warning-700 rounded-lg text-sm text-status-warning-800 dark:text-status-warning-200">
                  <Lock className="w-4 h-4 flex-shrink-0" aria-hidden="true" />
                  Admin access required to change storage settings.
                </div>
              )}
            </>
          }
        >
          <SettingsCard title="Storage Backend" icon={FolderOpen}>
            <SelectField
              label="Backend Type"
              value={config.storage_backend}
              onChange={(v) => canEdit && setField('storage_backend', v)}
              options={BACKEND_OPTIONS}
              disabled={!canEdit}
            />
          </SettingsCard>

          {config.storage_backend === 'local' && (
            <SettingsCard title="Local Storage" icon={FolderOpen}>
              <TextField
                label="Upload Directory"
                value={config.storage_local_path}
                onChange={(v) => canEdit && setField('storage_local_path', v)}
                help={t('admin.adminStorageSettings.absolutePathWhereUploadedFiles')}
                disabled={!canEdit}
              />
              <div className="bg-earth-50 dark:bg-earth-700/50 rounded-lg p-4 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                Local storage is suitable for single-server deployments. For multi-server or
                containerized deployments, use S3-compatible storage to ensure files are accessible from
                all instances.
              </div>
            </SettingsCard>
          )}

          {config.storage_backend === 's3' && (
            <SettingsCard title="S3 Configuration" icon={Cloud}>
              <SettingsGrid cols={2}>
                <TextField
                  label="Bucket Name"
                  value={config.s3_bucket}
                  onChange={(v) => canEdit && setField('s3_bucket', v)}
                  placeholder={t('placeholder.adminStorageSettings.bucketNameExample')}
                  disabled={!canEdit}
                />
                <SelectField
                  label="Region"
                  value={config.s3_region}
                  onChange={(v) => canEdit && setField('s3_region', v)}
                  options={S3_REGION_OPTIONS}
                  disabled={!canEdit}
                />
              </SettingsGrid>
              <TextField
                label="Custom Endpoint URL (optional)"
                value={config.s3_endpoint_url}
                onChange={(v) => canEdit && setField('s3_endpoint_url', v)}
                placeholder={t('placeholder.adminStorageSettings.httpss3customprovidercom')}
                help={t('admin.adminStorageSettings.forSCompatibleServicesMinio')}
                disabled={!canEdit}
              />
            </SettingsCard>
          )}
        </SettingsFormPage>
      )}
    </SectionShell>
  )
}

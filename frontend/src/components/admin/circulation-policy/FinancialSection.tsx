/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useMemo } from 'react'
import { TrendingUp, AlertCircle, Shield, User } from 'lucide-react'
import { useTranslation } from '@/i18n'
import { useOrganizationFeatures } from '@/contexts/OrganizationFeaturesContext'
import {
  SettingsCard, SettingsGrid, DiffField, AuditTrailAccordion,
  ChangesSummaryBanner, InfoBanner,
  type AuditTrailEntry,
} from '@/components/admin'
import { useConfigurationSection } from '@/hooks/useConfigurationSection'
import { SectionShell } from '../ai-settings/SectionShell'

interface FinancialConfig extends Record<string, unknown> {
  daily_fine_rate: number
  max_fine_per_user: number
  grace_period_days: number
  suspension_days: number
  damage_charge_none: number
  damage_charge_minor: number
  damage_charge_moderate: number
  damage_charge_major: number
  damage_charge_destroyed: number
  lost_item_replacement_cost: number
  lost_item_processing_fee: number
  lost_item_threshold_days: number
  max_claims_per_patron_per_year: number
}

const DEFAULT_FINANCIAL_CONFIG: FinancialConfig = {
  daily_fine_rate: 0.25,
  max_fine_per_user: 10.0,
  grace_period_days: 1,
  suspension_days: 30,
  damage_charge_none: 0.0,
  damage_charge_minor: 5.0,
  damage_charge_moderate: 15.0,
  damage_charge_major: 25.0,
  damage_charge_destroyed: 50.0,
  lost_item_replacement_cost: 20.0,
  lost_item_processing_fee: 5.0,
  lost_item_threshold_days: 14,
  max_claims_per_patron_per_year: 3,
}

const formatCurrency = (n: number): string =>
  new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(n)

interface FieldConfig {
  key: keyof FinancialConfig
  label: string
  description: string
  type: 'currency' | 'number'
  min: number
  max: number
  step: number
  section: 'fines' | 'damage' | 'lost' | 'claims'
  unit?: string
}

const getFieldConfigs = (t: (key: string) => string): FieldConfig[] => [
  { key: 'daily_fine_rate', label: 'Daily Fine Rate', description: t('admin.adminFinancialConfig.fineChargedPerDayFor'), type: 'currency', min: 0, max: 10, step: 0.01, section: 'fines' },
  { key: 'max_fine_per_user', label: t('admin.adminFinancialConfig.maximumFinePerUser'), description: t('admin.adminFinancialConfig.maximumFineAmountThatCan'), type: 'currency', min: 0, max: 1000, step: 0.01, section: 'fines' },
  { key: 'grace_period_days', label: 'Grace Period', description: t('admin.adminFinancialConfig.daysBeforeFinesAreApplied'), type: 'number', min: 0, max: 30, step: 1, section: 'fines', unit: 'days' },
  { key: 'suspension_days', label: 'Suspension Duration', description: t('admin.adminFinancialConfig.daysPatronIsSuspendedFor'), type: 'number', min: 1, max: 365, step: 1, section: 'fines', unit: 'days' },
  { key: 'damage_charge_none', label: 'No Damage Charge', description: t('admin.adminFinancialConfig.chargeWhenItemHasNo'), type: 'currency', min: 0, max: 100, step: 0.01, section: 'damage' },
  { key: 'damage_charge_minor', label: 'Minor Damage Charge', description: t('admin.adminFinancialConfig.chargeForMinorWearLoose'), type: 'currency', min: 0, max: 100, step: 0.01, section: 'damage' },
  { key: 'damage_charge_moderate', label: 'Moderate Damage Charge', description: t('admin.adminFinancialConfig.chargeForModerateDamageWater'), type: 'currency', min: 0, max: 100, step: 0.01, section: 'damage' },
  { key: 'damage_charge_major', label: 'Major Damage Charge', description: t('admin.adminFinancialConfig.chargeForMajorDamageBinding'), type: 'currency', min: 0, max: 500, step: 0.01, section: 'damage' },
  { key: 'damage_charge_destroyed', label: 'Destroyed Item Charge', description: t('admin.adminFinancialConfig.chargeWhenItemIsEffectively'), type: 'currency', min: 0, max: 500, step: 0.01, section: 'damage' },
  { key: 'lost_item_replacement_cost', label: 'Replacement Cost', description: t('admin.adminFinancialConfig.costToReplaceALost'), type: 'currency', min: 0, max: 1000, step: 0.01, section: 'lost' },
  { key: 'lost_item_processing_fee', label: 'Processing Fee', description: t('admin.adminFinancialConfig.administrativeFeeForProcessingLost'), type: 'currency', min: 0, max: 100, step: 0.01, section: 'lost' },
  { key: 'lost_item_threshold_days', label: 'Lost Item Threshold', description: t('admin.adminFinancialConfig.daysOverdueBeforeItemIs'), type: 'number', min: 1, max: 365, step: 1, section: 'lost', unit: 'days' },
  { key: 'max_claims_per_patron_per_year', label: t('admin.adminFinancialConfig.maxClaimsPerPatronPer'), description: t('admin.adminFinancialConfig.maximumNumberOfDamageLoss'), type: 'number', min: 0, max: 100, step: 1, section: 'claims', unit: 'claims' },
]

const TABS = [
  { id: 'fines', label: 'Fine Policies', icon: TrendingUp },
  { id: 'damage', label: 'Damage Charges', icon: AlertCircle },
  { id: 'lost', label: 'Lost Items', icon: Shield },
  { id: 'claims', label: 'Claims & Limits', icon: User },
] as const

interface FinancialSectionProps {
  onBack: () => void
}

export function FinancialSection({ onBack }: FinancialSectionProps) {
  const { t } = useTranslation()
  const { features } = useOrganizationFeatures()
  const fieldConfigs = useMemo(() => getFieldConfigs(t), [t])

  const {
    value: config,
    initialValue: beforeConfig,
    setField,
    loading,
    saving,
    dirty,
    changedFields,
    save,
  } = useConfigurationSection<FinancialConfig>('financial', DEFAULT_FINANCIAL_CONFIG, {
    successMessage: t('admin.adminFinancialConfig.financialConfigurationUpdatedSuccessfully'),
    errorMessage: t('toast.adminFinancialConfig.failedToUpdateFinancialConfiguration'),
    defaultReason: 'Admin update via financial configuration UI',
  })

  const [reason, setReason] = useState('')

  const auditHistory = useMemo<AuditTrailEntry[]>(() => {
    const raw = (features?.configuration as Record<string, unknown> | undefined)?.audit_history
    return Array.isArray(raw) ? (raw as AuditTrailEntry[]) : []
  }, [features])

  const fieldLabels = useMemo(() => {
    const labels: Record<string, string> = {}
    for (const f of fieldConfigs) labels[f.key as string] = f.label
    return labels
  }, [fieldConfigs])

  const summaryChanges = useMemo(() => {
    const out: Record<string, { before: string | number; after: string | number }> = {}
    for (const [key, change] of Object.entries(changedFields)) {
      if (!change) continue
      const fieldConfig = fieldConfigs.find((f) => f.key === (key as keyof FinancialConfig))
      const isCurrency = fieldConfig?.type === 'currency'
      out[key] = {
        before: isCurrency ? formatCurrency(change.before as number) : (change.before as number),
        after: isCurrency ? formatCurrency(change.after as number) : (change.after as number),
      }
    }
    return out
  }, [changedFields, fieldConfigs])

  const handleSave = async () => {
    if (!dirty) return
    const auditEntry: AuditTrailEntry = {
      timestamp: new Date().toISOString(),
      updated_by: features?.updated_by_id ? `User ${features.updated_by_id}` : 'Unknown',
      changes: Object.entries(summaryChanges).map(([field, { before, after }]) => ({ field, before, after })),
    }
    const nextHistory = [auditEntry, ...auditHistory.slice(0, 99)]
    await save(reason || undefined, { audit_history: nextHistory })
    setReason('')
  }

  if (loading) return null

  return (
    <SectionShell
      title="Fine Policies"
      description="Fines for overdue items, damage charges, lost item fees, and patron claim limits. What it costs when things go wrong."
      tabs={[...TABS]}
      defaultTab="fines"
      backLabel="Back to Circulation & Policy"
      onBack={onBack}
    >
      {(activeTab) => {
        const sectionFields = fieldConfigs.filter((f) => f.section === activeTab)
        const section = TABS.find((s) => s.id === activeTab)
        return (
          <div className="space-y-6">
            <InfoBanner tone="warning">
              <p className="font-semibold mb-1">Financial Impact</p>
              <p>These settings control fines, charges, and financial policies. Changes affect how patrons are charged. All changes are tracked in the audit history.</p>
            </InfoBanner>

            <SettingsCard title={section?.label ?? ''} {...(section?.icon ? { icon: section.icon } : {})}>
              <SettingsGrid cols={2}>
                {sectionFields.map((fieldConfig) => (
                  <DiffField
                    key={fieldConfig.key as string}
                    label={fieldConfig.label}
                    description={fieldConfig.description}
                    type={fieldConfig.type}
                    value={config[fieldConfig.key] as number}
                    beforeValue={beforeConfig[fieldConfig.key] as number}
                    onChange={(v) => setField(fieldConfig.key, v)}
                    min={fieldConfig.min}
                    max={fieldConfig.max}
                    step={fieldConfig.step}
                    {...(fieldConfig.unit != null ? { unit: fieldConfig.unit } : {})}
                    formatCurrency={formatCurrency}
                  />
                ))}
              </SettingsGrid>
            </SettingsCard>

            <AuditTrailAccordion entries={auditHistory} fieldLabelMap={fieldLabels} />

            <SettingsCard title="Reason for Changes (optional)">
              <textarea
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder={t('admin.adminFinancialConfig.describeWhyYouReMaking')}
                rows={3}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream text-sm"
              />
              {dirty && <ChangesSummaryBanner changes={summaryChanges} fieldLabels={fieldLabels} />}
            </SettingsCard>

            <button onClick={handleSave} disabled={saving || !dirty}
              className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 disabled:opacity-50 font-semibold">
              {saving ? 'Saving...' : dirty ? 'Save Financial Configuration' : 'No Changes to Save'}
            </button>
          </div>
        )
      }}
    </SectionShell>
  )
}

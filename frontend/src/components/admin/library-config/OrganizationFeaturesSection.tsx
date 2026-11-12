/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useEffect, useMemo, useState } from 'react'
import toast from 'react-hot-toast'
import { Settings, Save, RefreshCw, ChevronDown } from 'lucide-react'
import type { AgeGroupLimits, AgeGroupLimitConfig, FeatureRegistryEntry } from '@/api/organization-features-api'
import { applyFeaturePreset, getFeatureRegistry } from '@/api/organization-features-api'
import { useTranslation } from '@/i18n'
import ConfirmDialog from '@/components/ConfirmDialog'
import { SettingsCard, SettingsGrid, NumberField, ToggleRow, InfoBanner } from '@/components/admin'
import { useOrganizationFeaturesFields } from '@/hooks/useOrganizationFeaturesFields'
import { SectionShell } from '../ai-settings/SectionShell'
import { FEATURE_GROUPS } from './featureGroups'

type FeaturesFormData = Record<string, unknown>

type PartitionedToggle = { key: string; label: string; description: string }

const DEFAULT_AGE_GROUP_LIMITS: AgeGroupLimits = {
  juvenile: { max_checkouts: 5, max_holds: 3, checkout_duration_days: 14 },
  teen: { max_checkouts: 7, max_holds: 5, checkout_duration_days: 21 },
  adult: { max_checkouts: 10, max_holds: 10, checkout_duration_days: 28 },
  senior: { max_checkouts: 10, max_holds: 10, checkout_duration_days: 28 },
}

const NON_TOGGLE_DEFAULTS: FeaturesFormData = {
  default_daily_goal_minutes: 30,
  max_holds_per_patron: 10,
  max_checkouts_per_patron: 10,
  age_group_limits: null,
}

const TABS = [
  { id: 'toggles', label: 'Feature Toggles', icon: Settings },
  { id: 'limits', label: 'Limits & Defaults', icon: Settings },
] as const

interface OrganizationFeaturesSectionProps {
  onBack: () => void
}

export function OrganizationFeaturesSection({ onBack }: OrganizationFeaturesSectionProps) {
  const [registry, setRegistry] = useState<FeatureRegistryEntry[] | null>(null)
  const [registryError, setRegistryError] = useState(false)

  useEffect(() => {
    let cancelled = false
    getFeatureRegistry()
      .then((entries) => {
        if (cancelled) return
        setRegistry(entries)
      })
      .catch((error: unknown) => {
        if (cancelled) return
        Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
        setRegistryError(true)
        setRegistry([])
      })
    return () => { cancelled = true }
  }, [])

  if (registry === null) return null

  return (
    <OrganizationFeaturesSectionInner
      registry={registry}
      registryError={registryError}
      onBack={onBack}
    />
  )
}

interface InnerProps {
  registry: FeatureRegistryEntry[]
  registryError: boolean
  onBack: () => void
}

function OrganizationFeaturesSectionInner({ registry, registryError, onBack }: InnerProps) {
  const { t } = useTranslation()

  const defaults = useMemo<FeaturesFormData>(() => {
    const out: FeaturesFormData = { ...NON_TOGGLE_DEFAULTS }
    registry.forEach((feature) => { out[feature.key] = false })
    return out
  }, [registry])

  const { value: formData, setField, loading, saving, save, refresh } =
    useOrganizationFeaturesFields<FeaturesFormData>(defaults, {
      successMessage: t('admin.adminOrganizationFeatures.organizationFeaturesUpdatedSuccessfully'),
      errorMessage: t('toast.adminOrganizationFeatures.failedToUpdateOrganizationFeatures'),
    })

  const partitioned = useMemo(() => {
    const byKey = new Map(registry.map((e) => [e.key, e]))
    const claimed = new Set<string>()
    const groups = FEATURE_GROUPS.map((group) => ({
      id: group.id,
      title: group.title,
      items: group.toggles
        .map((t): PartitionedToggle | null => {
          const entry = byKey.get(t.key)
          if (!entry) return null
          claimed.add(t.key)
          return { key: t.key, label: entry.label, description: t.description }
        })
        .filter((x): x is PartitionedToggle => x !== null),
    })).filter((g) => g.items.length > 0)
    const other: PartitionedToggle[] = registry
      .filter((e) => !claimed.has(e.key))
      .sort((a, b) => a.label.localeCompare(b.label))
      .map((e) => ({ key: e.key, label: e.label, description: '' }))
    return { groups, other }
  }, [registry])

  const [reason, setReason] = useState('')
  const [ageGroupOpen, setAgeGroupOpen] = useState(false)
  const [applyingPreset, setApplyingPreset] = useState(false)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [confirmMessage, setConfirmMessage] = useState('')
  const [pendingAction, setPendingAction] = useState<(() => void) | null>(null)

  const handleApplyPreset = async (preset: 'barebones' | 'full' | 'small_library') => {
    const labels: Record<string, string> = { barebones: 'Barebones ILS', full: 'All Features', small_library: 'Small Library' }
    setConfirmMessage(`Apply the "${labels[preset]}" preset? This will change all feature toggles.`)
    setPendingAction(() => async () => {
      try {
        setApplyingPreset(true)
        await applyFeaturePreset(preset)
        await refresh()
        toast.success(`Applied "${labels[preset]}" preset`)
      } catch (error: unknown) {
        Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
        toast.error('Failed to apply preset')
      } finally {
        setApplyingPreset(false)
      }
    })
    setConfirmOpen(true)
  }

  const handleConfirm = () => {
    setConfirmOpen(false)
    if (pendingAction) void pendingAction()
    setPendingAction(null)
  }

  const handleSave = async () => {
    await save(reason || undefined)
    setReason('')
  }

  const ageGroupLimits = (formData.age_group_limits as AgeGroupLimits | null) ?? DEFAULT_AGE_GROUP_LIMITS

  const updateAgeGroup = (group: keyof AgeGroupLimits, field: keyof AgeGroupLimitConfig, value: number) => {
    const updated = { ...ageGroupLimits, [group]: { ...ageGroupLimits[group], [field]: value } }
    setField('age_group_limits', updated)
  }

  if (loading) return null

  return (
    <SectionShell
      title="Organization Features"
      description="Turn library features on or off. Gamification, reading programs, board tools, training, community features, self-checkout."
      tabs={[...TABS]}
      defaultTab="toggles"
      backLabel="Back to Library Configuration"
      onBack={onBack}
    >
      {(activeTab) => (
        <div className="space-y-6">
          {activeTab === 'toggles' && (
            <>
              <InfoBanner tone="info">
                <p>Use presets to quickly configure all features, or toggle individual features below.</p>
              </InfoBanner>
              <div className="flex gap-2 mb-4">
                {(['barebones', 'small_library', 'full'] as const).map((preset) => (
                  <button key={preset} onClick={() => handleApplyPreset(preset)} disabled={applyingPreset}
                    className="px-3 py-1.5 text-sm border border-lsc-border dark:border-earth-700 rounded-lg hover:bg-lsc-cream/50 dark:hover:bg-earth-700 disabled:opacity-50 text-lsc-dark dark:text-lsc-cream">
                    {preset === 'barebones' ? 'Barebones' : preset === 'small_library' ? 'Small Library' : 'All Features'}
                  </button>
                ))}
              </div>
              {registryError && (
                <SettingsCard title="Feature Toggles">
                  <InfoBanner tone="danger">
                    <p>Could not load the feature registry. Toggles unavailable until the page is reloaded.</p>
                  </InfoBanner>
                </SettingsCard>
              )}
              {partitioned.groups.map((group) => (
                <SettingsCard key={group.id} title={group.title}>
                  <div className="space-y-3">
                    {group.items.map((item) => (
                      <ToggleRow
                        key={item.key}
                        label={item.label}
                        description={item.description}
                        checked={Boolean(formData[item.key])}
                        onChange={(v) => setField(item.key, v)}
                      />
                    ))}
                  </div>
                </SettingsCard>
              ))}
              {partitioned.other.length > 0 && (
                <SettingsCard title="Other">
                  <div className="space-y-3">
                    {partitioned.other.map((item) => (
                      <ToggleRow
                        key={item.key}
                        label={item.label}
                        checked={Boolean(formData[item.key])}
                        onChange={(v) => setField(item.key, v)}
                      />
                    ))}
                  </div>
                </SettingsCard>
              )}
            </>
          )}

          {activeTab === 'limits' && (
            <>
              <SettingsCard title="Limits & Defaults">
                <SettingsGrid cols={3}>
                  <NumberField label="Daily Reading Goal (minutes)" value={formData.default_daily_goal_minutes as number} onChange={(v) => setField('default_daily_goal_minutes', v)} min={5} max={120} />
                  <NumberField label="Max Holds Per Patron" value={formData.max_holds_per_patron as number} onChange={(v) => setField('max_holds_per_patron', v)} min={1} max={50} />
                  <NumberField label="Max Checkouts Per Patron" value={formData.max_checkouts_per_patron as number} onChange={(v) => setField('max_checkouts_per_patron', v)} min={1} max={200} />
                </SettingsGrid>
              </SettingsCard>

              <div className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-lg">
                <button type="button" onClick={() => setAgeGroupOpen(!ageGroupOpen)}
                  className="w-full px-6 py-4 flex items-center justify-between text-left hover:bg-lsc-cream/30 dark:hover:bg-earth-700/50 transition-colors rounded-lg">
                  <span className="font-semibold text-lsc-dark dark:text-lsc-cream">Age-Group Circulation Limits</span>
                  <ChevronDown className={`w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70 transition-transform ${ageGroupOpen ? 'rotate-180' : ''}`} />
                </button>
                {ageGroupOpen && (
                  <div className="px-6 pb-6 space-y-4">
                    {(Object.keys(ageGroupLimits) as Array<keyof AgeGroupLimits>).map((group) => (
                      <div key={group} className="border border-lsc-border dark:border-earth-700 rounded-lg p-4">
                        <h4 className="font-medium text-lsc-dark dark:text-lsc-cream capitalize mb-3">{group}</h4>
                        <SettingsGrid cols={3}>
                          <NumberField label="Max Checkouts" value={ageGroupLimits[group].max_checkouts} onChange={(v) => updateAgeGroup(group, 'max_checkouts', v)} min={1} max={100} />
                          <NumberField label="Max Holds" value={ageGroupLimits[group].max_holds} onChange={(v) => updateAgeGroup(group, 'max_holds', v)} min={1} max={50} />
                          <NumberField label="Checkout Duration (days)" value={ageGroupLimits[group].checkout_duration_days} onChange={(v) => updateAgeGroup(group, 'checkout_duration_days', v)} min={1} max={90} />
                        </SettingsGrid>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </>
          )}

          <SettingsCard title="Reason for Changes (optional)">
            <textarea value={reason} onChange={(e) => setReason(e.target.value)}
              placeholder="Describe why you're making these changes..."
              rows={3}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream text-sm" />
          </SettingsCard>

          <div className="flex gap-3">
            <button onClick={handleSave} disabled={saving}
              className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 disabled:opacity-50 font-semibold">
              <Save className="h-4 w-4" /> {saving ? 'Saving...' : 'Save Features'}
            </button>
            <button onClick={() => void refresh()} disabled={saving}
              className="flex items-center gap-2 px-4 py-2 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream border border-lsc-border dark:border-earth-700 rounded-lg hover:bg-lsc-cream/50 dark:hover:bg-earth-700 disabled:opacity-50 font-semibold">
              <RefreshCw className="h-4 w-4" /> Discard
            </button>
          </div>

          <ConfirmDialog
            isOpen={confirmOpen}
            onCancel={() => setConfirmOpen(false)}
            onConfirm={handleConfirm}
            title="Apply Preset"
            message={confirmMessage}
          />
        </div>
      )}
    </SectionShell>
  )
}

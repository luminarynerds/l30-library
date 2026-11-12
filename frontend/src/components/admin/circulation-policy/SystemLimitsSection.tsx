/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useMemo, useState } from 'react'
import { Save, AlertTriangle, Users, BookOpen, Clock, Shield, Info, Loader2, RefreshCw } from 'lucide-react'
import { useTranslation } from '@/i18n'
import { InfoBanner } from '@/components/admin'
import { useOrganizationFeaturesFields } from '@/hooks/useOrganizationFeaturesFields'
import { SectionShell } from '../ai-settings/SectionShell'

interface SystemLimitsConfig extends Record<string, unknown> {
  coppa_age_threshold: number
  age_transition_threshold: number
  quiz_passing_threshold: number
  card_expiration_grace_period_days: number
  inactive_account_threshold_days: number
  claims_returned_review_period_days: number
}

interface LimitConfig {
  key: keyof SystemLimitsConfig
  label: string
  minValue: number
  maxValue: number
  unit: string
  impact: string
  readOnly?: boolean
  section: string
}

const DEFAULT_LIMITS: SystemLimitsConfig = {
  coppa_age_threshold: 13,
  age_transition_threshold: 18,
  quiz_passing_threshold: 70,
  card_expiration_grace_period_days: 30,
  inactive_account_threshold_days: 365,
  claims_returned_review_period_days: 14,
}

const TABS = [
  { id: 'age', label: 'Age & Compliance', icon: Shield },
  { id: 'circulation', label: 'Circulation Limits', icon: BookOpen },
  { id: 'inactive', label: 'Inactive Accounts', icon: Users },
  { id: 'content', label: 'Content Limits', icon: Clock },
] as const

interface SystemLimitsSectionProps {
  onBack: () => void
}

export function SystemLimitsSection({ onBack }: SystemLimitsSectionProps) {
  const { t } = useTranslation()

  const limitConfigs: LimitConfig[] = useMemo(() => [
    { key: 'coppa_age_threshold', label: 'COPPA Age Threshold', minValue: 13, maxValue: 18, unit: 'years', readOnly: true, impact: 'Set by U.S. federal law (COPPA). Cannot be changed.', section: 'age' },
    { key: 'age_transition_threshold', label: 'Age Transition Threshold', minValue: 13, maxValue: 25, unit: 'years', impact: 'Age at which juvenile accounts transition to adult accounts.', section: 'age' },
    { key: 'quiz_passing_threshold', label: 'Quiz Passing Threshold', minValue: 50, maxValue: 100, unit: '%', impact: 'Minimum score to pass learning quizzes and complete courses.', section: 'circulation' },
    { key: 'card_expiration_grace_period_days', label: t('admin.adminSystemLimits.cardExpirationGracePeriod'), minValue: 0, maxValue: 180, unit: 'days', impact: 'Days after card expiration during which patrons can still use their library card.', section: 'circulation' },
    { key: 'inactive_account_threshold_days', label: 'Inactive Account Threshold', minValue: 90, maxValue: 1825, unit: 'days', impact: 'Time of inactivity before account is marked for cleanup.', section: 'inactive' },
    { key: 'claims_returned_review_period_days', label: t('admin.adminSystemLimits.claimsReturnedReviewPeriod'), minValue: 3, maxValue: 90, unit: 'days', impact: 'Time for staff to review patron claims of item returns before marking as lost.', section: 'content' },
  ], [t])

  const { value: limits, setField, loading, saving, save, refresh } =
    useOrganizationFeaturesFields<SystemLimitsConfig>(DEFAULT_LIMITS, {
      successMessage: t('admin.adminSystemLimits.systemLimitsUpdatedSuccessfully'),
      errorMessage: t('toast.adminSystemLimits.failedToUpdateSystemLimits'),
    })

  const [errors, setErrors] = useState<Record<string, string>>({})

  const validate = (key: keyof SystemLimitsConfig, value: number): string => {
    const config = limitConfigs.find((c) => c.key === key)
    if (!config) return ''
    if (isNaN(value)) return 'Please enter a valid number'
    if (value < config.minValue) return `Minimum value is ${config.minValue}`
    if (value > config.maxValue) return `Maximum value is ${config.maxValue}`
    if (key === 'coppa_age_threshold' && value !== 13) return 'COPPA threshold is regulated by law and cannot be changed'
    return ''
  }

  const handleChange = (key: keyof SystemLimitsConfig, value: number) => {
    setField(key, value as SystemLimitsConfig[typeof key])
    const error = validate(key, value)
    setErrors((prev) => {
      if (error) return { ...prev, [key]: error }
      const next = { ...prev }; delete next[key]; return next
    })
  }

  const handleSave = async () => {
    const newErrors: Record<string, string> = {}
    ;(Object.keys(limits) as Array<keyof SystemLimitsConfig>).forEach((key) => {
      const error = validate(key, limits[key] as number)
      if (error) newErrors[key] = error
    })
    if (Object.keys(newErrors).length > 0) { setErrors(newErrors); return }
    await save()
  }

  if (loading) return <div className="flex justify-center py-12"><Loader2 className="h-8 w-8 motion-safe:animate-spin text-lsc-rose" /></div>

  const renderLimit = (config: LimitConfig) => {
    const value = limits[config.key] as number
    const error = errors[config.key]
    return (
      <div key={config.key} className="mb-6 pb-6 border-b border-lsc-border dark:border-earth-700 last:border-b-0 last:mb-0 last:pb-0">
        <div className="grid md:grid-cols-2 gap-6">
          <div>
            <label className="block text-sm font-semibold text-lsc-dark dark:text-lsc-cream mb-2">
              {config.label}
              {config.readOnly && <span className="ml-2 text-xs font-normal text-status-danger-600 dark:text-status-danger-400">(Read-only)</span>}
            </label>
            <input type="number" value={value}
              onChange={(e) => handleChange(config.key, parseFloat(e.target.value))}
              disabled={saving || config.readOnly}
              min={config.minValue} max={config.maxValue}
              className={`w-full px-4 py-2 border rounded-lg mb-2 font-semibold text-lg transition-colors ${error ? 'border-status-danger-500 bg-status-danger-50 dark:bg-status-danger-900/20' : 'border-lsc-border dark:border-earth-700'} disabled:opacity-50 disabled:cursor-not-allowed text-lsc-dark dark:text-lsc-cream bg-lsc-white dark:bg-lsc-brown`} />
            {error && (
              <div className="flex items-start gap-2 text-status-danger-600 dark:text-status-danger-400 text-sm mb-2">
                <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" aria-hidden="true" />
                <span>{error}</span>
              </div>
            )}
            <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 space-y-1">
              <p><strong>Current:</strong> {value} {config.unit}</p>
              <p><strong>Range:</strong> {config.minValue} - {config.maxValue} {config.unit}</p>
            </div>
          </div>
          <div className="bg-earth-50 dark:bg-earth-800/20 border border-lsc-border dark:border-earth-700 rounded-lg p-4">
            <div className="flex items-start gap-2">
              <Info className="w-5 h-5 text-lsc-rose flex-shrink-0 mt-0.5" aria-hidden="true" />
              <div>
                <p className="font-semibold text-earth-900 dark:text-lsc-rose-light/80 text-sm mb-1">Impact</p>
                <p className="text-earth-800 dark:text-lsc-rose-light text-sm">{config.impact}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <SectionShell
      title="System Limits"
      description="Age thresholds, quiz passing scores, card expiration grace periods, and inactive account cleanup."
      tabs={[...TABS]}
      defaultTab="age"
      backLabel="Back to Circulation & Policy"
      onBack={onBack}
    >
      {(activeTab) => {
        const sectionLimits = limitConfigs.filter((c) => c.section === activeTab)
        return (
          <div className="space-y-6">
            <InfoBanner tone="warning">
              <p className="font-semibold mb-1">Compliance Notice</p>
              <p>Changes to system limits have library-wide implications. COPPA age thresholds are regulated by U.S. federal law.</p>
            </InfoBanner>

            <div className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-lg p-6">
              {sectionLimits.map((config) => renderLimit(config))}
            </div>

            <div className="flex gap-3">
              <button onClick={handleSave} disabled={saving || Object.keys(errors).length > 0}
                className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 disabled:opacity-50 font-semibold">
                <Save className="h-4 w-4" /> {saving ? 'Saving...' : 'Save Changes'}
              </button>
              <button onClick={() => void refresh()} disabled={saving}
                className="flex items-center gap-2 px-4 py-2 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream border border-lsc-border dark:border-earth-700 rounded-lg hover:bg-lsc-cream/50 dark:hover:bg-earth-700 disabled:opacity-50 font-semibold">
                <RefreshCw className="h-4 w-4" /> Discard Changes
              </button>
            </div>
          </div>
        )
      }}
    </SectionShell>
  )
}

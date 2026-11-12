/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import toast from 'react-hot-toast'
import { Users, CreditCard, Shield, Bell, UserPlus, Pencil, X, Check } from 'lucide-react'
import { t } from '@/i18n'
import { useConfigurationSection } from '@/hooks/useConfigurationSection'
import { InfoBanner } from '@/components/admin'
import { SectionShell } from '../ai-settings/SectionShell'

const safeInt = (val: string, fallback: number) => { const n = parseInt(val); return isNaN(n) ? fallback : n }

interface PatronTypePolicy {
  checkout_limit: number
  hold_limit: number
  loan_period_days: number
  renewal_limit: number
  fine_rate: string
}

interface PatronSettingsConfig extends Record<string, unknown> {
  allow_self_registration: boolean
  require_email_verification: boolean
  require_address_verification: boolean
  minimum_age_for_self_registration: number
  allow_guardian_registration: boolean
  default_patron_type: string
  card_expiry_years: number
  grace_period_days: number
  allow_renewal_online: boolean
  auto_renew_before_expiry: boolean
  require_id_for_renewal: boolean
  card_number_format: string
  default_reading_history_tracking: boolean
  allow_opt_out_of_history: boolean
  data_retention_years: number
  anonymous_usage_statistics: boolean
  coppa_compliance_for_minors: boolean
  default_notification_method: string
  send_welcome_message: boolean
  send_expiry_reminders: boolean
  reminder_days_before_expiry: number
  allow_marketing_communications: boolean
  patron_type_policies: Record<string, PatronTypePolicy>
}

const DEFAULT_CONFIG: PatronSettingsConfig = {
  allow_self_registration: true,
  require_email_verification: true,
  require_address_verification: false,
  minimum_age_for_self_registration: 13,
  allow_guardian_registration: true,
  default_patron_type: 'Adult',
  card_expiry_years: 3,
  grace_period_days: 30,
  allow_renewal_online: true,
  auto_renew_before_expiry: false,
  require_id_for_renewal: true,
  card_number_format: 'LIB-{YYYY}-{SEQ}',
  default_reading_history_tracking: false,
  allow_opt_out_of_history: true,
  data_retention_years: 3,
  anonymous_usage_statistics: true,
  coppa_compliance_for_minors: true,
  default_notification_method: 'Email',
  send_welcome_message: true,
  send_expiry_reminders: true,
  reminder_days_before_expiry: 30,
  allow_marketing_communications: false,
  patron_type_policies: {
    Adult: { checkout_limit: 50, hold_limit: 15, loan_period_days: 21, renewal_limit: 3, fine_rate: '0.25' },
    Juvenile: { checkout_limit: 25, hold_limit: 10, loan_period_days: 21, renewal_limit: 3, fine_rate: '0.00' },
    'Teen/Young Adult': { checkout_limit: 35, hold_limit: 12, loan_period_days: 21, renewal_limit: 3, fine_rate: '0.10' },
    Senior: { checkout_limit: 50, hold_limit: 15, loan_period_days: 28, renewal_limit: 5, fine_rate: '0.00' },
    Homebound: { checkout_limit: 30, hold_limit: 10, loan_period_days: 42, renewal_limit: 5, fine_rate: '0.00' },
    Educator: { checkout_limit: 75, hold_limit: 25, loan_period_days: 35, renewal_limit: 5, fine_rate: '0.10' },
    'Non-Resident': { checkout_limit: 15, hold_limit: 5, loan_period_days: 14, renewal_limit: 2, fine_rate: '0.50' },
    Institutional: { checkout_limit: 100, hold_limit: 30, loan_period_days: 28, renewal_limit: 3, fine_rate: '0.25' },
    Temporary: { checkout_limit: 5, hold_limit: 2, loan_period_days: 14, renewal_limit: 1, fine_rate: '0.50' },
  },
}

const TABS = [
  { id: 'types', label: 'Patron Types', icon: Users },
  { id: 'registration', label: 'Registration', icon: UserPlus },
  { id: 'cards', label: 'Card Policies', icon: CreditCard },
  { id: 'privacy', label: 'Privacy & Data', icon: Shield },
  { id: 'comms', label: 'Communications', icon: Bell },
] as const

interface PatronSettingsSectionProps {
  onBack: () => void
}

export function PatronSettingsSection({ onBack }: PatronSettingsSectionProps) {
  const { value: config, setField, loading, saving, save } =
    useConfigurationSection<PatronSettingsConfig>('patron_settings', DEFAULT_CONFIG, {
      successMessage: 'Patron settings saved successfully',
      errorMessage: 'Failed to save patron settings',
      defaultReason: 'Admin update via patron settings UI',
    })

  const [editingName, setEditingName] = useState<string | null>(null)
  const [editingPolicy, setEditingPolicy] = useState<PatronTypePolicy | null>(null)

  const patronTypeNames = Object.keys(config.patron_type_policies)

  const handleEditType = (name: string) => {
    setEditingName(name)
    setEditingPolicy({ ...config.patron_type_policies[name]! })
  }

  const handleCancelEdit = () => { setEditingName(null); setEditingPolicy(null) }

  const handleSaveType = () => {
    if (!editingName || !editingPolicy) return
    setField('patron_type_policies', { ...config.patron_type_policies, [editingName]: editingPolicy })
    setEditingName(null)
    setEditingPolicy(null)
    toast.success(t('toast.adminPatronSettings.patronTypeUpdated'))
  }

  const toggleField = (field: keyof PatronSettingsConfig) => {
    setField(field, !config[field] as PatronSettingsConfig[typeof field])
  }

  const renderToggle = (value: boolean, onToggle: () => void, label?: string) => (
    <button type="button" role="switch" aria-checked={value} aria-label={label} onClick={onToggle}
      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${value ? 'bg-lsc-rose' : 'bg-earth-200 dark:bg-earth-700'}`}>
      <span className={`inline-block h-4 w-4 transform rounded-full bg-lsc-white dark:bg-earth-800 transition-transform ${value ? 'translate-x-6' : 'translate-x-1'}`} />
    </button>
  )

  if (loading) return null

  return (
    <SectionShell
      title="Patron Types & Policies"
      description="Registration rules, library card policies, privacy settings, and communication defaults. How patrons join and stay."
      tabs={[...TABS]}
      defaultTab="types"
      backLabel="Back to Circulation & Policy"
      onBack={onBack}
    >
      {(activeTab) => (
        <div className="space-y-6">
          {activeTab === 'types' && (
            <>
              <InfoBanner tone="info">
                <p>Per-type fine rates override the global rate set in Fine Policies.</p>
              </InfoBanner>
              <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 p-6">
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-lsc-border dark:border-earth-700">
                        <th className="text-left py-3 px-2 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Name</th>
                        <th className="text-left py-3 px-2 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Checkout Limit</th>
                        <th className="text-left py-3 px-2 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Hold Limit</th>
                        <th className="text-left py-3 px-2 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Loan Period</th>
                        <th className="text-left py-3 px-2 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Renewals</th>
                        <th className="text-left py-3 px-2 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Fine Rate</th>
                        <th className="text-right py-3 px-2 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {patronTypeNames.map((name) => {
                        const policy = config.patron_type_policies[name]!
                        const isEditing = editingName === name && editingPolicy
                        return (
                          <tr key={name} className="border-b border-earth-100 dark:border-earth-700">
                            <td className="py-2 px-2 text-lsc-dark dark:text-lsc-cream font-medium">{name}</td>
                            {isEditing ? (
                              <>
                                <td className="py-2 px-2"><input type="number" min="1" max="200" value={editingPolicy.checkout_limit} onChange={(e) => setEditingPolicy({ ...editingPolicy, checkout_limit: safeInt(e.target.value, 0) })} className="w-20 px-2 py-1 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream" /></td>
                                <td className="py-2 px-2"><input type="number" min="1" max="100" value={editingPolicy.hold_limit} onChange={(e) => setEditingPolicy({ ...editingPolicy, hold_limit: safeInt(e.target.value, 0) })} className="w-20 px-2 py-1 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream" /></td>
                                <td className="py-2 px-2"><input type="number" min="1" max="365" value={editingPolicy.loan_period_days} onChange={(e) => setEditingPolicy({ ...editingPolicy, loan_period_days: safeInt(e.target.value, 0) })} className="w-20 px-2 py-1 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream" /></td>
                                <td className="py-2 px-2"><input type="number" min="0" max="10" value={editingPolicy.renewal_limit} onChange={(e) => setEditingPolicy({ ...editingPolicy, renewal_limit: safeInt(e.target.value, 0) })} className="w-20 px-2 py-1 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream" /></td>
                                <td className="py-2 px-2"><input type="number" min="0" max="10" step="0.01" value={editingPolicy.fine_rate} onChange={(e) => setEditingPolicy({ ...editingPolicy, fine_rate: e.target.value })} className="w-20 px-2 py-1 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream" /></td>
                                <td className="py-2 px-2 text-right">
                                  <div className="flex items-center justify-end gap-1">
                                    <button onClick={handleSaveType} className="inline-flex items-center justify-center min-w-[44px] min-h-[44px] p-1.5 text-status-success-600 hover:bg-status-success-50 dark:hover:bg-status-success-900/20 rounded-lg" aria-label={`Save ${name}`}><Check className="w-4 h-4" /></button>
                                    <button onClick={handleCancelEdit} className="inline-flex items-center justify-center min-w-[44px] min-h-[44px] p-1.5 text-earth-600 hover:bg-earth-100 dark:hover:bg-earth-700 rounded-lg" aria-label="Cancel editing"><X className="w-4 h-4" /></button>
                                  </div>
                                </td>
                              </>
                            ) : (
                              <>
                                <td className="py-2 px-2 text-lsc-dark/70 dark:text-lsc-cream/70">{policy.checkout_limit}</td>
                                <td className="py-2 px-2 text-lsc-dark/70 dark:text-lsc-cream/70">{policy.hold_limit}</td>
                                <td className="py-2 px-2 text-lsc-dark/70 dark:text-lsc-cream/70">{policy.loan_period_days}</td>
                                <td className="py-2 px-2 text-lsc-dark/70 dark:text-lsc-cream/70">{policy.renewal_limit}</td>
                                <td className="py-2 px-2 text-lsc-dark/70 dark:text-lsc-cream/70">${policy.fine_rate}</td>
                                <td className="py-2 px-2 text-right">
                                  <button onClick={() => handleEditType(name)} className="inline-flex items-center justify-center min-w-[44px] min-h-[44px] p-1.5 text-status-warning-600 hover:bg-status-warning-50 dark:hover:bg-status-warning-900/20 rounded-lg" aria-label={`Edit ${name}`}><Pencil className="w-4 h-4" /></button>
                                </td>
                              </>
                            )}
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          )}

          {activeTab === 'registration' && (
            <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 p-6 space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="flex items-center">{renderToggle(config.allow_self_registration as boolean, () => toggleField('allow_self_registration'), 'Allow self-registration')}<span className="ml-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Allow self-registration</span></div>
                <div className="flex items-center">{renderToggle(config.require_email_verification as boolean, () => toggleField('require_email_verification'), 'Require email verification')}<span className="ml-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Require email verification</span></div>
                <div className="flex items-center">{renderToggle(config.require_address_verification as boolean, () => toggleField('require_address_verification'), 'Require address verification')}<span className="ml-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Require address verification</span></div>
                <div className="flex items-center">{renderToggle(config.allow_guardian_registration as boolean, () => toggleField('allow_guardian_registration'), 'Allow guardian registration')}<span className="ml-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Allow guardian registration for minors</span></div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-4 border-t border-lsc-border dark:border-earth-700">
                <div>
                  <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Minimum age for self-registration</label>
                  <input type="number" min="0" max="18" value={config.minimum_age_for_self_registration as number} onChange={(e) => setField('minimum_age_for_self_registration', safeInt(e.target.value, 0))} className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Default patron type</label>
                  <select value={config.default_patron_type as string} onChange={(e) => setField('default_patron_type', e.target.value)} className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream">
                    {patronTypeNames.map((name) => <option key={name} value={name}>{name}</option>)}
                  </select>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'cards' && (
            <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 p-6 space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Card expiry period (years)</label>
                  <input type="number" min="1" max="10" value={config.card_expiry_years as number} onChange={(e) => setField('card_expiry_years', safeInt(e.target.value, 1))} className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Grace period after expiry (days)</label>
                  <input type="number" min="0" max="365" value={config.grace_period_days as number} onChange={(e) => setField('grace_period_days', safeInt(e.target.value, 0))} className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Card number format</label>
                  <input type="text" value={config.card_number_format as string} onChange={(e) => setField('card_number_format', e.target.value)} className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream" />
                </div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-4 border-t border-lsc-border dark:border-earth-700">
                <div className="flex items-center">{renderToggle(config.allow_renewal_online as boolean, () => toggleField('allow_renewal_online'), 'Allow renewal online')}<span className="ml-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Allow renewal online</span></div>
                <div className="flex items-center">{renderToggle(config.auto_renew_before_expiry as boolean, () => toggleField('auto_renew_before_expiry'), 'Auto-renew before expiry')}<span className="ml-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Auto-renew before expiry</span></div>
                <div className="flex items-center">{renderToggle(config.require_id_for_renewal as boolean, () => toggleField('require_id_for_renewal'), 'Require ID for renewal')}<span className="ml-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Require ID for card renewal</span></div>
              </div>
            </div>
          )}

          {activeTab === 'privacy' && (
            <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 p-6 space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <div className="flex items-center">{renderToggle(config.default_reading_history_tracking as boolean, () => toggleField('default_reading_history_tracking'), 'Default reading history tracking')}<span className="ml-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Default reading history tracking</span></div>
                  <p className="text-xs text-status-warning-700 dark:text-status-warning-400 mt-1 ml-14">Warning: Enabling this by default may raise patron privacy concerns.</p>
                </div>
                <div className="flex items-center">{renderToggle(config.allow_opt_out_of_history as boolean, () => toggleField('allow_opt_out_of_history'), 'Allow opt out')}<span className="ml-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Allow patrons to opt out of history</span></div>
                <div className="flex items-center">{renderToggle(config.anonymous_usage_statistics as boolean, () => toggleField('anonymous_usage_statistics'), 'Anonymous usage statistics')}<span className="ml-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Anonymous usage statistics</span></div>
                <div>
                  <div className="flex items-center">{renderToggle(config.coppa_compliance_for_minors as boolean, () => toggleField('coppa_compliance_for_minors'), 'COPPA compliance')}<span className="ml-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">COPPA compliance for minors</span></div>
                  <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1 ml-14">Enforces COPPA requirements for patrons under 13.</p>
                </div>
              </div>
              <div className="pt-4 border-t border-lsc-border dark:border-earth-700 max-w-xs">
                <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Data retention period (years)</label>
                <input type="number" min="1" max="10" value={config.data_retention_years as number} onChange={(e) => setField('data_retention_years', safeInt(e.target.value, 1))} className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream" />
              </div>
            </div>
          )}

          {activeTab === 'comms' && (
            <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 p-6 space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Default notification method</label>
                  <select value={config.default_notification_method as string} onChange={(e) => setField('default_notification_method', e.target.value)} className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream">
                    <option value="Email">Email</option>
                    <option value="SMS">SMS</option>
                    <option value="Both">Both</option>
                    <option value="None">None</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Reminder days before expiry</label>
                  <input type="number" min="1" max="90" value={config.reminder_days_before_expiry as number} onChange={(e) => setField('reminder_days_before_expiry', safeInt(e.target.value, 1))} className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream" />
                </div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-4 border-t border-lsc-border dark:border-earth-700">
                <div className="flex items-center">{renderToggle(config.send_welcome_message as boolean, () => toggleField('send_welcome_message'), 'Send welcome message')}<span className="ml-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Send welcome message</span></div>
                <div className="flex items-center">{renderToggle(config.send_expiry_reminders as boolean, () => toggleField('send_expiry_reminders'), 'Send expiry reminders')}<span className="ml-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Send expiry reminders</span></div>
                <div className="flex items-center">{renderToggle(config.allow_marketing_communications as boolean, () => toggleField('allow_marketing_communications'), 'Allow marketing')}<span className="ml-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Allow marketing communications</span></div>
              </div>
            </div>
          )}

          <button onClick={() => save()} disabled={saving}
            className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 disabled:opacity-50 font-semibold">
            {saving ? 'Saving...' : 'Save Settings'}
          </button>
        </div>
      )}
    </SectionShell>
  )
}

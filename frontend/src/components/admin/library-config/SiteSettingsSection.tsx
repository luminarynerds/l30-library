/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useState, useEffect } from 'react'
import api from '@/api/api'
import toast from 'react-hot-toast'
import { Settings, Save, BookOpen, DollarSign, Clock, Users, Bell, Layers, Loader2, BarChart3 } from 'lucide-react'
import { API_BASE } from '@/api/types'
import { useTranslation } from '@/i18n'
import { SectionShell } from '../ai-settings/SectionShell'

interface SystemSettings {
  id: number
  library_system_id: number
  default_loan_period_days: number
  default_renewal_limit: number
  default_hold_limit: number
  default_checkout_limit: number
  default_overdue_fine_per_day: number
  default_max_fine: number
  grace_period_days: number
  fine_free_juvenile: boolean
  lost_item_threshold_days: number
  default_replacement_cost: number
  processing_fee: number
  hold_pickup_days: number
  allow_hold_on_available: boolean
  transit_time_estimate_days: number
  auto_approve_transit: boolean
  require_address_verification: boolean
  allow_self_registration: boolean
  card_expiry_years: number
  age_transition_threshold: number
  auto_transition_enabled: boolean
  forgive_reading_minutes_on_transition: boolean
  overdue_notice_days: number[] | null
  courtesy_notice_days: number
  enable_floating_collections: boolean
  enable_reciprocal_borrowing: boolean
  enable_self_checkout: boolean
  fte_annual_hours: number | null
  volunteer_hour_value: string | null
  updated_at: string | null
}

interface LibrarySystem {
  id: number
  code: string
  name: string
}

const TABS = [
  { id: 'settings', label: 'Settings', icon: Settings },
] as const

interface SiteSettingsSectionProps {
  onBack: () => void
}

export function SiteSettingsSection({ onBack }: SiteSettingsSectionProps) {
  const { t } = useTranslation()
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [systems, setSystems] = useState<LibrarySystem[]>([])
  const [selectedSystemId, setSelectedSystemId] = useState<number | null>(null)
  const [settings, setSettings] = useState<SystemSettings | null>(null)
  const [overdueNoticeDaysInput, setOverdueNoticeDaysInput] = useState('')

  const loadSystems = async () => {
    try {
      const data = await api.get<LibrarySystem[]>(`${API_BASE}/branches/systems`)
      setSystems(data)
      if (data.length > 0) setSelectedSystemId(data[0]!.id)
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      toast.error(t('admin.adminSiteSettings.failedToLoadLibrarySystems'))
    }
  }


  useEffect(() => { void loadSystems() }, [])

  const loadSettings = async (systemId: number) => {
    try {
      setLoading(true)
      const data = await api.get<SystemSettings>(`${API_BASE}/branches/systems/${systemId}/settings`)
      setSettings(data)
      setOverdueNoticeDaysInput(data.overdue_notice_days?.join(', ') || '1, 7, 14, 21')
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      toast.error(t('admin.adminSiteSettings.failedToLoadSystemSettings'))
    } finally {
      setLoading(false)
    }
  }


  useEffect(() => {
    if (selectedSystemId) void loadSettings(selectedSystemId)
  }, [selectedSystemId])

  const handleNumberChange = (field: keyof SystemSettings, value: string) => {
    if (!settings) return
    const numValue = parseFloat(value)
    if (!isNaN(numValue)) setSettings({ ...settings, [field]: numValue })
  }

  const handleDecimalChange = (field: keyof SystemSettings, value: string) => {
    if (!settings) return
    const numValue = parseFloat(value)
    if (!isNaN(numValue)) setSettings({ ...settings, [field]: numValue })
  }

  const handleBooleanChange = (field: keyof SystemSettings) => {
    if (!settings) return
    setSettings({ ...settings, [field]: !settings[field] })
  }

  const handleSave = async () => {
    if (!settings || !selectedSystemId) return
    try {
      setSaving(true)
      const overdueNoticeDays = overdueNoticeDaysInput.split(',').map(s => parseInt(s.trim())).filter(n => !isNaN(n))
      const payload = { ...settings, overdue_notice_days: overdueNoticeDays.length > 0 ? overdueNoticeDays : null }
      await api.patch(`${API_BASE}/branches/systems/${selectedSystemId}/settings`, payload)
      toast.success(t('admin.adminSiteSettings.siteSettingsUpdatedSuccessfully'))
      await loadSettings(selectedSystemId)
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } }
      toast.error(err.response?.data?.detail || t('toast.adminSiteSettings.failedToUpdateSettings'))
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
    } finally {
      setSaving(false)
    }
  }

  const renderToggle = (value: boolean, onToggle: () => void, label?: string) => (
    <button type="button" role="switch" aria-checked={value} aria-label={label} onClick={onToggle}
      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${value ? 'bg-lsc-rose' : 'bg-earth-200 dark:bg-earth-700'}`}>
      <span className={`inline-block h-4 w-4 transform rounded-full bg-lsc-white dark:bg-earth-800 transition-transform ${value ? 'translate-x-6' : 'translate-x-1'}`} />
    </button>
  )

  if (loading || !settings) {
    return (
      <SectionShell title="Site Settings" description="General library configuration." tabs={[...TABS]} defaultTab="settings" backLabel="Back to Library Configuration" onBack={onBack}>
        {() => <div className="flex justify-center py-12"><Loader2 className="h-8 w-8 motion-safe:animate-spin text-lsc-rose" /></div>}
      </SectionShell>
    )
  }

  return (
    <SectionShell
      title="Site Settings"
      description="General library configuration -- circulation defaults, fine defaults, hold policies, transit rules, notification timing, and feature flags."
      tabs={[...TABS]}
      defaultTab="settings"
      backLabel="Back to Library Configuration"
      onBack={onBack}
    >
      {() => (
        <div className="space-y-6">
          {systems.length > 1 && (
            <div className="flex items-center gap-3">
              <label className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Library System:</label>
              <select value={selectedSystemId || ''} onChange={(e) => setSelectedSystemId(parseInt(e.target.value))}
                className="px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream">
                {systems.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
              </select>
            </div>
          )}

          <div className="bg-status-warning-50 dark:bg-status-warning-900/20 border border-status-warning-200 dark:border-status-warning-800 rounded-lg p-4">
            <p className="text-sm text-status-warning-800 dark:text-status-warning-200">These settings control circulation policies, fines, holds, and other system-wide defaults.</p>
          </div>

          {/* Circulation Policies */}
          <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 p-6 space-y-4">
            <div className="flex items-center gap-2 mb-4"><BookOpen className="w-5 h-5 text-status-warning-600" /><h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">Circulation Policies</h3></div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <div><label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Default Loan Period (days)</label><input type="number" min="1" max="365" value={settings.default_loan_period_days} onChange={(e) => handleNumberChange('default_loan_period_days', e.target.value)} className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream" /></div>
              <div><label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Default Renewal Limit</label><input type="number" min="0" max="20" value={settings.default_renewal_limit} onChange={(e) => handleNumberChange('default_renewal_limit', e.target.value)} className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream" /></div>
              <div><label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Default Hold Limit</label><input type="number" min="0" max="50" value={settings.default_hold_limit} onChange={(e) => handleNumberChange('default_hold_limit', e.target.value)} className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream" /></div>
              <div><label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Default Checkout Limit</label><input type="number" min="1" max="200" value={settings.default_checkout_limit} onChange={(e) => handleNumberChange('default_checkout_limit', e.target.value)} className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream" /></div>
            </div>
          </div>

          {/* Fine Policies */}
          <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 p-6 space-y-4">
            <div className="flex items-center gap-2 mb-4"><DollarSign className="w-5 h-5 text-status-warning-600" /><h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">Fine Policies</h3></div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <div><label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Overdue Fine Per Day ($)</label><input type="number" min="0" max="10" step="0.01" value={settings.default_overdue_fine_per_day} onChange={(e) => handleDecimalChange('default_overdue_fine_per_day', e.target.value)} className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream" /></div>
              <div><label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Maximum Fine ($)</label><input type="number" min="0" max="1000" step="0.01" value={settings.default_max_fine} onChange={(e) => handleDecimalChange('default_max_fine', e.target.value)} className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream" /></div>
              <div><label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Grace Period (days)</label><input type="number" min="0" max="30" value={settings.grace_period_days} onChange={(e) => handleNumberChange('grace_period_days', e.target.value)} className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream" /></div>
              <div className="flex items-center pt-6">{renderToggle(settings.fine_free_juvenile, () => handleBooleanChange('fine_free_juvenile'), 'Fine-free for juveniles')}<span className="ml-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Fine-free for juveniles</span></div>
            </div>
          </div>

          {/* Lost Item Policies */}
          <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 p-6 space-y-4">
            <div className="flex items-center gap-2 mb-4"><Clock className="w-5 h-5 text-status-warning-600" /><h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">Lost Item Policies</h3></div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div><label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Lost Item Threshold (days)</label><input type="number" min="1" max="365" value={settings.lost_item_threshold_days} onChange={(e) => handleNumberChange('lost_item_threshold_days', e.target.value)} className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream" /></div>
              <div><label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Default Replacement Cost ($)</label><input type="number" min="0" max="1000" step="0.01" value={settings.default_replacement_cost} onChange={(e) => handleDecimalChange('default_replacement_cost', e.target.value)} className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream" /></div>
              <div><label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Processing Fee ($)</label><input type="number" min="0" max="100" step="0.01" value={settings.processing_fee} onChange={(e) => handleDecimalChange('processing_fee', e.target.value)} className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream" /></div>
            </div>
          </div>

          {/* Hold & Transit Policies */}
          <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 p-6 space-y-4">
            <div className="flex items-center gap-2 mb-4"><Layers className="w-5 h-5 text-status-warning-600" /><h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">Hold & Transit Policies</h3></div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <div><label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Hold Pickup Days</label><input type="number" min="1" max="30" value={settings.hold_pickup_days} onChange={(e) => handleNumberChange('hold_pickup_days', e.target.value)} className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream" /></div>
              <div className="flex items-center pt-6">{renderToggle(settings.allow_hold_on_available, () => handleBooleanChange('allow_hold_on_available'), 'Allow hold on available items')}<span className="ml-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Allow hold on available</span></div>
              <div><label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Transit Time Estimate (days)</label><input type="number" min="1" max="14" value={settings.transit_time_estimate_days} onChange={(e) => handleNumberChange('transit_time_estimate_days', e.target.value)} className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream" /></div>
              <div className="flex items-center pt-6">{renderToggle(settings.auto_approve_transit, () => handleBooleanChange('auto_approve_transit'), 'Auto-approve transit')}<span className="ml-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Auto-approve transit</span></div>
            </div>
          </div>

          {/* Patron Policies */}
          <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 p-6 space-y-4">
            <div className="flex items-center gap-2 mb-4"><Users className="w-5 h-5 text-status-warning-600" /><h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">Patron Policies</h3></div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="flex items-center">{renderToggle(settings.require_address_verification, () => handleBooleanChange('require_address_verification'), 'Require address verification')}<span className="ml-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Require address verification</span></div>
              <div className="flex items-center">{renderToggle(settings.allow_self_registration, () => handleBooleanChange('allow_self_registration'), 'Allow self-registration')}<span className="ml-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Allow self-registration</span></div>
              <div><label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Card Expiry (years)</label><input type="number" min="1" max="10" value={settings.card_expiry_years} onChange={(e) => handleNumberChange('card_expiry_years', e.target.value)} className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream" /></div>
              <div><label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Age Transition Threshold</label><input type="number" min="13" max="25" value={settings.age_transition_threshold} onChange={(e) => handleNumberChange('age_transition_threshold', e.target.value)} className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream" /></div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-4 border-t border-lsc-border dark:border-earth-700">
              <div className="flex items-center">{renderToggle(settings.auto_transition_enabled, () => handleBooleanChange('auto_transition_enabled'), 'Auto-transition juvenile accounts')}<span className="ml-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Auto-transition juvenile accounts</span></div>
              <div className="flex items-center">{renderToggle(settings.forgive_reading_minutes_on_transition, () => handleBooleanChange('forgive_reading_minutes_on_transition'), 'Forgive reading minutes on transition')}<span className="ml-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Forgive reading minutes on transition</span></div>
            </div>
          </div>

          {/* Notifications */}
          <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 p-6 space-y-4">
            <div className="flex items-center gap-2 mb-4"><Bell className="w-5 h-5 text-status-warning-600" /><h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">Notifications</h3></div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div><label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Overdue Notice Days (comma-separated)</label><input type="text" value={overdueNoticeDaysInput} onChange={(e) => setOverdueNoticeDaysInput(e.target.value)} placeholder="1, 7, 14, 21" className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream" /></div>
              <div><label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Courtesy Notice Days Before Due</label><input type="number" min="0" max="14" value={settings.courtesy_notice_days} onChange={(e) => handleNumberChange('courtesy_notice_days', e.target.value)} className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream" /></div>
            </div>
          </div>

          {/* Reporting basis (state annual report + board monthly report) */}
          <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 p-6 space-y-4">
            <div className="flex items-center gap-2 mb-4"><BarChart3 className="w-5 h-5 text-status-warning-600" /><h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">Reporting basis</h3></div>
            <p className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60 -mt-2">FTE divisor for the state annual report and dollar value per volunteer hour on the board monthly report.</p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div><label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">FTE annual hours</label><input type="number" min="1" max="8760" value={settings.fte_annual_hours ?? 2080} onChange={(e) => handleNumberChange('fte_annual_hours', e.target.value)} className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream" /></div>
              <div><label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Volunteer hour value ($)</label><input type="number" min="0" max="1000" step="0.01" value={settings.volunteer_hour_value ?? '33.49'} onChange={(e) => handleDecimalChange('volunteer_hour_value', e.target.value)} className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream" /></div>
            </div>
          </div>

          {/* Feature Flags */}
          <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 p-6 space-y-4">
            <div className="flex items-center gap-2 mb-4"><Settings className="w-5 h-5 text-status-warning-600" /><h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">Feature Flags</h3></div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="flex items-center">{renderToggle(settings.enable_floating_collections, () => handleBooleanChange('enable_floating_collections'), 'Floating collections')}<span className="ml-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Floating collections</span></div>
              <div className="flex items-center">{renderToggle(settings.enable_reciprocal_borrowing, () => handleBooleanChange('enable_reciprocal_borrowing'), 'Reciprocal borrowing')}<span className="ml-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Reciprocal borrowing</span></div>
              <div className="flex items-center">{renderToggle(settings.enable_self_checkout, () => handleBooleanChange('enable_self_checkout'), 'Self-checkout')}<span className="ml-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Self-checkout</span></div>
            </div>
          </div>

          <button onClick={handleSave} disabled={saving}
            className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 disabled:opacity-50 font-semibold">
            <Save className="h-4 w-4" /> {saving ? 'Saving...' : 'Save Settings'}
          </button>
        </div>
      )}
    </SectionShell>
  )
}

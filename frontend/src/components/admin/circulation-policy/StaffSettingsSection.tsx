/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect } from 'react'
import toast from 'react-hot-toast'
import { Save, Users, Building2, Lock, Calendar, GraduationCap, Loader2 } from 'lucide-react'
import api from '@/lib/api-client'
import { API_BASE } from '@/api/types'
import { SectionShell } from '../ai-settings/SectionShell'

const safeInt = (val: string, fallback: number) => { const n = parseInt(val); return isNaN(n) ? fallback : n }

interface RolePermissions {
  can_checkout: boolean; can_checkin: boolean; can_renew: boolean; can_waive_fines: boolean
  can_create_records: boolean; can_edit_records: boolean; can_delete_records: boolean; can_import: boolean
  can_view_patrons: boolean; can_edit_patrons: boolean; can_create_patrons: boolean; can_merge_patrons: boolean
  can_manage_staff: boolean; can_manage_settings: boolean; can_view_reports: boolean; can_manage_features: boolean
}

interface Role {
  name: string; description: string; memberCount: number; active: boolean; permissions: RolePermissions
}

interface Department {
  name: string; color: string; headCount: number; active: boolean
}

interface StaffPolicies {
  require_2fa: boolean; session_timeout: number; max_concurrent_sessions: number
  password_expiry_days: number; allow_remote_access: boolean; require_vpn: boolean; ip_whitelist_enabled: boolean
}

interface SchedulingSettings {
  default_shift_duration: number; allow_shift_swaps: boolean; require_manager_approval: boolean
  overtime_tracking: boolean; break_duration: number; max_hours_per_week: number
}

interface TrainingSettings {
  require_onboarding: boolean; training_deadline_days: number; annual_ce_hours: number
  track_certifications: boolean; allow_self_paced: boolean
}

const defaultPermissions = (overrides: Partial<RolePermissions> = {}): RolePermissions => ({
  can_checkout: false, can_checkin: false, can_renew: false, can_waive_fines: false,
  can_create_records: false, can_edit_records: false, can_delete_records: false, can_import: false,
  can_view_patrons: false, can_edit_patrons: false, can_create_patrons: false, can_merge_patrons: false,
  can_manage_staff: false, can_manage_settings: false, can_view_reports: false, can_manage_features: false,
  ...overrides,
})

const DEFAULT_ROLES: Role[] = [
  { name: 'Circulation Clerk', description: 'Front desk circulation duties', memberCount: 3, active: true, permissions: defaultPermissions({ can_checkout: true, can_checkin: true, can_renew: true, can_view_patrons: true }) },
  { name: 'Cataloger', description: 'Catalog and metadata management', memberCount: 1, active: true, permissions: defaultPermissions({ can_create_records: true, can_edit_records: true, can_import: true }) },
  { name: 'Reference Librarian', description: 'Reference services and patron assistance', memberCount: 2, active: true, permissions: defaultPermissions({ can_checkout: true, can_checkin: true, can_renew: true, can_view_patrons: true, can_edit_patrons: true, can_view_reports: true }) },
  { name: 'Branch Manager', description: 'Full branch management', memberCount: 1, active: true, permissions: defaultPermissions({ can_checkout: true, can_checkin: true, can_renew: true, can_waive_fines: true, can_create_records: true, can_edit_records: true, can_view_patrons: true, can_edit_patrons: true, can_create_patrons: true, can_manage_staff: true, can_view_reports: true }) },
  { name: 'Director', description: 'System-wide administration', memberCount: 1, active: true, permissions: defaultPermissions(Object.fromEntries(Object.keys(defaultPermissions()).map((k) => [k, true])) as unknown as RolePermissions) },
]

const DEFAULT_DEPARTMENTS: Department[] = [
  { name: 'Circulation', color: '#f59e0b', headCount: 4, active: true },
  { name: 'Technical Services', color: '#3b82f6', headCount: 2, active: true },
  { name: 'Reference', color: '#10b981', headCount: 2, active: true },
  { name: 'Youth Services', color: '#8b5cf6', headCount: 1, active: true },
  { name: 'Administration', color: '#ef4444', headCount: 1, active: true },
]

const DEFAULT_POLICIES: StaffPolicies = {
  require_2fa: false, session_timeout: 480, max_concurrent_sessions: 3,
  password_expiry_days: 90, allow_remote_access: true, require_vpn: false, ip_whitelist_enabled: false,
}

const DEFAULT_SCHEDULING: SchedulingSettings = {
  default_shift_duration: 8, allow_shift_swaps: true, require_manager_approval: true,
  overtime_tracking: true, break_duration: 30, max_hours_per_week: 40,
}

const DEFAULT_TRAINING: TrainingSettings = {
  require_onboarding: true, training_deadline_days: 30, annual_ce_hours: 20,
  track_certifications: true, allow_self_paced: true,
}

const TABS = [
  { id: 'roles', label: 'Roles & Permissions', icon: Users },
  { id: 'departments', label: 'Departments', icon: Building2 },
  { id: 'policies', label: 'Staff Policies', icon: Lock },
  { id: 'scheduling', label: 'Scheduling', icon: Calendar },
  { id: 'training', label: 'Training', icon: GraduationCap },
] as const

interface StaffSettingsSectionProps {
  onBack: () => void
}

export function StaffSettingsSection({ onBack }: StaffSettingsSectionProps) {
  const [roles, setRoles] = useState<Role[]>(DEFAULT_ROLES)
  const [departments, setDepartments] = useState<Department[]>(DEFAULT_DEPARTMENTS)
  const [policies, setPolicies] = useState<StaffPolicies>(DEFAULT_POLICIES)
  const [scheduling, setScheduling] = useState<SchedulingSettings>(DEFAULT_SCHEDULING)
  const [training, setTraining] = useState<TrainingSettings>(DEFAULT_TRAINING)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    const load = async () => {
      try {
        const data = await api.get(`${API_BASE}/admin/staff-settings`)
        if (data) {
          const d = data as Record<string, unknown>
          if (Array.isArray(d.roles)) setRoles(d.roles as Role[])
          if (Array.isArray(d.departments)) setDepartments(d.departments as Department[])
          if (d.policies) setPolicies(d.policies as StaffPolicies)
          if (d.scheduling) setScheduling(d.scheduling as SchedulingSettings)
          if (d.training) setTraining(d.training as TrainingSettings)
        }
      } catch { /* use defaults */ }
      setLoading(false)
    }
    void load()
  }, [])

  const handleSave = async () => {
    try {
      setSaving(true)
      await api.patch(`${API_BASE}/admin/staff-settings`, { roles, departments, policies, scheduling, training })
      toast.success('Staff settings saved')
    } catch {
      toast.error('Failed to save staff settings')
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

  if (loading) return <div className="flex justify-center py-12"><Loader2 className="h-8 w-8 motion-safe:animate-spin text-lsc-rose" /></div>

  return (
    <SectionShell
      title="Staff Roles & Policies"
      description="Staff roles, permissions, departments, security policies, scheduling, and training requirements."
      tabs={[...TABS]}
      defaultTab="roles"
      backLabel="Back to Circulation & Policy"
      onBack={onBack}
    >
      {(activeTab) => (
        <div className="space-y-6">
          {activeTab === 'roles' && (
            <div className="space-y-4">
              {roles.map((role, idx) => (
                <div key={role.name} className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl p-4">
                  <div className="flex items-center justify-between mb-2">
                    <div>
                      <h4 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">{role.name}</h4>
                      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{role.description}</p>
                    </div>
                    <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60">{role.memberCount} member{role.memberCount !== 1 ? 's' : ''}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    {renderToggle(role.active, () => {
                      const updated = [...roles]; updated[idx] = { ...role, active: !role.active }; setRoles(updated)
                    }, `Toggle ${role.name}`)}
                    <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{role.active ? 'Active' : 'Inactive'}</span>
                  </div>
                </div>
              ))}
            </div>
          )}

          {activeTab === 'departments' && (
            <div className="space-y-4">
              {departments.map((dept, idx) => (
                <div key={dept.name} className="flex items-center gap-4 bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl p-4">
                  <div className="w-4 h-4 rounded-full flex-shrink-0" style={{ backgroundColor: dept.color }} />
                  <div className="flex-1">
                    <h4 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">{dept.name}</h4>
                    <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60">{dept.headCount} staff</span>
                  </div>
                  {renderToggle(dept.active, () => {
                    const updated = [...departments]; updated[idx] = { ...dept, active: !dept.active }; setDepartments(updated)
                  }, `Toggle ${dept.name}`)}
                </div>
              ))}
            </div>
          )}

          {activeTab === 'policies' && (
            <div className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl p-6 space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="flex items-center">{renderToggle(policies.require_2fa, () => setPolicies({ ...policies, require_2fa: !policies.require_2fa }), 'Require 2FA')}<span className="ml-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Require two-factor authentication</span></div>
                <div className="flex items-center">{renderToggle(policies.allow_remote_access, () => setPolicies({ ...policies, allow_remote_access: !policies.allow_remote_access }), 'Allow remote access')}<span className="ml-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Allow remote access</span></div>
                <div className="flex items-center">{renderToggle(policies.require_vpn, () => setPolicies({ ...policies, require_vpn: !policies.require_vpn }), 'Require VPN')}<span className="ml-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Require VPN for remote access</span></div>
                <div className="flex items-center">{renderToggle(policies.ip_whitelist_enabled, () => setPolicies({ ...policies, ip_whitelist_enabled: !policies.ip_whitelist_enabled }), 'IP whitelist')}<span className="ml-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Enable IP whitelist</span></div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-4 border-t border-lsc-border dark:border-earth-700">
                <div>
                  <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Session timeout (minutes)</label>
                  <input type="number" min="15" max="1440" value={policies.session_timeout} onChange={(e) => setPolicies({ ...policies, session_timeout: safeInt(e.target.value, 480) })} className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Max concurrent sessions</label>
                  <input type="number" min="1" max="10" value={policies.max_concurrent_sessions} onChange={(e) => setPolicies({ ...policies, max_concurrent_sessions: safeInt(e.target.value, 3) })} className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Password expiry (days)</label>
                  <input type="number" min="30" max="365" value={policies.password_expiry_days} onChange={(e) => setPolicies({ ...policies, password_expiry_days: safeInt(e.target.value, 90) })} className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream" />
                </div>
              </div>
            </div>
          )}

          {activeTab === 'scheduling' && (
            <div className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl p-6 space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="flex items-center">{renderToggle(scheduling.allow_shift_swaps, () => setScheduling({ ...scheduling, allow_shift_swaps: !scheduling.allow_shift_swaps }), 'Allow shift swaps')}<span className="ml-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Allow shift swaps</span></div>
                <div className="flex items-center">{renderToggle(scheduling.require_manager_approval, () => setScheduling({ ...scheduling, require_manager_approval: !scheduling.require_manager_approval }), 'Require manager approval')}<span className="ml-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Require manager approval for swaps</span></div>
                <div className="flex items-center">{renderToggle(scheduling.overtime_tracking, () => setScheduling({ ...scheduling, overtime_tracking: !scheduling.overtime_tracking }), 'Overtime tracking')}<span className="ml-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Track overtime</span></div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-4 border-t border-lsc-border dark:border-earth-700">
                <div>
                  <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Default shift duration (hours)</label>
                  <input type="number" min="4" max="12" value={scheduling.default_shift_duration} onChange={(e) => setScheduling({ ...scheduling, default_shift_duration: safeInt(e.target.value, 8) })} className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Break duration (minutes)</label>
                  <input type="number" min="0" max="60" value={scheduling.break_duration} onChange={(e) => setScheduling({ ...scheduling, break_duration: safeInt(e.target.value, 30) })} className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Max hours per week</label>
                  <input type="number" min="20" max="60" value={scheduling.max_hours_per_week} onChange={(e) => setScheduling({ ...scheduling, max_hours_per_week: safeInt(e.target.value, 40) })} className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream" />
                </div>
              </div>
            </div>
          )}

          {activeTab === 'training' && (
            <div className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl p-6 space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="flex items-center">{renderToggle(training.require_onboarding, () => setTraining({ ...training, require_onboarding: !training.require_onboarding }), 'Require onboarding')}<span className="ml-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Require onboarding training</span></div>
                <div className="flex items-center">{renderToggle(training.track_certifications, () => setTraining({ ...training, track_certifications: !training.track_certifications }), 'Track certifications')}<span className="ml-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Track certifications</span></div>
                <div className="flex items-center">{renderToggle(training.allow_self_paced, () => setTraining({ ...training, allow_self_paced: !training.allow_self_paced }), 'Allow self-paced')}<span className="ml-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Allow self-paced training</span></div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-4 border-t border-lsc-border dark:border-earth-700">
                <div>
                  <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Training deadline (days)</label>
                  <input type="number" min="7" max="180" value={training.training_deadline_days} onChange={(e) => setTraining({ ...training, training_deadline_days: safeInt(e.target.value, 30) })} className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Annual CE hours required</label>
                  <input type="number" min="0" max="100" value={training.annual_ce_hours} onChange={(e) => setTraining({ ...training, annual_ce_hours: safeInt(e.target.value, 20) })} className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream" />
                </div>
              </div>
            </div>
          )}

          <button onClick={handleSave} disabled={saving}
            className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 disabled:opacity-50 font-semibold">
            <Save className="h-4 w-4" /> {saving ? 'Saving...' : 'Save Staff Settings'}
          </button>
        </div>
      )}
    </SectionShell>
  )
}

/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { User, Search, Edit2, Save, X, Plus, Loader2, Briefcase } from 'lucide-react'
import toast from 'react-hot-toast'
import { fairSchedulingApi } from '../api/fair-scheduling-api'
import { AdminShell } from '../components/shells/AdminShell'

interface SchedulingProfile {
  id: number
  staff_id: number
  branch_id: number | null
  employment_type: 'full_time' | 'part_time' | 'temporary' | 'seasonal'
  contracted_hours_per_week: number
  min_hours_per_week: number
  max_hours_per_week: number
  skills: string[]
  hire_date: string | null
  seniority_level: number
  max_consecutive_days: number
  min_hours_between_shifts: number
  max_weekend_shifts_per_month: number
  max_closing_shifts_per_week: number
  desirable_shift_score: number
  is_active: boolean
  created_at?: string | null
}

type EmploymentType = SchedulingProfile['employment_type']

const EMPLOYMENT_TYPES: { value: EmploymentType; label: string }[] = [
  { value: 'full_time', label: 'Full Time' },
  { value: 'part_time', label: 'Part Time' },
  { value: 'temporary', label: 'Temporary' },
  { value: 'seasonal', label: 'Seasonal' },
]

const EMPLOYMENT_BADGE_COLORS: Record<EmploymentType, string> = {
  full_time: 'bg-lsc-green text-white',
  part_time: 'bg-status-info-500 text-white',
  temporary: 'bg-status-warning-500 text-white',
  seasonal: 'bg-category-500 text-white',
}

const INPUT_CLASS =
  'rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown px-3 py-2 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent w-full'

const BLANK_FORM: Omit<SchedulingProfile, 'id' | 'desirable_shift_score' | 'created_at'> = {
  staff_id: 0,
  branch_id: null,
  employment_type: 'full_time',
  contracted_hours_per_week: 40,
  min_hours_per_week: 0,
  max_hours_per_week: 40,
  skills: [],
  hire_date: null,
  seniority_level: 1,
  max_consecutive_days: 5,
  min_hours_between_shifts: 10,
  max_weekend_shifts_per_month: 4,
  max_closing_shifts_per_week: 2,
  is_active: true,
}

export default function FairSchedulingProfilesPage(): React.ReactElement {
  const [staffIdInput, setStaffIdInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [profile, setProfile] = useState<SchedulingProfile | null>(null)
  const [notFound, setNotFound] = useState(false)
  const [editing, setEditing] = useState(false)
  const [creating, setCreating] = useState(false)
  const [saving, setSaving] = useState(false)
  const [formData, setFormData] = useState<typeof BLANK_FORM>({ ...BLANK_FORM })
  const [skillInput, setSkillInput] = useState('')

  const loadProfile = async () => {
    const id = parseInt(staffIdInput, 10)
    if (isNaN(id) || id <= 0) {
      toast.error('Enter a valid staff ID')
      return
    }
    setLoading(true)
    setProfile(null)
    setNotFound(false)
    setEditing(false)
    setCreating(false)
    try {
      const res = await fairSchedulingApi.getProfile(id)
      setProfile(res as SchedulingProfile)
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } })?.response?.status
      if (status === 404) {
        setNotFound(true)
      } else {
        toast.error('Failed to load profile')
      }
    } finally {
      setLoading(false)
    }
  }

  const startEdit = () => {
    if (!profile) return
    setFormData({
      staff_id: profile.staff_id,
      branch_id: profile.branch_id,
      employment_type: profile.employment_type,
      contracted_hours_per_week: profile.contracted_hours_per_week,
      min_hours_per_week: profile.min_hours_per_week,
      max_hours_per_week: profile.max_hours_per_week,
      skills: [...profile.skills],
      hire_date: profile.hire_date,
      seniority_level: profile.seniority_level,
      max_consecutive_days: profile.max_consecutive_days,
      min_hours_between_shifts: profile.min_hours_between_shifts,
      max_weekend_shifts_per_month: profile.max_weekend_shifts_per_month,
      max_closing_shifts_per_week: profile.max_closing_shifts_per_week,
      is_active: profile.is_active,
    })
    setSkillInput('')
    setEditing(true)
  }

  const cancelEdit = () => {
    setEditing(false)
    setCreating(false)
  }

  const startCreate = () => {
    const id = parseInt(staffIdInput, 10)
    setFormData({ ...BLANK_FORM, staff_id: id })
    setSkillInput('')
    setCreating(true)
    setNotFound(false)
  }

  const addSkills = () => {
    if (!skillInput.trim()) return
    const newSkills = skillInput
      .split(',')
      .map((s) => s.trim())
      .filter((s) => s.length > 0 && !formData.skills.includes(s))
    setFormData((prev) => ({ ...prev, skills: [...prev.skills, ...newSkills] }))
    setSkillInput('')
  }

  const removeSkill = (skill: string) => {
    setFormData((prev) => ({ ...prev, skills: prev.skills.filter((s) => s !== skill) }))
  }

  const updateField = <K extends keyof typeof BLANK_FORM>(key: K, value: (typeof BLANK_FORM)[K]) => {
    setFormData((prev) => ({ ...prev, [key]: value }))
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      if (creating) {
        const res = await fairSchedulingApi.createProfile(
          formData as Parameters<typeof fairSchedulingApi.createProfile>[0]
        )
        setProfile(res as SchedulingProfile)
        setCreating(false)
        toast.success('Profile created')
      } else {
        const { staff_id, ...updates } = formData
        const res = await fairSchedulingApi.updateProfile(staff_id, updates)
        setProfile(res as SchedulingProfile)
        setEditing(false)
        toast.success('Profile updated')
      }
    } catch {
      toast.error(creating ? 'Failed to create profile' : 'Failed to update profile')
    } finally {
      setSaving(false)
    }
  }

  const renderBadge = (type: EmploymentType) => (
    <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${EMPLOYMENT_BADGE_COLORS[type]}`}>
      {EMPLOYMENT_TYPES.find((t) => t.value === type)?.label}
    </span>
  )

  const renderSkillBadges = (skills: string[]) =>
    skills.map((skill) => (
      <span
        key={skill}
        className="rounded-full px-2.5 py-1 text-xs font-medium bg-lsc-rose/10 text-lsc-rose"
      >
        {skill}
      </span>
    ))

  const renderFormFields = () => (
    <div className="space-y-6">
      {/* Employment Type */}
      <div>
        <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
          Employment Type
        </label>
        <select
          className={INPUT_CLASS}
          value={formData.employment_type}
          onChange={(e) => updateField('employment_type', e.target.value as EmploymentType)}
        >
          {EMPLOYMENT_TYPES.map((t) => (
            <option key={t.value} value={t.value}>
              {t.label}
            </option>
          ))}
        </select>
      </div>

      {/* Hours */}
      <div>
        <h4 className="text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-3">Hours per Week</h4>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div>
            <label className="block text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
              Contracted
            </label>
            <input
              type="number"
              className={INPUT_CLASS}
              value={formData.contracted_hours_per_week}
              onChange={(e) =>
                updateField('contracted_hours_per_week', parseFloat(e.target.value) || 0)
              }
              min={0}
            />
          </div>
          <div>
            <label className="block text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
              Minimum
            </label>
            <input
              type="number"
              className={INPUT_CLASS}
              value={formData.min_hours_per_week}
              onChange={(e) => updateField('min_hours_per_week', parseFloat(e.target.value) || 0)}
              min={0}
            />
          </div>
          <div>
            <label className="block text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
              Maximum
            </label>
            <input
              type="number"
              className={INPUT_CLASS}
              value={formData.max_hours_per_week}
              onChange={(e) => updateField('max_hours_per_week', parseFloat(e.target.value) || 0)}
              min={0}
            />
          </div>
        </div>
      </div>

      {/* Constraints */}
      <div>
        <h4 className="text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-3">
          Scheduling Constraints
        </h4>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
              Max Consecutive Days
            </label>
            <input
              type="number"
              className={INPUT_CLASS}
              value={formData.max_consecutive_days}
              onChange={(e) =>
                updateField('max_consecutive_days', parseInt(e.target.value, 10) || 0)
              }
              min={1}
            />
          </div>
          <div>
            <label className="block text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
              Min Hours Between Shifts
            </label>
            <input
              type="number"
              className={INPUT_CLASS}
              value={formData.min_hours_between_shifts}
              onChange={(e) =>
                updateField('min_hours_between_shifts', parseFloat(e.target.value) || 0)
              }
              min={0}
            />
          </div>
          <div>
            <label className="block text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
              Max Weekend Shifts / Month
            </label>
            <input
              type="number"
              className={INPUT_CLASS}
              value={formData.max_weekend_shifts_per_month}
              onChange={(e) =>
                updateField('max_weekend_shifts_per_month', parseInt(e.target.value, 10) || 0)
              }
              min={0}
            />
          </div>
          <div>
            <label className="block text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
              Max Closing Shifts / Week
            </label>
            <input
              type="number"
              className={INPUT_CLASS}
              value={formData.max_closing_shifts_per_week}
              onChange={(e) =>
                updateField('max_closing_shifts_per_week', parseInt(e.target.value, 10) || 0)
              }
              min={0}
            />
          </div>
        </div>
      </div>

      {/* Skills */}
      <div>
        <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
          Skills
        </label>
        <div className="flex flex-wrap gap-2 mb-2">
          {formData.skills.map((skill) => (
            <span
              key={skill}
              className="rounded-full px-2.5 py-1 text-xs font-medium bg-lsc-rose/10 text-lsc-rose inline-flex items-center gap-1"
            >
              {skill}
              <button
                type="button"
                onClick={() => removeSkill(skill)}
                className="hover:text-status-danger-500"
              >
                <X className="h-3 w-3" />
              </button>
            </span>
          ))}
        </div>
        <div className="flex gap-2">
          <input
            type="text"
            className={INPUT_CLASS}
            placeholder="Add skills (comma-separated)"
            value={skillInput}
            onChange={(e) => setSkillInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                e.preventDefault()
                addSkills()
              }
            }}
          />
          <button
            type="button"
            onClick={addSkills}
            className="bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg px-4 py-2 flex items-center gap-1 shrink-0"
          >
            <Plus className="h-4 w-4" /> Add
          </button>
        </div>
      </div>

      {/* Seniority & Hire Date */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
            Seniority Level
          </label>
          <input
            type="number"
            className={INPUT_CLASS}
            value={formData.seniority_level}
            onChange={(e) => updateField('seniority_level', parseInt(e.target.value, 10) || 1)}
            min={1}
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
            Hire Date
          </label>
          <input
            type="date"
            className={INPUT_CLASS}
            value={formData.hire_date || ''}
            onChange={(e) => updateField('hire_date', e.target.value || null)}
          />
        </div>
      </div>

      {/* Branch ID */}
      <div>
        <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
          Branch ID
        </label>
        <input
          type="number"
          className={INPUT_CLASS}
          value={formData.branch_id ?? ''}
          onChange={(e) =>
            updateField('branch_id', e.target.value ? parseInt(e.target.value, 10) : null)
          }
          min={1}
        />
      </div>

      {/* Active */}
      <label className="flex items-center gap-2 text-lsc-dark dark:text-lsc-cream">
        <input
          type="checkbox"
          checked={formData.is_active}
          onChange={(e) => updateField('is_active', e.target.checked)}
          className="rounded border-lsc-border dark:border-earth-700 text-lsc-rose focus:ring-lsc-rose"
        />
        <span className="text-sm font-medium">Active</span>
      </label>

      {/* Actions */}
      <div className="flex items-center gap-3 pt-2">
        <button
          onClick={handleSave}
          disabled={saving}
          className="bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg px-4 py-2 flex items-center gap-2 disabled:opacity-50"
        >
          {saving ? (
            <Loader2 className="h-4 w-4 motion-safe:animate-spin" />
          ) : (
            <Save className="h-4 w-4" />
          )}
          {creating ? 'Create Profile' : 'Save Changes'}
        </button>
        <button
          onClick={cancelEdit}
          className="text-lsc-dark/70 hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-lg px-4 py-2"
        >
          Cancel
        </button>
      </div>
    </div>
  )

  const renderViewFields = () => {
    if (!profile) return null
    const row = (label: string, value: React.ReactNode) => (
      <div className="flex justify-between py-2 border-b border-lsc-border dark:border-earth-700 last:border-0">
        <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{label}</span>
        <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">{value}</span>
      </div>
    )

    return (
      <div className="space-y-1">
        {row('Employment Type', renderBadge(profile.employment_type))}
        {row('Contracted Hours / Week', profile.contracted_hours_per_week)}
        {row('Min Hours / Week', profile.min_hours_per_week)}
        {row('Max Hours / Week', profile.max_hours_per_week)}
        {row('Max Consecutive Days', profile.max_consecutive_days)}
        {row('Min Hours Between Shifts', profile.min_hours_between_shifts)}
        {row('Max Weekend Shifts / Month', profile.max_weekend_shifts_per_month)}
        {row('Max Closing Shifts / Week', profile.max_closing_shifts_per_week)}
        {row('Seniority Level', profile.seniority_level)}
        {row('Hire Date', profile.hire_date || '\u2014')}
        {row('Branch ID', profile.branch_id ?? '\u2014')}
        {row(
          'Status',
          profile.is_active ? (
            <span className="text-lsc-green font-medium">Active</span>
          ) : (
            <span className="text-status-danger-500 font-medium">Inactive</span>
          )
        )}
        {row('Desirable Shift Score', profile.desirable_shift_score.toFixed(2))}
        <div className="pt-3">
          <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Skills</span>
          <div className="flex flex-wrap gap-2 mt-2">
            {profile.skills.length > 0 ? (
              renderSkillBadges(profile.skills)
            ) : (
              <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 italic">None</span>
            )}
          </div>
        </div>
      </div>
    )
  }

  return (
    <AdminShell
      title="Staff Scheduling Profiles"
      subtitle="Manage staff availability and constraints"
    >
      {/* Lookup */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-6 mb-6">
        <div className="flex items-center gap-2 mb-4">
          <Search className="h-5 w-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
          <h3 className="text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
            Look Up Staff Profile
          </h3>
        </div>
        <div className="flex gap-3">
          <input
            type="number"
            className={INPUT_CLASS + ' max-w-xs'}
            placeholder="Staff ID"
            value={staffIdInput}
            onChange={(e) => setStaffIdInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') loadProfile()
            }}
            min={1}
          />
          <button
            onClick={loadProfile}
            disabled={loading}
            className="bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg px-4 py-2 flex items-center gap-2 disabled:opacity-50"
          >
            {loading ? (
              <Loader2 className="h-4 w-4 motion-safe:animate-spin" />
            ) : (
              <User className="h-4 w-4" />
            )}
            Load Profile
          </button>
        </div>
      </div>

      {/* Not found */}
      {notFound && (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-6 mb-6">
          <div className="flex items-center gap-3 mb-4">
            <Briefcase className="h-5 w-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
            <p className="text-lsc-dark dark:text-lsc-cream">
              No profile found for staff ID <strong>{staffIdInput}</strong>.
            </p>
          </div>
          <button
            onClick={startCreate}
            className="bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg px-4 py-2 flex items-center gap-2"
          >
            <Plus className="h-4 w-4" /> Create Profile
          </button>
        </div>
      )}

      {/* Create form */}
      {creating && (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-6 mb-6">
          <div className="flex items-center gap-2 mb-6">
            <Plus className="h-5 w-5 text-lsc-rose" />
            <h3 className="text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
              Create Profile for Staff #{formData.staff_id}
            </h3>
          </div>
          {renderFormFields()}
        </div>
      )}

      {/* Profile view/edit */}
      {profile && !creating && (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-6">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-2">
              <User className="h-5 w-5 text-lsc-rose" />
              <h3 className="text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
                Staff #{profile.staff_id}
              </h3>
              {renderBadge(profile.employment_type)}
            </div>
            {!editing && (
              <button
                onClick={startEdit}
                className="text-lsc-dark/70 hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-lg px-4 py-2 flex items-center gap-2"
              >
                <Edit2 className="h-4 w-4" /> Edit
              </button>
            )}
          </div>
          {editing ? renderFormFields() : renderViewFields()}
        </div>
      )}
    </AdminShell>
  )
}

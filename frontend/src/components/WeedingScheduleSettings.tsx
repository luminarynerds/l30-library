/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect } from 'react'
import { useOrganizationFeatures } from '../contexts/OrganizationFeaturesContext'
import api from '@/lib/api-client'
import toast from 'react-hot-toast'
import { API_BASE } from '@/api/types'
import {
  Save, RefreshCw, Calendar, Mail, Shield, Clock, Zap, Info,
} from 'lucide-react'

interface WeedingScheduleConfig {
  enabled: boolean
  frequency: 'weekly' | 'monthly'
  day_of_week: number
  min_crew_score: number
  max_results: number
  auto_approve_duplicates: boolean
  auto_approve_never_circulated: boolean
  never_circulated_years: number
  notify_email: string
  email_enabled: boolean
}

const DEFAULT_CONFIG: WeedingScheduleConfig = {
  enabled: false,
  frequency: 'monthly',
  day_of_week: 0,
  min_crew_score: 50,
  max_results: 200,
  auto_approve_duplicates: false,
  auto_approve_never_circulated: false,
  never_circulated_years: 5,
  notify_email: '',
  email_enabled: false,
}

const DAYS_OF_WEEK = [
  'Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday',
]

export default function WeedingScheduleSettings({ token: _token, onRunAnalysis }: {
  token: string
  onRunAnalysis: () => Promise<void>
}) {
  const { features, refetch } = useOrganizationFeatures()
  const [saving, setSaving] = useState(false)
  const [running, setRunning] = useState(false)
  const [config, setConfig] = useState<WeedingScheduleConfig>(DEFAULT_CONFIG)

  useEffect(() => {
    if (features?.configuration) {
      const saved = (features.configuration as Record<string, unknown>)?.weeding_schedule as Partial<WeedingScheduleConfig> | undefined
      if (saved) {
        setConfig({ ...DEFAULT_CONFIG, ...saved })
      }
    }
  }, [features])

  const handleSave = async () => {
    if (config.email_enabled && config.notify_email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(config.notify_email)) {
      toast.error('Please enter a valid email address')
      return
    }
    try {
      setSaving(true)
      const payload = {
        configuration: {
          ...(features?.configuration || {}),
          weeding_schedule: config,
        },
        reason: 'Update weeding schedule settings',
      }
      await api.patch(`${API_BASE}/organization-features`, payload)
      await refetch()
      toast.success('Weeding schedule settings saved')
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } }
      toast.error(err.response?.data?.detail || 'Failed to save settings')
    } finally {
      setSaving(false)
    }
  }

  const handleRunNow = async () => {
    setRunning(true)
    try {
      await onRunAnalysis()
    } finally {
      setRunning(false)
    }
  }

  const updateConfig = <K extends keyof WeedingScheduleConfig>(
    field: K,
    value: WeedingScheduleConfig[K],
  ) => {
    setConfig(prev => ({ ...prev, [field]: value }))
  }

  return (
    <div className="space-y-5">
      {/* Section Header */}
      <div className="flex items-center gap-2">
        <Calendar className="w-5 h-5 text-lsc-rose" />
        <h3 className="font-serif text-base font-semibold text-earth-800 dark:text-earth-100">
          Scheduled Analysis
        </h3>
      </div>

      <div className="bg-status-warning-50 dark:bg-status-warning-900/20 border border-status-warning-200 dark:border-status-warning-800 rounded-lg p-3 flex gap-3">
        <Info className="w-4 h-4 text-status-warning-700 dark:text-status-warning-300 flex-shrink-0 mt-0.5" />
        <p className="text-xs text-status-warning-800 dark:text-status-warning-200">
          Configure automatic CREW analysis runs. The system will scan your collection
          on the configured schedule and optionally auto-approve low-risk candidates.
        </p>
      </div>

      {/* Schedule Frequency */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-lg p-5 border border-lsc-border dark:border-earth-700 space-y-4">
        <div className="flex items-center gap-2 mb-1">
          <Clock className="w-4 h-4 text-lsc-rose" />
          <h4 className="text-sm font-semibold text-lsc-dark/70 dark:text-lsc-cream/70">Frequency</h4>
        </div>

        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={config.enabled}
              onChange={e => updateConfig('enabled', e.target.checked)}
              className="rounded border-lsc-border text-lsc-green focus:ring-lsc-green"
            />
            <span className="text-sm text-lsc-dark dark:text-lsc-cream">Enable scheduled analysis</span>
          </label>
        </div>

        {config.enabled && (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-3">
            <div>
              <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                Run Every
              </label>
              <select
                value={config.frequency}
                onChange={e => updateConfig('frequency', e.target.value as 'weekly' | 'monthly')}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream text-sm"
              >
                <option value="weekly">Weekly</option>
                <option value="monthly">Monthly (1st of month)</option>
              </select>
            </div>

            {config.frequency === 'weekly' && (
              <div>
                <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                  Day of Week
                </label>
                <select
                  value={config.day_of_week}
                  onChange={e => updateConfig('day_of_week', parseInt(e.target.value))}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream text-sm"
                >
                  {DAYS_OF_WEEK.map((day, i) => (
                    <option key={i} value={i}>{day}</option>
                  ))}
                </select>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Auto-Approve Settings */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-lg p-5 border border-lsc-border dark:border-earth-700 space-y-4">
        <div className="flex items-center gap-2 mb-1">
          <Shield className="w-4 h-4 text-lsc-rose" />
          <h4 className="text-sm font-semibold text-lsc-dark/70 dark:text-lsc-cream/70">Auto-Approve Rules</h4>
        </div>
        <p className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60">
          Low-risk candidates matching these rules will be automatically approved during scheduled runs.
        </p>

        <div className="space-y-3">
          <label className="flex items-start gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={config.auto_approve_duplicates}
              onChange={e => updateConfig('auto_approve_duplicates', e.target.checked)}
              className="rounded border-lsc-border text-lsc-green focus:ring-lsc-green mt-0.5"
            />
            <div>
              <span className="text-sm text-lsc-dark dark:text-lsc-cream">Auto-approve excess duplicates</span>
              <p className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60">
                Copies identified as excess by duplicate detection will be auto-approved for weeding.
              </p>
            </div>
          </label>

          <label className="flex items-start gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={config.auto_approve_never_circulated}
              onChange={e => updateConfig('auto_approve_never_circulated', e.target.checked)}
              className="rounded border-lsc-border text-lsc-green focus:ring-lsc-green mt-0.5"
            />
            <div>
              <span className="text-sm text-lsc-dark dark:text-lsc-cream">Auto-approve never-circulated items</span>
              <p className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60">
                Items that have never been checked out and are older than the threshold below.
              </p>
            </div>
          </label>

          {config.auto_approve_never_circulated && (
            <div className="ml-6">
              <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                Minimum age (years)
              </label>
              <input
                type="number"
                min={1}
                max={20}
                value={config.never_circulated_years}
                onChange={e => updateConfig('never_circulated_years', parseInt(e.target.value) || 5)}
                className="w-24 px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream text-sm"
              />
              <p className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60 mt-1">
                Items acquired more than {config.never_circulated_years} years ago with zero checkouts.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Email Notifications */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-lg p-5 border border-lsc-border dark:border-earth-700 space-y-4">
        <div className="flex items-center gap-2 mb-1">
          <Mail className="w-4 h-4 text-lsc-rose" />
          <h4 className="text-sm font-semibold text-lsc-dark/70 dark:text-lsc-cream/70">Email Notifications</h4>
        </div>

        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={config.email_enabled}
            onChange={e => updateConfig('email_enabled', e.target.checked)}
            className="rounded border-lsc-border text-lsc-green focus:ring-lsc-green"
          />
          <span className="text-sm text-lsc-dark dark:text-lsc-cream">Send analysis summary by email</span>
        </label>

        {config.email_enabled && (
          <div>
            <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
              Collection Manager Email
            </label>
            <input
              type="email"
              value={config.notify_email}
              onChange={e => updateConfig('notify_email', e.target.value)}
              placeholder="collections@library.org"
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream text-sm"
            />
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="flex flex-col sm:flex-row gap-3">
        <button
          onClick={handleSave}
          disabled={saving}
          className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg transition-colors disabled:opacity-50 text-sm font-medium"
        >
          {saving ? <RefreshCw className="w-4 h-4 motion-safe:animate-spin" /> : <Save className="w-4 h-4" />}
          {saving ? 'Saving...' : 'Save Schedule Settings'}
        </button>

        <button
          onClick={handleRunNow}
          disabled={running}
          className="flex items-center justify-center gap-2 px-4 py-2.5 bg-lsc-green hover:bg-status-success-700 text-white rounded-lg transition-colors disabled:opacity-50 text-sm font-medium"
        >
          {running ? <RefreshCw className="w-4 h-4 motion-safe:animate-spin" /> : <Zap className="w-4 h-4" />}
          {running ? 'Running...' : 'Run Analysis Now'}
        </button>
      </div>
    </div>
  )
}

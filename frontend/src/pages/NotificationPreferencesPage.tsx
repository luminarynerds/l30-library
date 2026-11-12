/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import {
  Bell, Mail, Smartphone, Monitor,
  ArrowLeft, ChevronDown, ChevronRight, Save, Info, Loader2
} from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { useTranslation} from '@/i18n'
import { fetchApi } from '@/lib/api-client'
import toast from 'react-hot-toast'

// --- API response types ---

interface ChannelPreference {
  notification_type: string
  label: string
  description: string | null
  channel_email: boolean
  channel_in_app: boolean
  channel_sms: boolean
  is_digest: boolean
}

interface DigestConfig {
  enabled: boolean
  frequency: string
  preferred_time: string | null
  preferred_day: number | null
}

interface QuietHoursConfig {
  enabled: boolean
  start_time: string | null
  end_time: string | null
  days: number[]
}

interface FullNotificationSettings {
  preferences: ChannelPreference[]
  digest: DigestConfig
  quiet_hours: QuietHoursConfig
}

interface NotificationType {
  id: string
  label: string
  description: string
  category: string
  channelEmail: boolean
  channelInApp: boolean
  channelSms: boolean
  isDigest: boolean
}

const CRITICAL_NOTIFICATION_TYPES = ['hold_ready', 'hold_expiring', 'overdue_notice']

const DEFAULT_NOTIFICATION_TYPES: NotificationType[] = [
  { id: 'checkout_receipt', label: 'Checkout Receipt', description: 'Email confirmation when you check out items', category: 'Circulation', channelEmail: true, channelInApp: true, channelSms: false, isDigest: false },
  { id: 'due_date_reminder', label: 'Due Date Reminder', description: 'Reminder before items are due', category: 'Circulation', channelEmail: true, channelInApp: true, channelSms: false, isDigest: false },
  { id: 'overdue_notice', label: 'Overdue Notice', description: 'Notification when items become overdue', category: 'Circulation', channelEmail: true, channelInApp: true, channelSms: false, isDigest: false },
  { id: 'hold_ready', label: 'Hold Ready', description: 'When holds are ready for pickup', category: 'Circulation', channelEmail: true, channelInApp: true, channelSms: false, isDigest: false },
  { id: 'hold_expiring', label: 'Hold Expiring', description: 'Reminder before holds expire', category: 'Circulation', channelEmail: true, channelInApp: true, channelSms: false, isDigest: false },
  { id: 'fine_notice', label: 'Fine Notice', description: 'Notifications about fines', category: 'Circulation', channelEmail: true, channelInApp: true, channelSms: false, isDigest: false },
  { id: 'event_reminder', label: 'Event Reminder', description: 'Reminders for registered events', category: 'Events', channelEmail: true, channelInApp: true, channelSms: false, isDigest: false },
  { id: 'reading_program', label: 'Reading Program', description: 'Updates on reading program progress', category: 'Programs', channelEmail: true, channelInApp: true, channelSms: false, isDigest: false },
  { id: 'new_arrivals', label: 'New Arrivals', description: 'When new items match your interests', category: 'Discovery', channelEmail: true, channelInApp: true, channelSms: false, isDigest: false },
  { id: 'book_club', label: 'Book Club', description: 'Book club discussions and meetings', category: 'Community', channelEmail: true, channelInApp: true, channelSms: false, isDigest: false },
  { id: 'system_announcement', label: 'System Announcements', description: 'Library-wide announcements', category: 'System', channelEmail: true, channelInApp: true, channelSms: false, isDigest: false },
]

const CATEGORIES = ['Circulation', 'Events', 'Programs', 'Discovery', 'Community', 'System']

const getCategoryForType = (type: string): string => {
  const categoryMap: Record<string, string> = {
    checkout_receipt: 'Circulation',
    due_date_reminder: 'Circulation',
    overdue_notice: 'Circulation',
    hold_ready: 'Circulation',
    hold_expiring: 'Circulation',
    hold_cancelled: 'Circulation',
    fine_notice: 'Circulation',
    event_reminder: 'Events',
    reading_program: 'Programs',
    new_arrivals: 'Discovery',
    book_club: 'Community',
    system_announcement: 'System',
  }
  return categoryMap[type] || 'System'
}

export default function NotificationPreferencesPage(): React.ReactElement {
  const { t } = useTranslation()
  const { isAuthenticated } = useAuth()
  const [preferences, setPreferences] = useState<NotificationType[]>(DEFAULT_NOTIFICATION_TYPES)
  const [digestEnabled, setDigestEnabled] = useState(false)
  const [digestFrequency, setDigestFrequency] = useState<'daily' | 'weekly'>('daily')
  const [digestTime, setDigestTime] = useState('09:00')
  const [quietHoursEnabled, setQuietHoursEnabled] = useState(false)
  const [quietStart, setQuietStart] = useState('22:00')
  const [quietEnd, setQuietEnd] = useState('08:00')
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set(['Circulation']))
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)

  const loadSettings = useCallback(async () => {
    setLoading(true)
    try {
      const settings = await fetchApi<FullNotificationSettings>('/notifications/preferences')
      if (settings.preferences?.length) {
        setPreferences(settings.preferences.map(p => ({
          id: p.notification_type,
          label: p.label,
          description: p.description || '',
          category: getCategoryForType(p.notification_type),
          channelEmail: p.channel_email,
          channelInApp: p.channel_in_app,
          channelSms: p.channel_sms,
          isDigest: p.is_digest,
        })))
      }
      if (settings.digest) {
        setDigestEnabled(settings.digest.enabled)
        setDigestFrequency(settings.digest.frequency as 'daily' | 'weekly')
        setDigestTime(settings.digest.preferred_time || '09:00')
      }
      if (settings.quiet_hours) {
        setQuietHoursEnabled(settings.quiet_hours.enabled)
        setQuietStart(settings.quiet_hours.start_time || '22:00')
        setQuietEnd(settings.quiet_hours.end_time || '08:00')
      }
    } catch (err) {
      Sentry.captureException(err instanceof Error ? err : new Error(String(err)))
      toast.error(t('toast.notificationPreferences.failedToLoadNotificationPreferences'))
    } finally {
      setLoading(false)
    }
  }, [t])

  useEffect(() => {
    if (!isAuthenticated) return
    loadSettings()
  }, [isAuthenticated, loadSettings])

  const handleSave = async () => {
    // Validate critical notification types have at least one channel
    const criticalWithNoChannels = preferences.filter(
      p => CRITICAL_NOTIFICATION_TYPES.includes(p.id) &&
        !p.channelEmail && !p.channelInApp && !p.channelSms
    )
    if (criticalWithNoChannels.length > 0) {
      toast.error('Hold and overdue notifications must have at least one channel enabled.')
      return
    }

    setSaving(true)
    try {
      await fetchApi('/notifications/preferences', {
        method: 'PUT',
        body: {
          preferences: preferences.map(p => ({
            notification_type: p.id,
            label: p.label,
            description: p.description,
            channel_email: p.channelEmail,
            channel_in_app: p.channelInApp,
            channel_sms: p.channelSms,
            is_digest: p.isDigest,
          }))
        }
      })
      await fetchApi('/notifications/digest-config', {
        method: 'PUT',
        body: {
          enabled: digestEnabled,
          frequency: digestFrequency,
          preferred_time: digestTime,
          preferred_day: digestFrequency === 'weekly' ? 0 : null,
        }
      })
      await fetchApi('/notifications/quiet-hours', {
        method: 'PUT',
        body: {
          enabled: quietHoursEnabled,
          start_time: quietStart,
          end_time: quietEnd,
          days: [0, 1, 2, 3, 4, 5, 6],
        }
      })
      toast.success(t('toast.notificationPreferences.notificationPreferencesSaved'))
    } catch (err) {
      toast.error(t('toast.notificationPreferences.failedToSavePreferences'))
      Sentry.captureException(err instanceof Error ? err : new Error(String(err)))
    } finally {
      setSaving(false)
    }
  }

  if (!isAuthenticated) {
    return (
      <div className="py-12 text-center">
        <Bell className="w-12 h-12 text-lsc-rose/30 mx-auto mb-4" />
        <h2 className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream mb-2">{t('notificationPreferences.signInToManageNotifications')}</h2>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('notificationPreferences.controlHowYouReceiveUpdates')}</p>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <Link
          to="/account"
          className="inline-flex items-center gap-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Account
        </Link>
        <div className="flex flex-col items-center justify-center py-20">
          <Loader2 className="w-8 h-8 text-lsc-rose motion-safe:animate-spin mb-4" />
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Loading notification preferences...</p>
        </div>
      </div>
    )
  }

  const toggleCategory = (category: string) => {
    setExpandedCategories(prev => {
      const next = new Set(prev)
      if (next.has(category)) next.delete(category)
      else next.add(category)
      return next
    })
  }

  const updatePreference = (id: string, field: keyof NotificationType, value: boolean) => {
    setPreferences(prev => prev.map(p => p.id === id ? { ...p, [field]: value } : p))
  }

  return (
    <div className="space-y-6">
      {/* Back Link */}
      <Link
        to="/account"
        className="inline-flex items-center gap-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Account
      </Link>

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
            Notification Preferences
          </h1>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
            Choose how and when you hear from us. Your way, your pace.
          </p>
        </div>
      </div>

      {/* Channel Legend */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700">
        <div className="flex flex-wrap items-center gap-6 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
          <span className="flex items-center gap-2">
            <Mail className="w-4 h-4" /> Email
          </span>
          <span className="flex items-center gap-2">
            <Monitor className="w-4 h-4" /> In-App
          </span>
          <span className="flex items-center gap-2">
            <Smartphone className="w-4 h-4" /> SMS
          </span>
        </div>
      </div>

      {/* Per-Type Preferences */}
      <div className="space-y-3">
        {CATEGORIES.map(category => {
          const categoryPrefs = preferences.filter(p => p.category === category)
          if (categoryPrefs.length === 0) return null
          const isExpanded = expandedCategories.has(category)

          return (
            <div key={category} className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 overflow-hidden">
              <button
                onClick={() => toggleCategory(category)}
                className="w-full flex items-center gap-3 px-6 py-4 hover:bg-lsc-cream/50 dark:hover:bg-earth-700/50 transition-colors"
                aria-expanded={isExpanded}
              >
                <Bell className="w-5 h-5 text-lsc-rose flex-shrink-0" />
                <span className="flex-1 text-left font-semibold text-lsc-dark dark:text-lsc-cream">{category}</span>
                <span className="px-2 py-0.5 bg-lsc-cream dark:bg-earth-700 rounded-full text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70">
                  {categoryPrefs.length}
                </span>
                {isExpanded ? <ChevronDown className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/60" /> : <ChevronRight className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/60" />}
              </button>

              {isExpanded && (
                <div className="border-t border-lsc-border dark:border-earth-700">
                  {/* Column headers */}
                  <div className="hidden sm:grid grid-cols-[1fr_auto_auto_auto] gap-4 px-6 py-2 bg-lsc-cream/30 dark:bg-earth-900/30">
                    <span className="text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase tracking-wider">Type</span>
                    <span className="w-16 text-center text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase tracking-wider">Email</span>
                    <span className="w-16 text-center text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase tracking-wider">In-App</span>
                    <span className="w-16 text-center text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase tracking-wider">SMS</span>
                  </div>

                  {categoryPrefs.map(pref => (
                    <div key={pref.id} className="grid grid-cols-1 sm:grid-cols-[1fr_auto_auto_auto] gap-4 px-6 py-4 border-t border-lsc-border/50 dark:border-earth-700/50 items-center">
                      <div>
                        <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                          {pref.label}
                          {CRITICAL_NOTIFICATION_TYPES.includes(pref.id) && (
                            <span className="ml-2 inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wide bg-lsc-rose/10 text-lsc-rose border border-lsc-rose/20">
                              Required
                            </span>
                          )}
                        </p>
                        <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{pref.description}</p>
                      </div>
                      <label className="w-16 flex items-center justify-center cursor-pointer">
                        <input
                          type="checkbox"
                          checked={pref.channelEmail}
                          onChange={(e) => updatePreference(pref.id, 'channelEmail', e.target.checked)}
                          className="w-5 h-5 text-lsc-rose border-sage/30 rounded focus:ring-lsc-rose"
                          aria-label={`${pref.label} - Email`}
                        />
                      </label>
                      <label className="w-16 flex items-center justify-center cursor-pointer">
                        <input
                          type="checkbox"
                          checked={pref.channelInApp}
                          onChange={(e) => updatePreference(pref.id, 'channelInApp', e.target.checked)}
                          className="w-5 h-5 text-lsc-rose border-sage/30 rounded focus:ring-lsc-rose"
                          aria-label={`${pref.label} - In-App`}
                        />
                      </label>
                      <label className="w-16 flex items-center justify-center cursor-pointer">
                        <input
                          type="checkbox"
                          checked={pref.channelSms}
                          onChange={(e) => updatePreference(pref.id, 'channelSms', e.target.checked)}
                          className="w-5 h-5 text-lsc-rose border-sage/30 rounded focus:ring-lsc-rose"
                          aria-label={`${pref.label} - SMS`}
                        />
                      </label>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Digest Settings */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700">
        <h2 className="font-serif font-bold text-lg text-lsc-dark dark:text-lsc-cream mb-1">
          Digest Mode
        </h2>
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
          Prefer fewer interruptions? Bundle your notifications into a single summary.
        </p>

        <label className="flex items-center gap-3 cursor-pointer mb-4">
          <input
            type="checkbox"
            checked={digestEnabled}
            onChange={(e) => setDigestEnabled(e.target.checked)}
            className="w-5 h-5 text-lsc-rose border-sage/30 rounded focus:ring-lsc-rose"
          />
          <div>
            <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">Enable digest mode</span>
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{t('notificationPreferences.batchNotificationsIntoADaily')}</p>
          </div>
        </label>

        {digestEnabled && (
          <div className="grid sm:grid-cols-2 gap-4 pl-8">
            <div>
              <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Frequency</label>
              <select
                value={digestFrequency}
                onChange={(e) => setDigestFrequency(e.target.value as 'daily' | 'weekly')}
                className="w-full px-4 py-2 border border-sage/30 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose"
              >
                <option value="daily">Daily</option>
                <option value="weekly">Weekly</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Preferred time</label>
              <input
                type="time"
                value={digestTime}
                onChange={(e) => setDigestTime(e.target.value)}
                className="w-full px-4 py-2 border border-sage/30 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose"
              />
            </div>
          </div>
        )}
      </div>

      {/* Quiet Hours */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700">
        <h2 className="font-serif font-bold text-lg text-lsc-dark dark:text-lsc-cream mb-1">
          Quiet Hours
        </h2>
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
          Need a break? Pause notifications during specific hours. They'll be waiting for you when you're ready.
        </p>

        <label className="flex items-center gap-3 cursor-pointer mb-4">
          <input
            type="checkbox"
            checked={quietHoursEnabled}
            onChange={(e) => setQuietHoursEnabled(e.target.checked)}
            className="w-5 h-5 text-lsc-rose border-sage/30 rounded focus:ring-lsc-rose"
          />
          <div>
            <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">Enable quiet hours</span>
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{t('notificationPreferences.notificationsWillBeHeldUntil')}</p>
          </div>
        </label>

        {quietHoursEnabled && (
          <div className="grid sm:grid-cols-2 gap-4 pl-8">
            <div>
              <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Start time</label>
              <input
                type="time"
                value={quietStart}
                onChange={(e) => setQuietStart(e.target.value)}
                className="w-full px-4 py-2 border border-sage/30 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">End time</label>
              <input
                type="time"
                value={quietEnd}
                onChange={(e) => setQuietEnd(e.target.value)}
                className="w-full px-4 py-2 border border-sage/30 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose"
              />
            </div>
          </div>
        )}

        {quietHoursEnabled && (
          <p className="mt-3 pl-8 text-xs text-lsc-dark/70 dark:text-lsc-cream/70 flex items-start gap-1.5">
            <Info className="w-3.5 h-3.5 text-lsc-rose flex-shrink-0 mt-0.5" />
            Urgent notifications (hold ready, overdue) are always delivered regardless of quiet hours settings.
          </p>
        )}
      </div>

      {/* Save Button & Info Note */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-4 bg-lsc-rose/5 dark:bg-lsc-rose/10 rounded-xl border border-lsc-rose/20">
        <div className="flex items-start gap-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
          <Info className="w-5 h-5 text-lsc-rose flex-shrink-0 mt-0.5" />
          <span>Changes take effect immediately for in-app notifications and within the next scheduled delivery for email and SMS.</span>
        </div>
        <button
          onClick={handleSave}
          disabled={saving}
          className="flex items-center gap-2 px-6 py-3 bg-lsc-rose text-white rounded-xl font-medium hover:bg-lsc-rose/90 transition-colors disabled:opacity-50 flex-shrink-0"
        >
          {saving ? <Loader2 className="w-4 h-4 motion-safe:animate-spin" /> : <Save className="w-4 h-4" />}
          {saving ? 'Saving...' : 'Save Preferences'}
        </button>
      </div>
    </div>
  )
}

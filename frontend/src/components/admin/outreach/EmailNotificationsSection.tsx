/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useState, useEffect, useMemo } from 'react'
import toast from 'react-hot-toast'
import api from '@/lib/api-client'
import { API_BASE } from '@/api/types'
import {
  Settings,
  Mail,
  ToggleRight,
  AlertCircle,
  Send,
  Eye,
  Clock,
  Bell,
  RefreshCw,
  CheckCircle2,
  XCircle,
  Save,
} from 'lucide-react'
import { useTranslation } from '@/i18n'
import {
  SettingsCard,
  SettingsGrid,
  ToggleRow,
  NumberField,
  TextField,
  InfoBanner,
  StatCard,
  StatGrid,
  AuditTrailAccordion,
  type AuditTrailEntry,
} from '@/components/admin'
import { useConfigurationSection } from '@/hooks/useConfigurationSection'
import { SectionShell } from '../ai-settings/SectionShell'

interface NotificationConfig extends Record<string, unknown> {
  notifications_enabled: boolean
  courtesy_notice_enabled: boolean
  courtesy_notice_days_before: number
  overdue_notice_enabled: boolean
  overdue_notice_frequency_days: number
  overdue_max_notices_before_suspension: number
  hold_placed_notification_enabled: boolean
  hold_ready_notification_enabled: boolean
  hold_expiring_soon_notification_enabled: boolean
  hold_expiring_soon_days: number
  event_reminder_enabled: boolean
  event_reminder_days_before: number
  patron_default_email_notifications: boolean
  patron_default_sms_notifications: boolean
}

const DEFAULT_CONFIG: NotificationConfig = {
  notifications_enabled: true,
  courtesy_notice_enabled: true,
  courtesy_notice_days_before: 3,
  overdue_notice_enabled: true,
  overdue_notice_frequency_days: 7,
  overdue_max_notices_before_suspension: 3,
  hold_placed_notification_enabled: true,
  hold_ready_notification_enabled: true,
  hold_expiring_soon_notification_enabled: true,
  hold_expiring_soon_days: 3,
  event_reminder_enabled: true,
  event_reminder_days_before: 7,
  patron_default_email_notifications: true,
  patron_default_sms_notifications: false,
}

interface NotificationTemplate {
  id: string
  name: string
  subject: string
  preview: string
  variables: string[]
}

const NOTIFICATION_TEMPLATES: NotificationTemplate[] = [
  {
    id: 'courtesy_notice',
    name: 'Courtesy Notice',
    subject: 'Reminder: Item due on {due_date}',
    preview: 'Dear {patron_name}, your item "{item_title}" is due on {due_date}. Please renew or return it on time.',
    variables: ['patron_name', 'item_title', 'due_date', 'library_name'],
  },
  {
    id: 'overdue_notice',
    name: 'Overdue Notice',
    subject: 'Your item is now overdue',
    preview: 'Dear {patron_name}, your item "{item_title}" is now overdue. Please return or renew it immediately. Late fees may apply.',
    variables: ['patron_name', 'item_title', 'overdue_days', 'late_fee', 'library_name'],
  },
  {
    id: 'hold_placed',
    name: 'Hold Placed Confirmation',
    subject: 'Your hold for {item_title} has been placed',
    preview: 'Dear {patron_name}, we have placed a hold on "{item_title}". You will be notified when it is ready for pickup.',
    variables: ['patron_name', 'item_title', 'position_in_queue', 'library_name'],
  },
  {
    id: 'hold_ready',
    name: 'Hold Ready for Pickup',
    subject: '{item_title} is ready for pickup',
    preview: 'Dear {patron_name}, your hold "{item_title}" is ready for pickup at {branch_location}. Please pick it up within {hold_available_days} days.',
    variables: ['patron_name', 'item_title', 'branch_location', 'hold_available_days'],
  },
  {
    id: 'hold_expiring',
    name: 'Hold Expiring Soon',
    subject: 'Your hold expires soon',
    preview: 'Dear {patron_name}, your hold "{item_title}" will expire in {days_remaining} days. Please pick it up soon.',
    variables: ['patron_name', 'item_title', 'days_remaining', 'branch_location'],
  },
  {
    id: 'event_reminder',
    name: 'Event Reminder',
    subject: 'Reminder: {event_title} is coming up',
    preview: 'Dear {patron_name}, we wanted to remind you that "{event_title}" is scheduled for {event_date} at {branch_location}. We hope to see you there!',
    variables: ['patron_name', 'event_title', 'event_date', 'event_time', 'branch_location'],
  },
]

interface StaffActivityLog {
  id: number
  action?: string
  activity_type?: string
  changes?: Record<string, { old: unknown; new: unknown }>
  details?: Record<string, { old: unknown; new: unknown }>
  changed_by?: string
  admin_email?: string
  changed_at?: string
  created_at?: string
}

interface EmailNotificationsSectionProps {
  onBack: () => void
}

export function EmailNotificationsSection({ onBack }: EmailNotificationsSectionProps) {
  const { t } = useTranslation()
  const {
    value: config,
    setField,
    loading,
    saving,
    save,
  } = useConfigurationSection<NotificationConfig>('notification_settings', DEFAULT_CONFIG, {
    successMessage: t('admin.adminEmailNotificationConfig.emailNotificationSettingsUpdatedSuccessfully'),
    errorMessage: t('toast.adminEmailNotificationConfig.failedToUpdateNotificationSettings'),
    defaultReason: 'Admin update via email notification settings UI',
  })

  const [reason, setReason] = useState('')
  const [testEmail, setTestEmail] = useState('')
  const [testingEmail, setTestingEmail] = useState(false)
  const [selectedTemplateId, setSelectedTemplateId] = useState<string | null>(null)
  const [auditEntries, setAuditEntries] = useState<AuditTrailEntry[]>([])

  const loadAuditLogs = async () => {
    try {
      const response = await api.get<{ logs?: StaffActivityLog[] }>(
        `${API_BASE}/admin/audit/staff-activity?page=1&page_size=10`,
      )
      const logs = response?.logs || []
      setAuditEntries(
        logs.map((log) => ({
          timestamp: log.changed_at || log.created_at || new Date().toISOString(),
          updated_by:
            log.changed_by || log.admin_email || log.action || log.activity_type || 'Unknown',
          changes: Object.entries(log.changes || log.details || {}).map(
            ([field, change]) => ({
              field,
              before: String(change.old),
              after: String(change.new),
            }),
          ),
        })),
      )
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      setAuditEntries([])
    }
  }


  useEffect(() => {
    void loadAuditLogs()
  }, [])

  const handleSave = async () => {
    await save(reason || undefined)
    setReason('')
    void loadAuditLogs()
  }

  const handleTestEmail = async () => {
    if (!testEmail) {
      toast.error(t('admin.adminEmailNotificationConfig.pleaseEnterATestEmail'))
      return
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(testEmail)) {
      toast.error(t('admin.adminEmailNotificationConfig.pleaseEnterAValidEmail'))
      return
    }
    try {
      setTestingEmail(true)
      await api.post(`${API_BASE}/notifications/send-test`, {
        email: testEmail,
        template_id: 'test_notification',
      })
      toast.success(
        t('toast.adminEmailNotificationConfig.testEmailSentToTestemailaddress', {
          testemailaddress: testEmail,
        }),
      )
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } }
      toast.error(
        err.response?.data?.detail ||
          t('toast.adminEmailNotificationConfig.failedToSendTestEmail'),
      )
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
    } finally {
      setTestingEmail(false)
    }
  }

  const typesEnabled = useMemo(() => {
    return [
      config.courtesy_notice_enabled,
      config.overdue_notice_enabled,
      config.hold_placed_notification_enabled,
      config.hold_ready_notification_enabled,
      config.hold_expiring_soon_notification_enabled,
      config.event_reminder_enabled,
    ].filter(Boolean).length
  }, [config])

  if (loading) {
    return (
      <SectionShell
        title="Email Notifications"
        description="Controls what emails patrons get -- due date reminders, hold alerts, event reminders."
        tabs={[{ id: 'settings', label: 'Notification Settings', icon: Mail }]}
        defaultTab="settings"
        backLabel="Back to Outreach Dashboard"
        onBack={onBack}
      >
        {() => (
          <div className="flex items-center justify-center h-64">
            <RefreshCw className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" aria-hidden="true" />
          </div>
        )}
      </SectionShell>
    )
  }

  return (
    <SectionShell
      title="Email Notifications"
      description="Controls what emails patrons get -- due date reminders, hold alerts, event reminders."
      tabs={[{ id: 'settings', label: 'Notification Settings', icon: Mail }]}
      defaultTab="settings"
      backLabel="Back to Outreach Dashboard"
      onBack={onBack}
    >
      {() => (
        <div className="space-y-6">
          <InfoBanner
            tone={config.notifications_enabled ? 'success' : 'danger'}
            icon={config.notifications_enabled ? CheckCircle2 : XCircle}
          >
            <p className="font-medium mb-1">
              {config.notifications_enabled
                ? 'Email notifications are currently ENABLED globally'
                : 'Email notifications are currently DISABLED globally'}
            </p>
            <p className="text-xs">
              {config.notifications_enabled
                ? 'All configured notifications will be sent to patrons according to their preferences.'
                : 'No notifications will be sent until this setting is enabled. Individual notification types may also be disabled.'}
            </p>
          </InfoBanner>

          <SettingsCard title="Enable Email Notifications Globally" icon={ToggleRight}>
            <ToggleRow
              label="Master switch for all notification types"
              description="Controls whether any notifications are sent. Individual types below can still be toggled off."
              checked={config.notifications_enabled}
              onChange={(v) => setField('notifications_enabled', v)}
            />
          </SettingsCard>

          <SettingsCard title="Courtesy Notices" icon={Bell}>
            <ToggleRow
              label="Send courtesy notices"
              description="Notify patrons before due dates"
              checked={config.courtesy_notice_enabled}
              onChange={(v) => setField('courtesy_notice_enabled', v)}
            />
            {config.courtesy_notice_enabled && (
              <NumberField
                label="Days before due date to send notice"
                min={1}
                max={30}
                unit="days"
                value={config.courtesy_notice_days_before}
                onChange={(v) => setField('courtesy_notice_days_before', v)}
                help="Example: setting 3 will send notices 3 days before items are due"
              />
            )}
          </SettingsCard>

          <SettingsCard title="Overdue Notices" icon={AlertCircle}>
            <ToggleRow
              label="Send overdue notices"
              description="Send periodic notices for overdue items and manage suspension"
              checked={config.overdue_notice_enabled}
              onChange={(v) => setField('overdue_notice_enabled', v)}
            />
            {config.overdue_notice_enabled && (
              <SettingsGrid cols={2}>
                <NumberField
                  label="Frequency between notices"
                  min={1}
                  max={30}
                  unit="days"
                  value={config.overdue_notice_frequency_days}
                  onChange={(v) => setField('overdue_notice_frequency_days', v)}
                />
                <NumberField
                  label="Max notices before suspension"
                  min={1}
                  max={10}
                  unit="notices"
                  value={config.overdue_max_notices_before_suspension}
                  onChange={(v) => setField('overdue_max_notices_before_suspension', v)}
                />
              </SettingsGrid>
            )}
          </SettingsCard>

          <SettingsCard title="Hold Notifications" icon={Clock}>
            <ToggleRow
              label="Notify when hold is placed"
              description="Confirm placement and position in queue"
              checked={config.hold_placed_notification_enabled}
              onChange={(v) => setField('hold_placed_notification_enabled', v)}
            />
            <ToggleRow
              label={t('admin.adminEmailNotificationConfig.notifyWhenHoldIsReady')}
              description="Alert patron that item is available for pickup"
              checked={config.hold_ready_notification_enabled}
              onChange={(v) => setField('hold_ready_notification_enabled', v)}
            />
            <ToggleRow
              label="Notify when hold is expiring"
              description="Remind patrons to pick up their holds before expiration"
              checked={config.hold_expiring_soon_notification_enabled}
              onChange={(v) => setField('hold_expiring_soon_notification_enabled', v)}
            />
            {config.hold_expiring_soon_notification_enabled && (
              <NumberField
                label="Days before expiration to send notice"
                min={1}
                max={14}
                unit="days"
                value={config.hold_expiring_soon_days}
                onChange={(v) => setField('hold_expiring_soon_days', v)}
              />
            )}
          </SettingsCard>

          <SettingsCard title="Event Reminders" icon={Bell}>
            <ToggleRow
              label="Send event reminders"
              description="Send reminders for upcoming library events"
              checked={config.event_reminder_enabled}
              onChange={(v) => setField('event_reminder_enabled', v)}
            />
            {config.event_reminder_enabled && (
              <NumberField
                label="Days before event to send reminder"
                min={1}
                max={30}
                unit="days"
                value={config.event_reminder_days_before}
                onChange={(v) => setField('event_reminder_days_before', v)}
              />
            )}
          </SettingsCard>

          <SettingsCard
            title="Patron Default Preferences"
            icon={Settings}
            description="Default notification preferences for new patron accounts"
          >
            <ToggleRow
              label="Email Notifications"
              description="Enable email by default for new patrons"
              checked={config.patron_default_email_notifications}
              onChange={(v) => setField('patron_default_email_notifications', v)}
            />
            <ToggleRow
              label="SMS Notifications"
              description="Enable SMS by default for new patrons"
              checked={config.patron_default_sms_notifications}
              onChange={(v) => setField('patron_default_sms_notifications', v)}
            />
          </SettingsCard>

          <SettingsCard
            title="Notification Templates"
            icon={Eye}
            description="Preview of notification templates (read-only)"
          >
            <div className="space-y-3">
              {NOTIFICATION_TEMPLATES.map((template) => {
                const isOpen = selectedTemplateId === template.id
                return (
                  <div
                    key={template.id}
                    className="border border-lsc-border dark:border-earth-700 rounded-lg dark:bg-earth-900"
                  >
                    <button
                      type="button"
                      onClick={() => setSelectedTemplateId(isOpen ? null : template.id)}
                      aria-expanded={isOpen}
                      aria-controls={`template-panel-${template.id}`}
                      className="w-full text-left p-4 hover:bg-earth-50 dark:hover:bg-earth-700/50 transition-colors rounded-lg"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                          <p className="font-medium text-lsc-dark dark:text-lsc-cream">{template.name}</p>
                          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                            Subject: {template.subject}
                          </p>
                        </div>
                        <span className="text-lsc-dark/70 dark:text-lsc-cream/70" aria-hidden="true">
                          {isOpen ? '\u25BC' : '\u25B6'}
                        </span>
                      </div>
                    </button>
                    {isOpen && (
                      <div id={`template-panel-${template.id}`} role="region" className="px-4 pb-4 border-t border-lsc-border dark:border-earth-700 space-y-3">
                        <div className="pt-4">
                          <p className="text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 uppercase mb-1">
                            Preview
                          </p>
                          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 italic p-2 bg-earth-50 dark:bg-earth-700/50 rounded">
                            {template.preview}
                          </p>
                        </div>
                        <div>
                          <p className="text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 uppercase mb-2">
                            Available Variables
                          </p>
                          <div className="flex flex-wrap gap-2">
                            {template.variables.map((variable) => (
                              <span
                                key={variable}
                                className="px-2 py-1 text-xs bg-earth-100 dark:bg-earth-800 text-earth-800 dark:text-lsc-rose-light/80 rounded font-mono"
                              >
                                {'{' + variable + '}'}
                              </span>
                            ))}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          </SettingsCard>

          <SettingsCard
            title="Send Test Email"
            icon={Send}
            description="Send a sample notification email to verify configuration"
          >
            <div className="flex gap-3">
              <div className="flex-1">
                <TextField
                  label=""
                  type="email"
                  value={testEmail}
                  onChange={setTestEmail}
                  placeholder={t('placeholder.adminEmailNotificationConfig.adminlibraryorg')}
                />
              </div>
              <button
                type="button"
                onClick={handleTestEmail}
                disabled={testingEmail || !config.notifications_enabled}
                className="self-end px-4 py-2 bg-teal-600 hover:bg-teal-700 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg transition-colors flex items-center gap-2 font-medium"
              >
                {testingEmail ? (
                  <>
                    <RefreshCw className="w-4 h-4 motion-safe:animate-spin" aria-hidden="true" />
                    Sending...
                  </>
                ) : (
                  <>
                    <Send className="w-4 h-4" aria-hidden="true" />
                    Send Test Email
                  </>
                )}
              </button>
            </div>
          </SettingsCard>

          <AuditTrailAccordion entries={auditEntries} />

          <SettingsCard title="Reason for Changes (optional)">
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder={t('admin.adminEmailNotificationConfig.describeWhyYouReMaking')}
              rows={3}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
            />
            <StatGrid columns={4}>
              <StatCard
                title="Notifications"
                value={config.notifications_enabled ? 'ON' : 'OFF'}
                icon={config.notifications_enabled ? CheckCircle2 : XCircle}
                color={config.notifications_enabled ? 'green' : 'red'}
              />
              <StatCard title="Types Enabled" value={typesEnabled} icon={Bell} color="accent" />
              <StatCard
                title="Email Default"
                value={config.patron_default_email_notifications ? 'ON' : 'OFF'}
                icon={Mail}
                color={config.patron_default_email_notifications ? 'green' : 'earth'}
              />
              <StatCard
                title="SMS Default"
                value={config.patron_default_sms_notifications ? 'ON' : 'OFF'}
                icon={Bell}
                color={config.patron_default_sms_notifications ? 'green' : 'earth'}
              />
            </StatGrid>
          </SettingsCard>

          <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm p-6 border border-lsc-border dark:border-earth-700">
            <button
              type="button"
              onClick={() => void handleSave()}
              disabled={saving}
              className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-lg font-medium transition-colors bg-lsc-rose hover:bg-lsc-rose/90 text-white disabled:opacity-50"
            >
              {saving ? (
                <RefreshCw className="w-5 h-5 motion-safe:animate-spin" aria-hidden="true" />
              ) : (
                <Save className="w-5 h-5" aria-hidden="true" />
              )}
              {saving ? 'Saving...' : 'Save Notification Settings'}
            </button>
          </div>
        </div>
      )}
    </SectionShell>
  )
}

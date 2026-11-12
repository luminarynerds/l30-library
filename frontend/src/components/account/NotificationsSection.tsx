/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Notifications Tab
 * Displays and manages notification preferences
 */
import React, { useState } from 'react'
import {
  Loader2,
  Bell,
  Smartphone,
  CheckCircle,
  AlertCircle,
} from 'lucide-react'
import { NotificationPreferences } from '../../api/api'
import { useTranslation } from '@/i18n'

interface NotificationsSectionProps {
  preferences: NotificationPreferences | null
  loading: boolean
  saving: boolean
  onUpdate: (field: string, value: boolean | number) => void
}

export const NotificationsSection: React.FC<NotificationsSectionProps> = ({
  preferences,
  loading,
  saving,
  onUpdate,
}) => {
  const { t } = useTranslation()
  const [pendingChanges, setPendingChanges] = useState<Record<string, boolean | number>>({})
  const isDirty = Object.keys(pendingChanges).length > 0

  const getValue = (field: string, originalValue: boolean | number) => {
    return field in pendingChanges ? pendingChanges[field] : originalValue
  }

  const handleChange = (field: string, value: boolean | number) => {
    setPendingChanges(prev => ({ ...prev, [field]: value }))
  }

  const handleSave = async () => {
    for (const [field, value] of Object.entries(pendingChanges)) {
      await onUpdate(field, value)
    }
    setPendingChanges({})
  }

  const handleDiscard = () => {
    setPendingChanges({})
  }

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-dark/70 dark:text-lsc-cream/70" />
      </div>
    )
  }

  if (!preferences) {
    return (
      <div className="text-center py-12">
        <Bell className="w-12 h-12 text-sage/30 mx-auto mb-3" />
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('components.account.notificationsSection.unableToLoadNotificationPreferences')}</p>
      </div>
    )
  }

  return (
    <div>
      <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-6">
        {t('account.notificationPreferences', 'Notification Preferences')}
      </h2>
      <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
        {t('account.notificationPreferencesDesc', 'Manage how you receive updates from the library.')}
      </p>

      {/* Link to advanced notification preferences */}
      <a
        href="/notifications/preferences"
        className="inline-flex items-center gap-2 px-4 py-2 mb-6 bg-lsc-rose/10 hover:bg-lsc-rose/20 text-lsc-rose rounded-xl text-sm font-medium transition-colors"
      >
        <Bell className="w-4 h-4" />
        {t('components.account.notificationsSection.advancedPreferencesLink', 'Advanced Preferences (Digest & Quiet Hours)')}
      </a>

      <div className="space-y-4">
        {/* Email Notifications Section */}
        <div className="p-6 bg-cream dark:bg-earth-800 rounded-xl">
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4">
            {t('account.emailNotifications', 'Email Notifications')}
          </h3>
          <div className="space-y-4">
            {/* Checkout Receipt */}
            <label className="flex items-center space-x-3 cursor-pointer">
              <input
                type="checkbox"
                checked={getValue('email_checkout_receipt', preferences.email_checkout_receipt) as boolean}
                onChange={(e) => handleChange('email_checkout_receipt', e.target.checked)}
                disabled={saving}
                className="w-5 h-5 text-lsc-rose border-sage/30 rounded focus:ring-lsc-rose dark:focus:ring-status-warning-400"
              />
              <div className="flex-1">
                <div className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                  {t('account.checkoutReceipt', 'Checkout Receipt')}
                </div>
                <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                  {t('account.checkoutReceiptDesc', 'Receive an email confirmation when you check out items')}
                </div>
              </div>
            </label>

            {/* Due Date Reminder */}
            <label className="flex items-center space-x-3 cursor-pointer">
              <input
                type="checkbox"
                checked={getValue('email_due_date_reminder', preferences.email_due_date_reminder) as boolean}
                onChange={(e) => handleChange('email_due_date_reminder', e.target.checked)}
                disabled={saving}
                className="w-5 h-5 text-lsc-rose border-sage/30 rounded focus:ring-lsc-rose dark:focus:ring-status-warning-400"
              />
              <div className="flex-1">
                <div className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                  {t('account.dueDateReminder', 'Due Date Reminder')}
                </div>
                <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                  {t('account.dueDateReminderDesc', 'Get reminded before your items are due')}
                </div>
              </div>
            </label>

            {/* Overdue Notice */}
            <label className="flex items-center space-x-3 cursor-pointer">
              <input
                type="checkbox"
                checked={getValue('email_overdue_notice', preferences.email_overdue_notice) as boolean}
                onChange={(e) => handleChange('email_overdue_notice', e.target.checked)}
                disabled={saving}
                className="w-5 h-5 text-lsc-rose border-sage/30 rounded focus:ring-lsc-rose dark:focus:ring-status-warning-400"
              />
              <div className="flex-1">
                <div className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                  {t('account.overdueNotice', 'Overdue Notice')}
                </div>
                <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                  {t('account.overdueNoticeDesc', 'Receive notifications when items become overdue')}
                </div>
              </div>
            </label>

            {/* Hold Ready */}
            <label className="flex items-center space-x-3 cursor-pointer">
              <input
                type="checkbox"
                checked={getValue('email_hold_ready', preferences.email_hold_ready) as boolean}
                onChange={(e) => handleChange('email_hold_ready', e.target.checked)}
                disabled={saving}
                className="w-5 h-5 text-lsc-rose border-sage/30 rounded focus:ring-lsc-rose dark:focus:ring-status-warning-400"
              />
              <div className="flex-1">
                <div className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                  {t('account.holdReadyForPickup', 'Hold Ready for Pickup')}
                </div>
                <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                  {t('account.holdReadyForPickupDesc', 'Get notified when your holds are ready to pick up')}
                </div>
              </div>
            </label>

            {/* Hold Expiring */}
            <label className="flex items-center space-x-3 cursor-pointer">
              <input
                type="checkbox"
                checked={getValue('email_hold_expiring', preferences.email_hold_expiring) as boolean}
                onChange={(e) => handleChange('email_hold_expiring', e.target.checked)}
                disabled={saving}
                className="w-5 h-5 text-lsc-rose border-sage/30 rounded focus:ring-lsc-rose dark:focus:ring-status-warning-400"
              />
              <div className="flex-1">
                <div className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                  {t('account.holdExpiringSoon', 'Hold Expiring Soon')}
                </div>
                <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                  {t('account.holdExpiringSoonDesc', 'Receive reminders before your holds expire')}
                </div>
              </div>
            </label>

            {/* Hold Cancelled */}
            <label className="flex items-center space-x-3 cursor-pointer">
              <input
                type="checkbox"
                checked={getValue('email_hold_cancelled', preferences.email_hold_cancelled) as boolean}
                onChange={(e) => handleChange('email_hold_cancelled', e.target.checked)}
                disabled={saving}
                className="w-5 h-5 text-lsc-rose border-sage/30 rounded focus:ring-lsc-rose dark:focus:ring-status-warning-400"
              />
              <div className="flex-1">
                <div className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                  {t('account.holdCancelled', 'Hold Cancelled')}
                </div>
                <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                  {t('account.holdCancelledDesc', 'Be notified if your hold is cancelled')}
                </div>
              </div>
            </label>

            {/* Fine Notice */}
            <label className="flex items-center space-x-3 cursor-pointer">
              <input
                type="checkbox"
                checked={getValue('email_fine_notice', preferences.email_fine_notice) as boolean}
                onChange={(e) => handleChange('email_fine_notice', e.target.checked)}
                disabled={saving}
                className="w-5 h-5 text-lsc-rose border-sage/30 rounded focus:ring-lsc-rose dark:focus:ring-status-warning-400"
              />
              <div className="flex-1">
                <div className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                  {t('account.fineNotice', 'Fine Notice')}
                </div>
                <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                  {t('account.fineNoticeDesc', 'Receive notifications about fines on your account')}
                </div>
              </div>
            </label>
          </div>
        </div>

        {/* Reminder Timing Section */}
        <div className="p-6 bg-cream dark:bg-earth-800 rounded-xl">
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4">
            {t('account.reminderTiming', 'Reminder Timing')}
          </h3>
          <div className="space-y-4">
            {/* Due Date Reminder Days */}
            <div>
              <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
                {t('account.dueDateReminderDays', 'Due Date Reminder (days before due date)')}
              </label>
              <input
                type="number"
                min="0"
                max="14"
                value={getValue('due_date_reminder_days', preferences.due_date_reminder_days) as number}
                onChange={(e) => handleChange('due_date_reminder_days', parseInt(e.target.value) || 0)}
                disabled={saving}
                className="w-full px-4 py-2 border border-sage/30 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose dark:focus:ring-status-warning-400 focus:border-transparent"
              />
              <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                {t('account.dueDateReminderDaysHelp', 'How many days before the due date should we remind you?')}
              </p>
            </div>

            {/* Hold Expiring Reminder Days */}
            <div>
              <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
                {t('account.holdExpiringReminderDays', 'Hold Expiring Reminder (days before expiration)')}
              </label>
              <input
                type="number"
                min="0"
                max="7"
                value={getValue('hold_expiring_reminder_days', preferences.hold_expiring_reminder_days) as number}
                onChange={(e) => handleChange('hold_expiring_reminder_days', parseInt(e.target.value) || 0)}
                disabled={saving}
                className="w-full px-4 py-2 border border-sage/30 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose dark:focus:ring-status-warning-400 focus:border-transparent"
              />
              <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                {t('account.holdExpiringReminderDaysHelp', 'How many days before a hold expires should we remind you to pick it up?')}
              </p>
            </div>
          </div>
        </div>

        {/* SMS Notifications Section */}
        <div className="p-6 bg-cream dark:bg-earth-800 rounded-xl">
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
            <Smartphone className="w-5 h-5" />
            {t('components.account.notificationsSection.smsNotificationsTitle', 'SMS Notifications')}
          </h3>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
            {t('components.account.notificationsSection.smsNotificationsDesc', 'Receive text message notifications for important library alerts.')}
          </p>

          {/* Enable SMS Toggle */}
          <label className="flex items-center space-x-3 cursor-pointer mb-4 pb-4 border-b border-sage/20 dark:border-earth-700">
            <input
              type="checkbox"
              checked={getValue('sms_notifications_enabled', preferences.sms_notifications_enabled || false) as boolean}
              onChange={(e) => handleChange('sms_notifications_enabled', e.target.checked)}
              disabled={saving}
              className="w-5 h-5 text-lsc-rose border-sage/30 rounded focus:ring-lsc-rose"
            />
            <div className="flex-1">
              <div className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                {t('components.account.notificationsSection.enableSmsLabel', 'Enable SMS Notifications')}
              </div>
              <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                {t('components.account.notificationsSection.smsRatesNotice', 'Standard messaging rates may apply')}
              </div>
            </div>
          </label>

          {(getValue('sms_notifications_enabled', preferences.sms_notifications_enabled || false) as boolean) && (
            <div className="space-y-4">
              {/* Phone Number Status */}
              <div className="flex items-center gap-2 p-3 rounded-lg bg-lsc-white dark:bg-lsc-brown">
                {preferences.sms_phone_verified ? (
                  <>
                    <CheckCircle className="w-5 h-5 text-status-success-600" />
                    <span className="text-sm text-status-success-700 dark:text-status-success-400">
                      {preferences.sms_phone_number
                        ? t('components.account.notificationsSection.smsEnabledForPhone', { phone: preferences.sms_phone_number })
                        : t('components.account.notificationsSection.smsEnabledForYourPhone', 'SMS enabled for your phone')}
                    </span>
                  </>
                ) : (
                  <>
                    <AlertCircle className="w-5 h-5 text-status-warning-600" />
                    <span className="text-sm text-status-warning-700 dark:text-status-warning-400">
                      {t('components.account.notificationsSection.phoneNotVerified', 'Phone number not verified - contact library staff to enable SMS')}
                    </span>
                  </>
                )}
              </div>

              {/* SMS Notification Types */}
              {preferences.sms_phone_verified && (
                <div className="space-y-3 pt-2">
                  <label className="flex items-center space-x-3 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={getValue('sms_due_date_reminder', preferences.sms_due_date_reminder || false) as boolean}
                      onChange={(e) => handleChange('sms_due_date_reminder', e.target.checked)}
                      disabled={saving}
                      className="w-5 h-5 text-lsc-rose border-sage/30 rounded focus:ring-lsc-rose"
                    />
                    <div className="flex-1">
                      <div className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                        {t('components.account.notificationsSection.smsDueDateReminderLabel', 'Due Date Reminders')}
                      </div>
                    </div>
                  </label>

                  <label className="flex items-center space-x-3 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={getValue('sms_overdue_notice', preferences.sms_overdue_notice || false) as boolean}
                      onChange={(e) => handleChange('sms_overdue_notice', e.target.checked)}
                      disabled={saving}
                      className="w-5 h-5 text-lsc-rose border-sage/30 rounded focus:ring-lsc-rose"
                    />
                    <div className="flex-1">
                      <div className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                        {t('components.account.notificationsSection.smsOverdueNoticeLabel', 'Overdue Notices')}
                      </div>
                    </div>
                  </label>

                  <label className="flex items-center space-x-3 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={getValue('sms_hold_ready', preferences.sms_hold_ready || false) as boolean}
                      onChange={(e) => handleChange('sms_hold_ready', e.target.checked)}
                      disabled={saving}
                      className="w-5 h-5 text-lsc-rose border-sage/30 rounded focus:ring-lsc-rose"
                    />
                    <div className="flex-1">
                      <div className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                        {t('account.holdReadyForPickup', 'Hold Ready for Pickup')}
                      </div>
                    </div>
                  </label>

                  <label className="flex items-center space-x-3 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={getValue('sms_event_reminder', preferences.sms_event_reminder || false) as boolean}
                      onChange={(e) => handleChange('sms_event_reminder', e.target.checked)}
                      disabled={saving}
                      className="w-5 h-5 text-lsc-rose border-sage/30 rounded focus:ring-lsc-rose"
                    />
                    <div className="flex-1">
                      <div className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                        {t('components.account.notificationsSection.smsEventReminderLabel', 'Event Reminders')}
                      </div>
                    </div>
                  </label>
                </div>
              )}
            </div>
          )}
        </div>

        {/* SaveBar - shown when there are unsaved changes */}
        {isDirty && (
          <div className="sticky bottom-0 left-0 right-0 p-4 bg-lsc-white dark:bg-earth-900 border-t border-sage/20 dark:border-earth-700 flex items-center justify-between rounded-b-xl shadow-lg z-10">
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
              {t('components.account.notificationsSection.unsavedChangesNotice', 'You have unsaved changes')}
            </p>
            <div className="flex items-center gap-3">
              <button
                onClick={handleDiscard}
                className="px-4 py-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream transition-colors"
              >
                {t('components.account.notificationsSection.discardButton', 'Discard')}
              </button>
              <button
                onClick={handleSave}
                disabled={saving}
                className="px-4 py-2 bg-lsc-rose text-white rounded-xl text-sm font-medium hover:bg-lsc-rose/90 transition-colors disabled:opacity-50 flex items-center gap-2"
              >
                {saving ? <Loader2 className="w-4 h-4 motion-safe:animate-spin" /> : null}
                {t('components.account.notificationsSection.saveChangesButton', 'Save Changes')}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

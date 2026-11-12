/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { X } from 'lucide-react'
import { useTranslation } from '@/i18n'
import type { OutreachNotificationTemplate, NotificationType, NotificationChannel } from '../../../api/staff-outreach-api'
import type { TemplateFormState } from './outreach-types'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

interface Props {
  selectedTemplate: OutreachNotificationTemplate | null
  templateForm: TemplateFormState
  setTemplateForm: (f: TemplateFormState) => void
  isPending: boolean
  onSave: () => void
  onClose: () => void
}

export function TemplateModal({ selectedTemplate, templateForm, setTemplateForm, isPending, onSave, onClose }: Props) {
  const { t } = useTranslation()
  return (
    <ModalBackdrop onClose={onClose} title="Edit Template">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-lg w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream">
              {selectedTemplate ? "Edit Template" : "New Template"}
            </h2>
            <button onClick={onClose} className="text-lsc-dark/70 hover:text-lsc-dark dark:text-lsc-cream/70 dark:hover:text-lsc-cream">
              <X className="w-5 h-5" />
            </button>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Name</label>
              <input
                type="text"
                value={templateForm.name}
                onChange={(e) => setTemplateForm({ ...templateForm, name: e.target.value })}
                className="w-full px-3 py-2 bg-lsc-white dark:bg-earth-700 border border-lsc-border dark:border-earth-700 rounded-lg text-lsc-dark dark:text-lsc-cream"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Type</label>
                <select
                  value={templateForm.notification_type}
                  onChange={(e) => setTemplateForm({ ...templateForm, notification_type: e.target.value as NotificationType })}
                  className="w-full px-3 py-2 bg-lsc-white dark:bg-earth-700 border border-lsc-border dark:border-earth-700 rounded-lg text-lsc-dark dark:text-lsc-cream"
                >
                  <option value="visit_reminder">Visit Reminder</option>
                  <option value="due_date_reminder">Due Date Reminder</option>
                  <option value="overdue_notice">Overdue Notice</option>
                  <option value="deposit_expiring">Deposit Expiring</option>
                  <option value="card_expiring">Card Expiring</option>
                  <option value="welcome">Welcome</option>
                  <option value="thank_you">Thank You</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Channel</label>
                <select
                  value={templateForm.channel}
                  onChange={(e) => setTemplateForm({ ...templateForm, channel: e.target.value as NotificationChannel })}
                  className="w-full px-3 py-2 bg-lsc-white dark:bg-earth-700 border border-lsc-border dark:border-earth-700 rounded-lg text-lsc-dark dark:text-lsc-cream"
                >
                  <option value="email">Email</option>
                  <option value="sms">SMS</option>
                  <option value="in_app">In-App</option>
                </select>
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Subject (for email)</label>
              <input
                type="text"
                value={templateForm.subject}
                onChange={(e) => setTemplateForm({ ...templateForm, subject: e.target.value })}
                className="w-full px-3 py-2 bg-lsc-white dark:bg-earth-700 border border-lsc-border dark:border-earth-700 rounded-lg text-lsc-dark dark:text-lsc-cream"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Body</label>
              <textarea
                value={templateForm.body}
                onChange={(e) => setTemplateForm({ ...templateForm, body: e.target.value })}
                rows={5}
                className="w-full px-3 py-2 bg-lsc-white dark:bg-earth-700 border border-lsc-border dark:border-earth-700 rounded-lg text-lsc-dark dark:text-lsc-cream"
                placeholder={t('staffOutreach.useVariableNameForDynamic')}
              />
            </div>
            <div className="flex items-center gap-4">
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={templateForm.is_active}
                  onChange={(e) => setTemplateForm({ ...templateForm, is_active: e.target.checked })}
                  className="rounded"
                />
                <span className="text-sm text-lsc-dark dark:text-lsc-cream">Active</span>
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={templateForm.is_default}
                  onChange={(e) => setTemplateForm({ ...templateForm, is_default: e.target.checked })}
                  className="rounded"
                />
                <span className="text-sm text-lsc-dark dark:text-lsc-cream">Default</span>
              </label>
            </div>
          </div>

          <div className="flex justify-end gap-3 mt-6">
            <button onClick={onClose} className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70">
              Cancel
            </button>
            <button
              onClick={onSave}
              disabled={isPending}
              className="px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg"
            >
              Save
            </button>
          </div>
        </div>
      </div>
    </ModalBackdrop>
  )
}

/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Plus, Mail, Loader2 } from 'lucide-react'
import type {
  OutreachNotificationTemplate,
  listNotificationTemplates,
  getNotificationStats,
} from '../../../api/staff-outreach-api'

type TemplatesData = Awaited<ReturnType<typeof listNotificationTemplates>>
type NotificationStatsData = Awaited<ReturnType<typeof getNotificationStats>>

interface Props {
  templatesData: TemplatesData | undefined
  templatesLoading: boolean
  notificationStats: NotificationStatsData | undefined
  onNew: () => void
  onEdit: (template: OutreachNotificationTemplate) => void
  onDelete: (id: number) => void
  onSetDefault: (id: number) => void
}

export function TemplatesTab({
  templatesData, templatesLoading, notificationStats,
  onNew, onEdit, onDelete, onSetDefault,
}: Props) {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4">
        <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">Notification Templates</h3>
        <button
          onClick={onNew}
          className="flex items-center gap-2 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg text-sm"
        >
          <Plus className="w-4 h-4" /> New Template
        </button>
      </div>

      {notificationStats && (
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700 text-center">
            <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">{notificationStats.total_notifications}</p>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Total Sent</p>
          </div>
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700 text-center">
            <p className="text-2xl font-bold text-status-success-600">{notificationStats.delivery_rate.toFixed(1)}%</p>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Delivery Rate</p>
          </div>
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700 text-center">
            <p className="text-2xl font-bold text-status-danger-600">{notificationStats.failure_rate.toFixed(1)}%</p>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Failure Rate</p>
          </div>
        </div>
      )}

      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 overflow-hidden">
        {templatesLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-6 h-6 motion-safe:animate-spin text-lsc-rose" />
          </div>
        ) : templatesData?.templates && templatesData.templates.length > 0 ? (
          <div className="divide-y divide-lsc-border dark:divide-earth-700">
            {templatesData.templates.map((template) => (
              <div key={template.id} className="p-4 hover:bg-lsc-cream/50 dark:hover:bg-earth-700/50 transition-colors">
                <div className="flex items-start justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <p className="font-medium text-lsc-dark dark:text-lsc-cream">{template.name}</p>
                      {template.is_default && (
                        <span className="px-2 py-0.5 text-xs bg-lsc-rose text-white rounded-full">Default</span>
                      )}
                      {!template.is_active && (
                        <span className="px-2 py-0.5 text-xs bg-earth-400 text-white rounded-full">Inactive</span>
                      )}
                    </div>
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                      {template.notification_type.replace("_", " ")} via {template.channel}
                    </p>
                    {template.subject && (
                      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                        Subject: {template.subject}
                      </p>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    {!template.is_default && (
                      <button
                        onClick={() => onSetDefault(template.id)}
                        className="px-2 py-1 text-xs bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded"
                      >
                        Set Default
                      </button>
                    )}
                    <button
                      onClick={() => onEdit(template)}
                      className="px-2 py-1 text-xs bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => onDelete(template.id)}
                      className="px-2 py-1 text-xs bg-status-danger-600 hover:bg-status-danger-700 text-white rounded"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-lsc-dark/70 dark:text-lsc-cream/70">
            <Mail className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p>No notification templates</p>
          </div>
        )}
      </div>
    </div>
  )
}

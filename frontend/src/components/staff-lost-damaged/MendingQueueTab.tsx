/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import {
  Loader2, Clock, Play, AlertCircle, CheckCircle, Wrench,
} from "lucide-react"
import type { MendingQueueEntry } from "../../api/staff-api"
import { useTranslation } from '@/i18n'

interface MendingQueueTabProps {
  mendingData: { items: MendingQueueEntry[]; total: number } | undefined
  mendingLoading: boolean
  completeRepairMutation: {
    mutate: (data: { mending_entry_id: number; new_condition: string; completion_notes?: string }) => void
    isPending: boolean
  }
}

export function MendingQueueTab({
  mendingData,
  mendingLoading,
  completeRepairMutation,
}: MendingQueueTabProps): React.ReactElement {
  const { t } = useTranslation()
  return (
    <div className="space-y-4">
      {/* Summary Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700">
          <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
            <Clock className="w-4 h-4" />
            <span className="text-sm">Pending</span>
          </div>
          <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
            {mendingData?.items.filter(i => !i.is_in_progress && !i.is_completed).length || 0}
          </p>
        </div>
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700">
          <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
            <Play className="w-4 h-4" />
            <span className="text-sm">In Progress</span>
          </div>
          <p className="text-2xl font-bold text-lsc-rose dark:text-lsc-rose-light">
            {mendingData?.items.filter(i => i.is_in_progress).length || 0}
          </p>
        </div>
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700">
          <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
            <AlertCircle className="w-4 h-4" />
            <span className="text-sm">High Priority</span>
          </div>
          <p className="text-2xl font-bold text-status-warning-600 dark:text-status-warning-400">
            {mendingData?.items.filter(i => i.priority >= 4 && !i.is_completed).length || 0}
          </p>
        </div>
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700">
          <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
            <CheckCircle className="w-4 h-4" />
            <span className="text-sm">Total</span>
          </div>
          <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
            {mendingData?.total || 0}
          </p>
        </div>
      </div>

      {/* Mending Queue Table */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 overflow-hidden">
        {mendingLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-6 h-6 motion-safe:animate-spin text-lsc-rose" />
          </div>
        ) : mendingData?.items && mendingData.items.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-lsc-cream/50 dark:bg-earth-700/50">
                <tr className="text-left text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                  <th className="px-4 py-3 font-medium">Position</th>
                  <th className="px-4 py-3 font-medium">Item</th>
                  <th className="px-4 py-3 font-medium">Priority</th>
                  <th className="px-4 py-3 font-medium">Repair Type</th>
                  <th className="px-4 py-3 font-medium">Assigned To</th>
                  <th className="px-4 py-3 font-medium">Est. Time</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-lsc-border dark:divide-earth-700">
                {mendingData.items.map((entry) => (
                  <tr key={entry.id} className="hover:bg-lsc-cream/30 dark:hover:bg-earth-700/30 transition-colors">
                    <td className="px-4 py-3 font-mono text-sm text-lsc-dark dark:text-lsc-cream">
                      #{entry.queue_position}
                    </td>
                    <td className="px-4 py-3">
                      <div className="font-medium text-lsc-dark dark:text-lsc-cream truncate max-w-xs" title={entry.item_title || `Item #${entry.item_copy_id}`}>
                        {entry.item_title || `Item #${entry.item_copy_id}`}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${
                        entry.priority >= 4 ? "bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900/30 dark:text-status-danger-400" :
                        entry.priority >= 3 ? "bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-400" :
                        "bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-400"
                      }`}>
                        P{entry.priority}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-lsc-dark/80 dark:text-lsc-cream/80">
                      {entry.repair_type || "-"}
                    </td>
                    <td className="px-4 py-3 text-sm text-lsc-dark/80 dark:text-lsc-cream/80">
                      {entry.assigned_to_name || "Unassigned"}
                    </td>
                    <td className="px-4 py-3 text-sm text-lsc-dark/80 dark:text-lsc-cream/80">
                      {entry.estimated_time_hours ? `${entry.estimated_time_hours}h` : "-"}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${
                        entry.is_completed ? "bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-400" :
                        entry.is_in_progress ? "bg-earth-100 text-earth-800 dark:bg-earth-800/30 dark:text-lsc-rose-light" :
                        "bg-earth-100 text-earth-800 dark:bg-earth-900/30 dark:text-earth-300"
                      }`}>
                        {entry.is_completed ? "Completed" : entry.is_in_progress ? "In Progress" : "Pending"}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        {!entry.is_completed && (
                          <button
                            onClick={() => completeRepairMutation.mutate({
                              mending_entry_id: entry.id,
                              new_condition: "good",
                            })}
                            disabled={completeRepairMutation.isPending}
                            className="p-1.5 text-status-success-600 hover:bg-status-success-100 dark:bg-status-success-900/30 dark:hover:bg-status-success-900/30 rounded-lg transition-colors"
                            title="Mark Complete"
                          >
                            <CheckCircle className="w-4 h-4" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-12 text-lsc-dark/70 dark:text-lsc-cream/70">
            <Wrench className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p>{t('components.staffLostDamaged.mendingQueueTab.noItemsInMendingQueue')}</p>
          </div>
        )}
      </div>
    </div>
  )
}

/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import {
  Filter, Loader2, AlertTriangle, Wrench,
} from "lucide-react"
import type { DamagedItemRecord } from "../../api/staff-api"
import { getDamagedStatusColor, getSeverityColor } from "../../utils/status-colors"
import { formatStatus, formatDate, formatCurrency } from "../../utils/format-utils"
import { useTranslation } from '@/i18n'

interface DamagedItemsTabProps {
  damagedItemsData: { items: DamagedItemRecord[]; total: number } | undefined
  damagedLoading: boolean
  damagedStatusFilter: string
  setDamagedStatusFilter: (v: string) => void
  setSelectedDamagedItem: (item: DamagedItemRecord) => void
  setShowMendingModal: (v: boolean) => void
}

export function DamagedItemsTab({
  damagedItemsData,
  damagedLoading,
  damagedStatusFilter,
  setDamagedStatusFilter,
  setSelectedDamagedItem,
  setShowMendingModal,
}: DamagedItemsTabProps): React.ReactElement {
  const { t } = useTranslation()
  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex flex-wrap gap-4 items-center bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700">
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" />
          <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">Filters:</span>
        </div>
        <select
          value={damagedStatusFilter}
          onChange={(e) => setDamagedStatusFilter(e.target.value)}
          className="px-3 py-1.5 text-sm border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
        >
          <option value="">All Statuses</option>
          <option value="reported">Reported</option>
          <option value="assessing">Assessing</option>
          <option value="in_mending">In Mending</option>
          <option value="repaired">Repaired</option>
          <option value="withdrawn">Withdrawn</option>
        </select>
      </div>

      {/* Damaged Items Table */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 overflow-hidden">
        {damagedLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-6 h-6 motion-safe:animate-spin text-lsc-rose" />
          </div>
        ) : damagedItemsData?.items && damagedItemsData.items.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-lsc-cream/50 dark:bg-earth-700/50">
                <tr className="text-left text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                  <th className="px-4 py-3 font-medium">Item</th>
                  <th className="px-4 py-3 font-medium">Patron</th>
                  <th className="px-4 py-3 font-medium">Severity</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 font-medium">Damage Types</th>
                  <th className="px-4 py-3 font-medium">Est. Repair</th>
                  <th className="px-4 py-3 font-medium">Reported</th>
                  <th className="px-4 py-3 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-lsc-border dark:divide-earth-700">
                {damagedItemsData.items.map((item) => (
                  <tr key={item.id} className="hover:bg-lsc-cream/30 dark:hover:bg-earth-700/30 transition-colors">
                    <td className="px-4 py-3">
                      <div className="font-medium text-lsc-dark dark:text-lsc-cream truncate max-w-xs" title={item.item_title || `Item #${item.item_copy_id}`}>
                        {item.item_title || `Item #${item.item_copy_id}`}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-sm text-lsc-dark/80 dark:text-lsc-cream/80">
                      {item.patron_name || "-"}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${getSeverityColor(item.severity)}`}>
                        {formatStatus(item.severity)}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${getDamagedStatusColor(item.status)}`}>
                        {formatStatus(item.status)}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-lsc-dark/80 dark:text-lsc-cream/80">
                      {item.damage_types?.join(", ") || "-"}
                    </td>
                    <td className="px-4 py-3 text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                      {formatCurrency(item.estimated_repair_cost)}
                    </td>
                    <td className="px-4 py-3 text-sm text-lsc-dark/80 dark:text-lsc-cream/80">
                      {formatDate(item.reported_at)}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        {(item.status === "reported" || item.status === "assessing") && (
                          <button
                            onClick={() => { setSelectedDamagedItem(item); setShowMendingModal(true) }}
                            className="p-1.5 text-category-600 hover:bg-category-100 dark:bg-category-900/30 dark:hover:bg-category-900/30 rounded-lg transition-colors"
                            title="Send to Mending"
                          >
                            <Wrench className="w-4 h-4" />
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
            <AlertTriangle className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p>{t('components.staffLostDamaged.damagedItemsTab.noDamagedItemsFound')}</p>
          </div>
        )}
      </div>
      {damagedItemsData && (
        <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
          Showing {damagedItemsData.items.length} of {damagedItemsData.total} items
        </div>
      )}
    </div>
  )
}

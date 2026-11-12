/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import {
  Filter, Loader2, Clock, CheckCircle, Archive, FileX,
} from "lucide-react"
import type { LostItemRecord } from "../../api/staff-api"
import { getLostStatusColor, getLostTypeLabel } from "../../utils/status-colors"
import { formatStatus, formatDate, formatCurrency } from "../../utils/format-utils"
import { useTranslation } from '@/i18n'

interface LostItemsTabProps {
  lostItemsData: { items: LostItemRecord[]; total: number } | undefined
  lostLoading: boolean
  lostStatusFilter: string
  setLostStatusFilter: (v: string) => void
  lostTypeFilter: string
  setLostTypeFilter: (v: string) => void
  setShowAutoConvertModal: (v: boolean) => void
  setSelectedLostItem: (item: LostItemRecord) => void
  setShowFoundModal: (v: boolean) => void
  setShowWriteOffModal: (v: boolean) => void
}

export function LostItemsTab({
  lostItemsData,
  lostLoading,
  lostStatusFilter,
  setLostStatusFilter,
  lostTypeFilter,
  setLostTypeFilter,
  setShowAutoConvertModal,
  setSelectedLostItem,
  setShowFoundModal,
  setShowWriteOffModal,
}: LostItemsTabProps): React.ReactElement {
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
          value={lostStatusFilter}
          onChange={(e) => setLostStatusFilter(e.target.value)}
          className="px-3 py-1.5 text-sm border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
        >
          <option value="">All Statuses</option>
          <option value="reported">Reported</option>
          <option value="confirmed">Confirmed</option>
          <option value="charged">Charged</option>
          <option value="found">Found</option>
          <option value="written_off">Written Off</option>
        </select>
        <select
          value={lostTypeFilter}
          onChange={(e) => setLostTypeFilter(e.target.value)}
          className="px-3 py-1.5 text-sm border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
        >
          <option value="">All Types</option>
          <option value="lost_by_patron">Lost by Patron</option>
          <option value="lost_in_transit">Lost in Transit</option>
          <option value="missing_inventory">Missing (Inventory)</option>
          <option value="claims_returned">Claims Returned</option>
        </select>
        <button
          onClick={() => setShowAutoConvertModal(true)}
          className="ml-auto flex items-center gap-2 px-3 py-1.5 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg text-sm"
        >
          <Clock className="w-4 h-4" /> Auto-Convert Overdue
        </button>
      </div>

      {/* Lost Items Table */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 overflow-hidden">
        {lostLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-6 h-6 motion-safe:animate-spin text-lsc-rose" />
          </div>
        ) : lostItemsData?.items && lostItemsData.items.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-lsc-cream/50 dark:bg-earth-700/50">
                <tr className="text-left text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                  <th className="px-4 py-3 font-medium">Item</th>
                  <th className="px-4 py-3 font-medium">Patron</th>
                  <th className="px-4 py-3 font-medium">Type</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 font-medium">Replacement Cost</th>
                  <th className="px-4 py-3 font-medium">Reported</th>
                  <th className="px-4 py-3 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-lsc-border dark:divide-earth-700">
                {lostItemsData.items.map((item) => (
                  <tr key={item.id} className="hover:bg-lsc-cream/30 dark:hover:bg-earth-700/30 transition-colors">
                    <td className="px-4 py-3">
                      <div className="font-medium text-lsc-dark dark:text-lsc-cream truncate max-w-xs" title={item.item_title || `Item #${item.item_copy_id}`}>
                        {item.item_title || `Item #${item.item_copy_id}`}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-sm text-lsc-dark/80 dark:text-lsc-cream/80">
                      {item.patron_name || "-"}
                    </td>
                    <td className="px-4 py-3 text-sm text-lsc-dark/80 dark:text-lsc-cream/80">
                      {getLostTypeLabel(item.lost_type)}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${getLostStatusColor(item.status)}`}>
                        {formatStatus(item.status)}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                      {formatCurrency(item.replacement_cost)}
                    </td>
                    <td className="px-4 py-3 text-sm text-lsc-dark/80 dark:text-lsc-cream/80">
                      {formatDate(item.reported_at)}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        {(item.status === "reported" || item.status === "confirmed" || item.status === "charged") && (
                          <>
                            <button
                              onClick={() => { setSelectedLostItem(item); setShowFoundModal(true) }}
                              className="p-1.5 text-status-success-600 hover:bg-status-success-100 dark:bg-status-success-900/30 dark:hover:bg-status-success-900/30 rounded-lg transition-colors"
                              title="Mark as Found"
                            >
                              <CheckCircle className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => { setSelectedLostItem(item); setShowWriteOffModal(true) }}
                              className="p-1.5 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-earth-100 dark:bg-earth-700 dark:hover:bg-earth-900/30 rounded-lg transition-colors"
                              title="Write Off"
                            >
                              <Archive className="w-4 h-4" />
                            </button>
                          </>
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
            <FileX className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p>{t('components.staffLostDamaged.lostItemsTab.noLostItemsFound')}</p>
          </div>
        )}
      </div>
      {lostItemsData && (
        <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
          Showing {lostItemsData.items.length} of {lostItemsData.total} items
        </div>
      )}
    </div>
  )
}

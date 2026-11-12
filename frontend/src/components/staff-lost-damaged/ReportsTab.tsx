/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React from 'react'
import {
  Loader2, DollarSign, Package, BarChart3, AlertTriangle,
} from "lucide-react"
import { formatCurrency } from "../../utils/format-utils"
import { useTranslation } from '@/i18n'

interface FinancialSummary {
  total_charges: number
  total_collected: number
  total_outstanding: number
  total_waived: number
  total_credits: number
  collection_rate: number
}

interface InventorySummary {
  total_lost: number
  total_damaged: number
  in_mending: number
  items_found: number
}

interface ChargesByType {
  lost_item_charges: number
  damaged_item_charges: number
  processing_fees: number
  total: number
}

interface PatronRisk {
  patron_id: number
  patron_name: string
  lost_item_count: number
  damaged_item_count: number
  claims_returned_count: number
  total_charges: number
  risk_score: number
}

interface ReportsTabProps {
  financialSummary: FinancialSummary | null | undefined
  financialLoading: boolean
  inventorySummary: InventorySummary | null | undefined
  inventoryLoading: boolean
  chargesByType: ChargesByType | null | undefined
  patronRiskData: PatronRisk[] | undefined
}

export function ReportsTab({
  financialSummary,
  financialLoading,
  inventorySummary,
  inventoryLoading,
  chargesByType,
  patronRiskData,
}: ReportsTabProps): React.ReactElement {
  const { t } = useTranslation()
  return (
    <div className="space-y-6">
      {/* Financial Summary */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700">
        <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
          <DollarSign className="w-5 h-5" /> Financial Summary
        </h3>
        {financialLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-6 h-6 motion-safe:animate-spin text-lsc-rose" />
          </div>
        ) : financialSummary ? (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
            <div className="bg-lsc-cream dark:bg-earth-700/50 rounded-lg p-4">
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Total Charges</p>
              <p className="text-xl font-bold text-lsc-dark dark:text-lsc-cream">{formatCurrency(financialSummary.total_charges)}</p>
            </div>
            <div className="bg-lsc-cream dark:bg-earth-700/50 rounded-lg p-4">
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Total Collected</p>
              <p className="text-xl font-bold text-status-success-600 dark:text-status-success-400">{formatCurrency(financialSummary.total_collected)}</p>
            </div>
            <div className="bg-lsc-cream dark:bg-earth-700/50 rounded-lg p-4">
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Outstanding</p>
              <p className="text-xl font-bold text-status-warning-600 dark:text-status-warning-400">{formatCurrency(financialSummary.total_outstanding)}</p>
            </div>
            <div className="bg-lsc-cream dark:bg-earth-700/50 rounded-lg p-4">
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Waived</p>
              <p className="text-xl font-bold text-lsc-dark dark:text-lsc-cream">{formatCurrency(financialSummary.total_waived)}</p>
            </div>
            <div className="bg-lsc-cream dark:bg-earth-700/50 rounded-lg p-4">
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Credits</p>
              <p className="text-xl font-bold text-lsc-rose dark:text-lsc-rose-light">{formatCurrency(financialSummary.total_credits)}</p>
            </div>
            <div className="bg-lsc-cream dark:bg-earth-700/50 rounded-lg p-4">
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Collection Rate</p>
              <p className="text-xl font-bold text-lsc-dark dark:text-lsc-cream">{(financialSummary.collection_rate * 100).toFixed(1)}%</p>
            </div>
          </div>
        ) : (
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('components.staffLostDamaged.reportsTab.noFinancialDataAvailable')}</p>
        )}
      </div>

      {/* Inventory Summary */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700">
        <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
          <Package className="w-5 h-5" /> Inventory Summary
        </h3>
        {inventoryLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-6 h-6 motion-safe:animate-spin text-lsc-rose" />
          </div>
        ) : inventorySummary ? (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-lsc-cream dark:bg-earth-700/50 rounded-lg p-4">
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Total Lost</p>
              <p className="text-xl font-bold text-status-danger-600 dark:text-status-danger-400">{inventorySummary.total_lost}</p>
            </div>
            <div className="bg-lsc-cream dark:bg-earth-700/50 rounded-lg p-4">
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Total Damaged</p>
              <p className="text-xl font-bold text-status-warning-600 dark:text-status-warning-400">{inventorySummary.total_damaged}</p>
            </div>
            <div className="bg-lsc-cream dark:bg-earth-700/50 rounded-lg p-4">
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">In Mending</p>
              <p className="text-xl font-bold text-category-600 dark:text-category-400">{inventorySummary.in_mending}</p>
            </div>
            <div className="bg-lsc-cream dark:bg-earth-700/50 rounded-lg p-4">
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Items Found</p>
              <p className="text-xl font-bold text-status-success-600 dark:text-status-success-400">{inventorySummary.items_found}</p>
            </div>
          </div>
        ) : (
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('components.staffLostDamaged.reportsTab.noInventoryDataAvailable')}</p>
        )}
      </div>

      {/* Charges by Type */}
      {chargesByType && (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700">
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
            <BarChart3 className="w-5 h-5" /> Charges by Type
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-lsc-cream dark:bg-earth-700/50 rounded-lg p-4">
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Lost Items</p>
              <p className="text-xl font-bold text-lsc-dark dark:text-lsc-cream">{formatCurrency(chargesByType.lost_item_charges)}</p>
            </div>
            <div className="bg-lsc-cream dark:bg-earth-700/50 rounded-lg p-4">
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Damaged Items</p>
              <p className="text-xl font-bold text-lsc-dark dark:text-lsc-cream">{formatCurrency(chargesByType.damaged_item_charges)}</p>
            </div>
            <div className="bg-lsc-cream dark:bg-earth-700/50 rounded-lg p-4">
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Processing Fees</p>
              <p className="text-xl font-bold text-lsc-dark dark:text-lsc-cream">{formatCurrency(chargesByType.processing_fees)}</p>
            </div>
            <div className="bg-lsc-cream dark:bg-earth-700/50 rounded-lg p-4">
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Total</p>
              <p className="text-xl font-bold text-lsc-rose dark:text-lsc-rose-light">{formatCurrency(chargesByType.total)}</p>
            </div>
          </div>
        </div>
      )}

      {/* Patron Risk Report */}
      {patronRiskData && patronRiskData.length > 0 && (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700">
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
            <AlertTriangle className="w-5 h-5" /> High-Risk Patrons
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-lsc-cream/50 dark:bg-earth-700/50">
                <tr className="text-left text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                  <th className="px-4 py-2 font-medium">Patron</th>
                  <th className="px-4 py-2 font-medium">Lost</th>
                  <th className="px-4 py-2 font-medium">Damaged</th>
                  <th className="px-4 py-2 font-medium">Claims</th>
                  <th className="px-4 py-2 font-medium">Total Charges</th>
                  <th className="px-4 py-2 font-medium">Risk Score</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-lsc-border dark:divide-earth-700">
                {patronRiskData.map((patron) => (
                  <tr key={patron.patron_id}>
                    <td className="px-4 py-2 text-sm text-lsc-dark dark:text-lsc-cream">{patron.patron_name}</td>
                    <td className="px-4 py-2 text-sm">{patron.lost_item_count}</td>
                    <td className="px-4 py-2 text-sm">{patron.damaged_item_count}</td>
                    <td className="px-4 py-2 text-sm">{patron.claims_returned_count}</td>
                    <td className="px-4 py-2 text-sm">{formatCurrency(patron.total_charges)}</td>
                    <td className="px-4 py-2">
                      <span className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${
                        patron.risk_score >= 8 ? "bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900/30 dark:text-status-danger-400" :
                        patron.risk_score >= 5 ? "bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-400" :
                        "bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-400"
                      }`}>
                        {patron.risk_score.toFixed(1)}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}

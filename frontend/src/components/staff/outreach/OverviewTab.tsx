/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { AlertTriangle, TrendingUp, XCircle, AlertCircle } from 'lucide-react'
import type {
  getOverdueSummary,
  getDepositSummary,
  getPartnerEngagementAudit,
} from '../../../api/staff-outreach-api'

type OverdueSummary = Awaited<ReturnType<typeof getOverdueSummary>>
type DepositSummaryData = Awaited<ReturnType<typeof getDepositSummary>>
type EngagementAudit = Awaited<ReturnType<typeof getPartnerEngagementAudit>>

interface Props {
  overdueSummary: OverdueSummary | undefined
  depositSummary: DepositSummaryData | undefined
  engagementAudit: EngagementAudit | undefined
  formatDate: (d: string) => string
  formatCurrency: (amount: number) => string
  onViewCheckouts: () => void
}

export function OverviewTab({ overdueSummary, depositSummary, engagementAudit, formatDate, formatCurrency, onViewCheckouts }: Props) {
  return (
    <div className="space-y-6">
      {overdueSummary && overdueSummary.total_overdue_checkouts > 0 && (
        <div className="bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-3">
            <AlertTriangle className="w-5 h-5 text-status-danger-600 dark:text-status-danger-400" />
            <h3 className="font-serif font-semibold text-status-danger-800 dark:text-status-danger-300">
              Overdue Bulk Checkouts ({overdueSummary.total_overdue_checkouts})
            </h3>
          </div>
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {overdueSummary.checkouts.slice(0, 5).map((checkout) => (
              <div key={checkout.checkout_id} className="flex items-center justify-between text-sm p-2 bg-lsc-white dark:bg-earth-800 rounded">
                <div>
                  <p className="font-medium text-lsc-dark dark:text-lsc-cream">{checkout.checkout_name}</p>
                  <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
                    {checkout.partner_name} - {checkout.items_outstanding} items outstanding
                  </p>
                </div>
                <span className="text-status-danger-600 dark:text-status-danger-400 font-medium">
                  {checkout.days_overdue} days overdue
                </span>
              </div>
            ))}
          </div>
          <button
            onClick={onViewCheckouts}
            className="mt-3 text-sm text-status-danger-600 dark:text-status-danger-400 hover:underline"
          >
            View all overdue checkouts
          </button>
        </div>
      )}

      {engagementAudit && (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700">
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-lsc-rose" />
            Partner Engagement (Last 12 Months)
          </h3>
          <div className="grid grid-cols-4 gap-4 mb-4">
            <div className="text-center p-3 bg-status-success-50 dark:bg-status-success-900/20 rounded-lg">
              <p className="text-2xl font-bold text-status-success-600 dark:text-status-success-400">
                {engagementAudit.engagement_breakdown.high}
              </p>
              <p className="text-sm text-status-success-800 dark:text-status-success-300">High</p>
            </div>
            <div className="text-center p-3 bg-earth-50 dark:bg-earth-800/20 rounded-lg">
              <p className="text-2xl font-bold text-lsc-rose dark:text-lsc-rose-light">
                {engagementAudit.engagement_breakdown.medium}
              </p>
              <p className="text-sm text-earth-800 dark:text-lsc-rose-light">Medium</p>
            </div>
            <div className="text-center p-3 bg-status-warning-50 dark:bg-status-warning-900/20 rounded-lg">
              <p className="text-2xl font-bold text-status-warning-600 dark:text-status-warning-400">
                {engagementAudit.engagement_breakdown.low}
              </p>
              <p className="text-sm text-status-warning-800 dark:text-status-warning-300">Low</p>
            </div>
            <div className="text-center p-3 bg-earth-50 dark:bg-earth-800/50 rounded-lg">
              <p className="text-2xl font-bold text-lsc-dark/70 dark:text-lsc-cream/70">
                {engagementAudit.engagement_breakdown.none}
              </p>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">None</p>
            </div>
          </div>
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {engagementAudit.partners.slice(0, 10).map((partner) => (
              <div key={partner.partner_id} className="flex items-center justify-between p-2 bg-lsc-cream/50 dark:bg-earth-700/50 rounded">
                <div>
                  <p className="font-medium text-lsc-dark dark:text-lsc-cream">{partner.partner_name}</p>
                  <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                    {partner.visits_completed} visits, {partner.bulk_checkouts} checkouts
                  </p>
                </div>
                <div className="text-right">
                  <p className="font-medium text-lsc-rose">{partner.engagement_score} pts</p>
                  {partner.last_activity && (
                    <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                      Last: {formatDate(partner.last_activity)}
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {depositSummary && (
        <div className="grid md:grid-cols-2 gap-4">
          {depositSummary.expired_deposits.length > 0 && (
            <div className="bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800 rounded-xl p-4">
              <h4 className="font-serif font-semibold text-status-danger-800 dark:text-status-danger-300 mb-3 flex items-center gap-2">
                <XCircle className="w-4 h-4" />
                Expired Deposits ({depositSummary.expired_deposits.length})
              </h4>
              <div className="space-y-2">
                {depositSummary.expired_deposits.slice(0, 3).map((dep) => (
                  <div key={dep.deposit_id} className="flex justify-between text-sm p-2 bg-lsc-white dark:bg-earth-800 rounded">
                    <span className="text-lsc-dark dark:text-lsc-cream">{dep.partner_name}</span>
                    <span className="text-status-danger-600 dark:text-status-danger-400">{formatCurrency(dep.remaining)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
          {depositSummary.expiring_within_30_days.length > 0 && (
            <div className="bg-status-warning-50 dark:bg-status-warning-900/20 border border-status-warning-200 dark:border-status-warning-800 rounded-xl p-4">
              <h4 className="font-serif font-semibold text-status-warning-800 dark:text-status-warning-300 mb-3 flex items-center gap-2">
                <AlertCircle className="w-4 h-4" />
                Expiring Soon ({depositSummary.expiring_within_30_days.length})
              </h4>
              <div className="space-y-2">
                {depositSummary.expiring_within_30_days.slice(0, 3).map((dep) => (
                  <div key={dep.deposit_id} className="flex justify-between text-sm p-2 bg-lsc-white dark:bg-earth-800 rounded">
                    <span className="text-lsc-dark dark:text-lsc-cream">{dep.partner_name}</span>
                    <span className="text-status-warning-600 dark:text-status-warning-400">{dep.days_until_expiry} days</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

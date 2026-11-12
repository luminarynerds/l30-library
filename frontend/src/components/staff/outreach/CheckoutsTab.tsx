/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { CheckCircle2, Loader2 } from 'lucide-react'
import type { BulkCheckoutStatus, getOverdueSummary } from '../../../api/staff-outreach-api'

type OverdueSummary = Awaited<ReturnType<typeof getOverdueSummary>>

interface Props {
  overdueSummary: OverdueSummary | undefined
  overdueLoading: boolean
  checkoutStatusFilter: BulkCheckoutStatus | ""
  setCheckoutStatusFilter: (s: BulkCheckoutStatus | "") => void
  selectedCheckouts: number[]
  setSelectedCheckouts: (ids: number[]) => void
  onExtendDue: () => void
  formatDate: (d: string) => string
}

export function CheckoutsTab({
  overdueSummary, overdueLoading, checkoutStatusFilter, setCheckoutStatusFilter,
  selectedCheckouts, setSelectedCheckouts, onExtendDue, formatDate,
}: Props) {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-4 flex-1">
          <select
            value={checkoutStatusFilter}
            onChange={(e) => setCheckoutStatusFilter(e.target.value as BulkCheckoutStatus | "")}
            className="px-4 py-2 bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-lsc-rose text-lsc-dark dark:text-lsc-cream"
          >
            <option value="">All Statuses</option>
            <option value="pending">Pending</option>
            <option value="active">Active</option>
            <option value="overdue">Overdue</option>
            <option value="returned">Returned</option>
            <option value="partially_returned">Partially Returned</option>
            <option value="lost">Lost</option>
          </select>
        </div>
        <button
          onClick={onExtendDue}
          disabled={selectedCheckouts.length === 0}
          className="flex items-center gap-2 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 disabled:bg-earth-400 text-white rounded-lg text-sm"
        >
          Extend Due Dates
        </button>
      </div>

      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 overflow-hidden">
        {overdueLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-6 h-6 motion-safe:animate-spin text-lsc-rose" />
          </div>
        ) : overdueSummary?.checkouts && overdueSummary.checkouts.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-left text-sm text-lsc-dark/70 dark:text-lsc-cream/70 border-b border-lsc-border dark:border-earth-700 bg-lsc-cream/50 dark:bg-earth-700/50">
                  <th className="px-4 py-3 font-medium">
                    <input
                      type="checkbox"
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSelectedCheckouts(overdueSummary.checkouts.map(c => c.checkout_id))
                        } else {
                          setSelectedCheckouts([])
                        }
                      }}
                      checked={selectedCheckouts.length === overdueSummary.checkouts.length}
                      className="rounded"
                    />
                  </th>
                  <th className="px-4 py-3 font-medium">Checkout</th>
                  <th className="px-4 py-3 font-medium">Partner</th>
                  <th className="px-4 py-3 font-medium">Requestor</th>
                  <th className="px-4 py-3 font-medium">Due Date</th>
                  <th className="px-4 py-3 font-medium">Days Overdue</th>
                  <th className="px-4 py-3 font-medium">Items</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-lsc-border dark:divide-earth-700">
                {overdueSummary.checkouts.map((checkout) => (
                  <tr key={checkout.checkout_id} className="hover:bg-lsc-cream/50 dark:hover:bg-earth-700/50 transition-colors">
                    <td className="px-4 py-3">
                      <input
                        type="checkbox"
                        checked={selectedCheckouts.includes(checkout.checkout_id)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setSelectedCheckouts([...selectedCheckouts, checkout.checkout_id])
                          } else {
                            setSelectedCheckouts(selectedCheckouts.filter(id => id !== checkout.checkout_id))
                          }
                        }}
                        className="rounded"
                      />
                    </td>
                    <td className="px-4 py-3">
                      <p className="font-medium text-lsc-dark dark:text-lsc-cream">{checkout.checkout_name}</p>
                    </td>
                    <td className="px-4 py-3 text-sm text-lsc-dark/80 dark:text-lsc-cream/80">
                      {checkout.partner_name}
                    </td>
                    <td className="px-4 py-3">
                      <p className="text-sm text-lsc-dark dark:text-lsc-cream">{checkout.requestor}</p>
                      {checkout.requestor_email && (
                        <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{checkout.requestor_email}</p>
                      )}
                    </td>
                    <td className="px-4 py-3 text-sm text-lsc-dark/80 dark:text-lsc-cream/80">
                      {formatDate(checkout.due_date)}
                    </td>
                    <td className="px-4 py-3">
                      <span className="px-2 py-1 text-xs font-medium rounded-full bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900/30 dark:text-status-danger-400">
                        {checkout.days_overdue} days
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-lsc-dark/80 dark:text-lsc-cream/80">
                      {checkout.items_outstanding} / {checkout.total_items}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-8 text-lsc-dark/70 dark:text-lsc-cream/70">
            <CheckCircle2 className="w-12 h-12 mx-auto mb-3 opacity-50 text-status-success-500" />
            <p>No overdue checkouts!</p>
          </div>
        )}
      </div>
    </div>
  )
}

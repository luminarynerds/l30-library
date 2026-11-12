/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { XCircle, AlertCircle } from 'lucide-react'
import { useTranslation } from '@/i18n'
import type { DepositStatus, getDepositSummary } from '../../../api/staff-outreach-api'

type DepositSummaryData = Awaited<ReturnType<typeof getDepositSummary>>

interface Props {
  depositSummary: DepositSummaryData | undefined
  depositStatusFilter: DepositStatus | ""
  setDepositStatusFilter: (s: DepositStatus | "") => void
  selectedDeposits: number[]
  setSelectedDeposits: (ids: number[]) => void
  onForfeit: () => void
  formatCurrency: (amount: number) => string
}

export function DepositsTab({
  depositSummary, depositStatusFilter, setDepositStatusFilter,
  selectedDeposits, setSelectedDeposits, onForfeit, formatCurrency,
}: Props) {
  const { t } = useTranslation()
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-4 flex-1">
          <select
            value={depositStatusFilter}
            onChange={(e) => setDepositStatusFilter(e.target.value as DepositStatus | "")}
            className="px-4 py-2 bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-lsc-rose text-lsc-dark dark:text-lsc-cream"
          >
            <option value="">All Statuses</option>
            <option value="held">Held</option>
            <option value="partially_applied">Partially Applied</option>
            <option value="fully_applied">Fully Applied</option>
            <option value="refunded">Refunded</option>
            <option value="forfeited">Forfeited</option>
          </select>
        </div>
        <button
          onClick={onForfeit}
          disabled={selectedDeposits.length === 0}
          className="flex items-center gap-2 px-4 py-2 bg-status-danger-600 hover:bg-status-danger-700 disabled:bg-earth-400 text-white rounded-lg text-sm"
        >
          Forfeit Selected
        </button>
      </div>

      {depositSummary && (
        <div className="grid md:grid-cols-2 gap-4">
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700">
            <h4 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-3 flex items-center gap-2">
              <XCircle className="w-4 h-4 text-status-danger-500" />
              Expired Deposits
            </h4>
            {depositSummary.expired_deposits.length > 0 ? (
              <div className="space-y-2">
                {depositSummary.expired_deposits.map((dep) => (
                  <div key={dep.deposit_id} className="flex items-center justify-between p-2 bg-status-danger-50 dark:bg-status-danger-900/20 rounded">
                    <div className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={selectedDeposits.includes(dep.deposit_id)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setSelectedDeposits([...selectedDeposits, dep.deposit_id])
                          } else {
                            setSelectedDeposits(selectedDeposits.filter(id => id !== dep.deposit_id))
                          }
                        }}
                        className="rounded"
                      />
                      <div>
                        <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">{dep.partner_name}</p>
                        <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{dep.days_expired} days expired</p>
                      </div>
                    </div>
                    <span className="font-medium text-status-danger-600 dark:text-status-danger-400">{formatCurrency(dep.remaining)}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">No expired deposits</p>
            )}
          </div>

          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700">
            <h4 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-3 flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-status-warning-500" />
              Expiring Within 30 Days
            </h4>
            {depositSummary.expiring_within_30_days.length > 0 ? (
              <div className="space-y-2">
                {depositSummary.expiring_within_30_days.map((dep) => (
                  <div key={dep.deposit_id} className="flex items-center justify-between p-2 bg-status-warning-50 dark:bg-status-warning-900/20 rounded">
                    <div>
                      <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">{dep.partner_name}</p>
                      <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{dep.days_until_expiry} days left</p>
                    </div>
                    <span className="font-medium text-status-warning-600 dark:text-status-warning-400">{formatCurrency(dep.remaining)}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{t('staffOutreach.noDepositsExpiringSoon')}</p>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

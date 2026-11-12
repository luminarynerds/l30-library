/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { AlertTriangle } from 'lucide-react'

export interface FundSpendPreviewFund {
  name: string
  available_amount: number
}

interface FundSpendPreviewProps {
  fund: FundSpendPreviewFund | null
  newAmount: number
  formatMoney: (n: number) => string
}

export default function FundSpendPreview({ fund, newAmount, formatMoney }: FundSpendPreviewProps) {
  if (!fund) return null

  const available = Number(fund.available_amount) || 0
  const spend = Number(newAmount) || 0
  const after = available - spend
  const negative = after < 0

  return (
    <div
      className="p-4 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-cream/50 dark:bg-lsc-brown/30"
      data-testid="fund-spend-preview"
      aria-live="polite"
    >
      <div className="text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
        Fund: <span className="font-semibold">{fund.name}</span>
      </div>
      <dl className="space-y-1 text-sm">
        <div className="flex justify-between">
          <dt className="text-lsc-dark/70 dark:text-lsc-cream/70">Available</dt>
          <dd className="font-medium text-lsc-dark dark:text-lsc-cream tabular-nums">{formatMoney(available)}</dd>
        </div>
        <div className="flex justify-between">
          <dt className="text-lsc-dark/70 dark:text-lsc-cream/70">This PO</dt>
          <dd className="font-medium text-lsc-dark dark:text-lsc-cream tabular-nums">{formatMoney(spend)}</dd>
        </div>
        <div className="flex justify-between items-center pt-1 border-t border-lsc-border/60 dark:border-earth-700">
          <dt className="text-lsc-dark/70 dark:text-lsc-cream/70">After</dt>
          <dd
            className={
              'font-semibold tabular-nums flex items-center gap-1 ' +
              (negative
                ? 'text-status-danger-700 dark:text-status-danger-400'
                : 'text-status-success-700 dark:text-status-success-400')
            }
          >
            {negative && <AlertTriangle aria-hidden="true" className="w-4 h-4" />}
            <span>{formatMoney(after)}</span>
          </dd>
        </div>
      </dl>
      {negative && (
        <p className="mt-2 text-xs text-status-danger-700 dark:text-status-danger-400">
          This PO would overspend the fund by {formatMoney(Math.abs(after))}.
        </p>
      )}
    </div>
  )
}

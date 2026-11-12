/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ChevronDown, ChevronRight, DollarSign, Calendar, Package, Receipt } from 'lucide-react'
import { clsx } from '@/utils/helpers'
import { useTranslation, formatCurrency, getCurrentLocale } from '@/i18n'
import { getPatronFinesDetail, type FineDetailItem, type FinePaymentDetail } from '@/api/staff-api/fines'

const STATUS_STYLES: Record<string, string> = {
  unpaid: 'bg-status-danger-100 text-status-danger-700 dark:bg-status-danger-900/30 dark:text-status-danger-300',
  partial: 'bg-status-warning-100 text-status-warning-700 dark:bg-status-warning-900/30 dark:text-status-warning-300',
  paid: 'bg-status-success-100 text-status-success-700 dark:bg-status-success-900/30 dark:text-status-success-300',
  waived: 'bg-category-100 text-category-700 dark:bg-category-900/30 dark:text-category-300',
}

const TYPE_LABELS: Record<string, string> = {
  overdue: 'Overdue',
  lost_item: 'Lost Item',
  damaged_item: 'Damaged',
  other: 'Other',
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '—'
  return new Date(dateStr).toLocaleDateString(getCurrentLocale(), {
    month: 'short', day: 'numeric', year: 'numeric',
  })
}

function PaymentRow({ payment }: { payment: FinePaymentDetail }) {
  const { language } = useTranslation()
  return (
    <tr className="text-sm">
      <td className="py-1.5 pr-3 text-lsc-dark/70 dark:text-lsc-cream/70">{formatDate(payment.created_at)}</td>
      <td className="py-1.5 pr-3 font-medium text-lsc-dark dark:text-lsc-cream">{formatCurrency(payment.amount, language, 'USD')}</td>
      <td className="py-1.5 pr-3 text-lsc-dark/70 dark:text-lsc-cream/70 capitalize">{payment.payment_method}</td>
      <td className="py-1.5 pr-3 text-lsc-dark/70 dark:text-lsc-cream/70">{payment.processed_by_name || '—'}</td>
      <td className="py-1.5 text-lsc-dark/70 dark:text-lsc-cream/60 text-xs">{payment.receipt_number || '—'}</td>
    </tr>
  )
}

function FineCard({ fine }: { fine: FineDetailItem }) {
  const { language } = useTranslation()
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="border border-lsc-border dark:border-earth-700 rounded-xl overflow-hidden">
      {/* Summary row — always visible */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-start gap-3 p-4 text-left hover:bg-lsc-cream/50 dark:hover:bg-earth-800/50 transition-colors focus:outline-none focus:ring-2 focus:ring-inset focus:ring-lsc-rose"
        aria-expanded={expanded}
        aria-label={`Fine: ${fine.explanation}`}
      >
        <span className="mt-0.5 flex-shrink-0 text-lsc-dark/70 dark:text-lsc-cream/60">
          {expanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
        </span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <span className={clsx('text-xs font-semibold uppercase px-1.5 py-0.5 rounded-full', STATUS_STYLES[fine.status] || STATUS_STYLES.unpaid)}>
              {fine.status}
            </span>
            <span className="text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/60">
              {TYPE_LABELS[fine.fine_type] || fine.fine_type}
            </span>
            <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60">
              {formatDate(fine.created_at)}
            </span>
          </div>
          <p className="text-sm text-lsc-dark dark:text-lsc-cream leading-snug">
            {fine.explanation}
          </p>
        </div>
        <div className="text-right flex-shrink-0">
          <p className="text-sm font-bold text-lsc-dark dark:text-lsc-cream">{formatCurrency(fine.balance, language, 'USD')}</p>
          {fine.amount_paid > 0 && (
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60">of {formatCurrency(fine.amount, language, 'USD')}</p>
          )}
        </div>
      </button>

      {/* Expanded detail */}
      {expanded && (
        <div className="border-t border-lsc-border dark:border-earth-700 bg-lsc-cream/30 dark:bg-earth-900/30 px-4 py-3 space-y-4">
          {/* Item & checkout info */}
          {fine.item_title && (
            <div className="flex items-start gap-2">
              <Package className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/60 mt-0.5 flex-shrink-0" aria-hidden="true" />
              <div className="text-sm">
                <p className="font-medium text-lsc-dark dark:text-lsc-cream">
                  {fine.item_title}
                  {fine.item_author && <span className="font-normal text-lsc-dark/70 dark:text-lsc-cream/60"> by {fine.item_author}</span>}
                </p>
                <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60">
                  {fine.item_type && <span className="capitalize">{fine.item_type}</span>}
                  {fine.item_barcode && <span> · {fine.item_barcode}</span>}
                </p>
              </div>
            </div>
          )}

          {/* Checkout timeline */}
          {fine.checked_out_at && (
            <div className="flex items-start gap-2">
              <Calendar className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/60 mt-0.5 flex-shrink-0" aria-hidden="true" />
              <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                Checked out {formatDate(fine.checked_out_at)}
                {fine.due_date && <span> · Due {formatDate(fine.due_date)}</span>}
                {fine.returned_at && <span> · Returned {formatDate(fine.returned_at)}</span>}
              </div>
            </div>
          )}

          {/* Waiver info */}
          {fine.waived_at && (
            <div className="flex items-start gap-2">
              <DollarSign className="w-4 h-4 text-category-500 dark:text-category-400 mt-0.5 flex-shrink-0" aria-hidden="true" />
              <p className="text-sm text-category-700 dark:text-category-300">
                Waived on {formatDate(fine.waived_at)}
                {fine.waived_by_name && <span> by {fine.waived_by_name}</span>}
              </p>
            </div>
          )}

          {/* Payment history */}
          {fine.payments.length > 0 && (
            <div>
              <div className="flex items-center gap-2 mb-2">
                <Receipt className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/60 flex-shrink-0" aria-hidden="true" />
                <h4 className="text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/60 uppercase tracking-wide">
                  Payment History
                </h4>
              </div>
              <table className="w-full">
                <thead>
                  <tr className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60">
                    <th className="text-left py-1 pr-3 font-medium">Date</th>
                    <th className="text-left py-1 pr-3 font-medium">Amount</th>
                    <th className="text-left py-1 pr-3 font-medium">Method</th>
                    <th className="text-left py-1 pr-3 font-medium">Processed By</th>
                    <th className="text-left py-1 font-medium">Receipt</th>
                  </tr>
                </thead>
                <tbody>
                  {fine.payments.map(p => <PaymentRow key={p.id} payment={p} />)}
                </tbody>
              </table>
            </div>
          )}

          {fine.payments.length === 0 && fine.status !== 'waived' && fine.status !== 'paid' && (
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 italic">No payments recorded</p>
          )}

          {fine.notes && (
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 border-t border-lsc-border/50 dark:border-earth-700/50 pt-2">
              {fine.notes}
            </p>
          )}
        </div>
      )}
    </div>
  )
}

interface FineDetailPanelProps {
  patronId: number
}

export default function FineDetailPanel({ patronId }: FineDetailPanelProps) {
  const { language } = useTranslation()
  const { data, isLoading, error } = useQuery({
    queryKey: ['patron-fines-detail', patronId],
    queryFn: () => getPatronFinesDetail(patronId),
    staleTime: 60_000,
  })

  if (isLoading) {
    return (
      <div className="flex justify-center py-8">
        <div className="motion-safe:animate-spin w-6 h-6 border-2 border-lsc-rose border-t-transparent rounded-full" />
      </div>
    )
  }

  if (error) {
    return (
      <p className="text-sm text-status-danger-600 dark:text-status-danger-400 py-4">
        Failed to load fine details.
      </p>
    )
  }

  if (!data || data.fines.length === 0) {
    return (
      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60 py-4 italic">
        No fines on record.
      </p>
    )
  }

  return (
    <div className="space-y-3">
      {/* Summary header */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-bold text-lsc-dark dark:text-lsc-cream">
          Fines ({data.total_fines})
        </h3>
        {data.total_outstanding > 0 && (
          <span className="text-sm font-bold text-status-danger-600 dark:text-status-danger-400">
            {formatCurrency(data.total_outstanding, language, 'USD')} outstanding
          </span>
        )}
      </div>

      {/* Fine cards */}
      {data.fines.map(fine => (
        <FineCard key={fine.id} fine={fine} />
      ))}
    </div>
  )
}

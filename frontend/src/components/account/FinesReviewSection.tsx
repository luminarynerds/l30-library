/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Fines Review Section for patron self-service.
 *
 * Shows the patron their fines, balances, and payment history.
 */
import { useState, useEffect, useCallback } from 'react'
import { Clock, CheckCircle, AlertCircle, Loader2, ChevronDown, ChevronUp } from 'lucide-react'
import { useAuth } from '../../contexts/AuthContext'
import { fetchApi } from '../../api/fetchApi'
import { getCurrentLocale } from '@/i18n'

interface Fine {
  id: number
  fine_type: string
  status: string
  amount: number
  amount_paid: number
  balance: number
  description: string | null
  created_at: string | null
}

interface FineListResponse {
  fines: Fine[]
  total_outstanding: number
  total_paid: number
  total_fines: number
}

interface PaymentEntry {
  id: number
  fine_id: number
  amount: number
  payment_method: string
  notes: string | null
  created_at: string | null
}

const STATUS_STYLES: Record<string, { bg: string; text: string; icon: React.ReactNode }> = {
  unpaid: { bg: 'bg-status-danger-50 dark:bg-status-danger-900/20', text: 'text-status-danger-700 dark:text-status-danger-400', icon: <AlertCircle className="w-3 h-3" /> },
  partial: { bg: 'bg-status-warning-50 dark:bg-status-warning-900/20', text: 'text-status-warning-700 dark:text-status-warning-400', icon: <Clock className="w-3 h-3" /> },
  paid: { bg: 'bg-status-success-50 dark:bg-status-success-900/20', text: 'text-status-success-700 dark:text-status-success-400', icon: <CheckCircle className="w-3 h-3" /> },
  waived: { bg: 'bg-earth-50 dark:bg-earth-800/20', text: 'text-lsc-rose dark:text-lsc-rose-light', icon: <CheckCircle className="w-3 h-3" /> },
}

function formatCurrency(amount: number): string {
  return `$${amount.toFixed(2)}`
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return 'N/A'
  return new Date(dateStr).toLocaleDateString(getCurrentLocale(), {
    month: 'short', day: 'numeric', year: 'numeric',
  })
}

function FineTypeLabel({ type }: { type: string }) {
  const labels: Record<string, string> = {
    overdue: 'Overdue',
    lost_item: 'Lost Item',
    damaged_item: 'Damaged Item',
    other: 'Other',
  }
  return <span>{labels[type] || type}</span>
}

export function FinesReviewSection() {
  const { token } = useAuth()
  const [finesData, setFinesData] = useState<FineListResponse | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [expandedFine, setExpandedFine] = useState<number | null>(null)
  const [payments, setPayments] = useState<Record<number, PaymentEntry[]>>({})
  const [loadingPayments, setLoadingPayments] = useState<number | null>(null)

  const loadFines = useCallback(async () => {
    if (!token) return
    setIsLoading(true)
    try {
      const data = await fetchApi('/patron/profile/fines', {
        headers: { Authorization: `Bearer ${token}` },
      })
      setFinesData(data)
    } catch {
      // silently fail - will show empty state
    } finally {
      setIsLoading(false)
    }
  }, [token])

  useEffect(() => {
    loadFines()
  }, [loadFines])

  const loadPaymentHistory = async (fineId: number) => {
    if (!token || payments[fineId]) {
      setExpandedFine(expandedFine === fineId ? null : fineId)
      return
    }
    setLoadingPayments(fineId)
    setExpandedFine(fineId)
    try {
      const data = await fetchApi(`/patron/profile/fines/${fineId}/payments`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      setPayments(prev => ({ ...prev, [fineId]: data.payments }))
    } catch {
      // silently fail
    } finally {
      setLoadingPayments(null)
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-6 h-6 motion-safe:animate-spin text-lsc-rose" />
      </div>
    )
  }

  if (!finesData || finesData.total_fines === 0) {
    return (
      <div className="text-center py-12">
        <CheckCircle className="w-12 h-12 text-lsc-green mx-auto mb-3" />
        <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">No Fines</h3>
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60">
          Your account is in good standing. Keep it up!
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div className="p-4 bg-status-danger-50 dark:bg-status-danger-900/20 rounded-xl">
          <div className="text-xs text-status-danger-600 dark:text-status-danger-400 font-medium mb-1">Outstanding</div>
          <div className="text-xl font-bold text-status-danger-700 dark:text-status-danger-300">
            {formatCurrency(finesData.total_outstanding)}
          </div>
        </div>
        <div className="p-4 bg-status-success-50 dark:bg-status-success-900/20 rounded-xl">
          <div className="text-xs text-status-success-600 dark:text-status-success-400 font-medium mb-1">Total Paid</div>
          <div className="text-xl font-bold text-status-success-700 dark:text-status-success-300">
            {formatCurrency(finesData.total_paid)}
          </div>
        </div>
        <div className="p-4 bg-cream dark:bg-earth-800 rounded-xl">
          <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 font-medium mb-1">Total Fines</div>
          <div className="text-xl font-bold text-lsc-dark dark:text-lsc-cream">
            {finesData.total_fines}
          </div>
        </div>
      </div>

      {/* Fines List */}
      <div className="space-y-2">
        {finesData.fines.map(fine => {
          const style = (STATUS_STYLES[fine.status] ?? STATUS_STYLES.unpaid)!
          const isExpanded = expandedFine === fine.id

          return (
            <div key={fine.id} className="bg-cream dark:bg-earth-800 rounded-xl overflow-hidden">
              <button
                onClick={() => loadPaymentHistory(fine.id)}
                className="w-full p-4 flex items-center justify-between text-left hover:bg-lsc-rose/5 transition-colors"
              >
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <FineTypeLabel type={fine.fine_type} />
                    <span className={`inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full ${style.bg} ${style.text}`}>
                      {style.icon}
                      {fine.status}
                    </span>
                  </div>
                  {fine.description && (
                    <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60">{fine.description}</p>
                  )}
                  <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 mt-1">
                    {formatDate(fine.created_at)}
                  </p>
                </div>
                <div className="text-right ml-4">
                  <div className="text-sm font-bold text-lsc-dark dark:text-lsc-cream">
                    {formatCurrency(fine.balance)}
                  </div>
                  {fine.amount_paid > 0 && (
                    <div className="text-xs text-status-success-600 dark:text-status-success-400">
                      {formatCurrency(fine.amount_paid)} paid
                    </div>
                  )}
                </div>
                {isExpanded ? (
                  <ChevronUp className="w-4 h-4 ml-2 text-lsc-dark/70 dark:text-lsc-cream/60" />
                ) : (
                  <ChevronDown className="w-4 h-4 ml-2 text-lsc-dark/70 dark:text-lsc-cream/60" />
                )}
              </button>

              {isExpanded && (
                <div className="px-4 pb-4 border-t border-sage/10">
                  <h4 className="text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/60 mt-3 mb-2">
                    Payment History
                  </h4>
                  {loadingPayments === fine.id ? (
                    <div className="flex justify-center py-3">
                      <Loader2 className="w-4 h-4 motion-safe:animate-spin text-lsc-rose" />
                    </div>
                  ) : payments[fine.id]?.length ? (
                    <div className="space-y-2">
                      {payments[fine.id]?.map(p => (
                        <div key={p.id} className="flex items-center justify-between text-xs p-2 bg-lsc-white/50 dark:bg-earth-700/50 rounded-lg">
                          <div>
                            <span className="font-medium text-lsc-dark dark:text-lsc-cream">
                              {formatCurrency(p.amount)}
                            </span>
                            <span className="text-lsc-dark/70 dark:text-lsc-cream/60 ml-2">
                              via {p.payment_method}
                            </span>
                          </div>
                          <span className="text-lsc-dark/70 dark:text-lsc-cream/60">
                            {formatDate(p.created_at)}
                          </span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 py-2">
                      No payments recorded yet.
                    </p>
                  )}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

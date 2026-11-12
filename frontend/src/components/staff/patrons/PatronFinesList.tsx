/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useState } from 'react'
import { AlertCircle, Clock, DollarSign } from 'lucide-react'
import { listFines, type Fine } from '@/api/staff-api'
import { getAccessToken } from '@/utils/tokenStore'
import toast from 'react-hot-toast'
import { useTranslation, formatCurrency } from '@/i18n'

interface PatronFinesListProps {
  patronId: number
  onPayClick: (fineId: number, balance: number) => void
  onWaiveClick: (fineId: number, balance: number) => void
  refreshKey?: number
}

function fineStatusBadgeClass(status: string): string {
  switch (status) {
    case 'paid':
      return 'bg-status-success-100 dark:bg-status-success-900 text-status-success-800 dark:text-status-success-200'
    case 'partial':
      return 'bg-status-warning-100 dark:bg-status-warning-900 text-status-warning-800 dark:text-status-warning-200'
    case 'waived':
      return 'bg-earth-100 dark:bg-earth-900 text-earth-800 dark:text-lsc-rose-light/80'
    case 'unpaid':
      return 'bg-status-danger-100 dark:bg-status-danger-900 text-status-danger-800 dark:text-status-danger-200'
    default:
      return 'bg-earth-100 dark:bg-earth-950 text-earth-800 dark:text-earth-200'
  }
}

function fineTypeLabel(type: string): string {
  switch (type) {
    case 'overdue':
      return 'Overdue'
    case 'lost_item':
      return 'Lost Item'
    case 'damaged_item':
      return 'Damaged Item'
    default:
      return type.charAt(0).toUpperCase() + type.slice(1)
  }
}

export function PatronFinesList({ patronId, onPayClick, onWaiveClick, refreshKey = 0 }: PatronFinesListProps) {
  const { t, language } = useTranslation()
  const fmt = (amount: number): string => formatCurrency(amount, language, 'USD')
  const [fines, setFines] = useState<Fine[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const loadFines = async () => {
      setIsLoading(true)
      setError(null)
      try {
        const token = getAccessToken()
        if (!token) {
          setError('Authentication required')
          return
        }

        const response = await listFines(token, { patron_id: patronId, limit: 200 })
        setFines(response.fines)
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to load fines'
        setError(message)
        toast.error(message)
      } finally {
        setIsLoading(false)
      }
    }

    loadFines()
  }, [patronId, refreshKey])

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70">Loading fines...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-4 bg-status-danger-50 dark:bg-status-danger-900 border border-status-danger-200 dark:border-status-danger-800 rounded-xl flex gap-3">
        <AlertCircle className="w-5 h-5 text-status-danger-600 dark:text-status-danger-400 flex-shrink-0 mt-0.5" />
        <div>
          <p className="text-sm font-medium text-status-danger-900 dark:text-status-danger-100">Error loading fines</p>
          <p className="text-xs text-status-danger-800 dark:text-status-danger-200">{error}</p>
        </div>
      </div>
    )
  }

  if (fines.length === 0) {
    return (
      <div className="text-center py-8">
        <DollarSign className="w-12 h-12 text-lsc-dark/70 dark:text-lsc-rose-light mx-auto mb-3 opacity-50" />
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('components.staff.patronFinesList.noFinesOnRecord')}</p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {fines.map((fine) => {
        const balance = Number(fine.amount) - Number(fine.amount_paid)
        const isPayable = fine.status === 'unpaid' || fine.status === 'partial'
        const isWaivable = fine.status === 'unpaid' || fine.status === 'partial'

        return (
          <div key={fine.id} className="p-4 border border-lsc-border dark:border-earth-700 rounded-xl hover:bg-lsc-cream/30 dark:hover:bg-lsc-brown/20 transition-colors">
            <div className="flex items-start justify-between mb-3">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <h4 className="font-medium text-lsc-dark dark:text-lsc-cream">
                    {fineTypeLabel(fine.fine_type)}
                  </h4>
                  <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${fineStatusBadgeClass(fine.status)}`}>
                    {fine.status.charAt(0).toUpperCase() + fine.status.slice(1)}
                  </span>
                </div>
                {fine.description && (
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{fine.description}</p>
                )}
                <div className="flex items-center gap-3 mt-2 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                  <span className="flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {new Date(fine.created_at).toLocaleDateString()}
                  </span>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-2 mb-3 p-3 bg-lsc-cream/50 dark:bg-lsc-brown/30 rounded-lg text-sm">
              <div>
                <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Original</p>
                <p className="font-semibold text-lsc-dark dark:text-lsc-cream">{fmt(Number(fine.amount))}</p>
              </div>
              <div>
                <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Paid</p>
                <p className="font-semibold text-lsc-dark dark:text-lsc-cream">{fmt(Number(fine.amount_paid))}</p>
              </div>
              <div>
                <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Balance</p>
                <p className={`font-semibold ${balance > 0 ? 'text-lsc-rose dark:text-lsc-rose-light' : 'text-status-success-600 dark:text-status-success-400'}`}>
                  {fmt(balance)}
                </p>
              </div>
            </div>

            {isPayable || isWaivable ? (
              <div className="flex gap-2">
                {isPayable && (
                  <button
                    onClick={() => onPayClick(fine.id, balance)}
                    className="flex-1 px-3 py-2 text-sm bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg transition-colors font-medium"
                  >
                    Pay {fmt(balance)}
                  </button>
                )}
                {isWaivable && (
                  <button
                    onClick={() => onWaiveClick(fine.id, balance)}
                    className="flex-1 px-3 py-2 text-sm border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream/80 hover:bg-lsc-cream dark:hover:bg-lsc-brown rounded-lg transition-colors font-medium"
                  >
                    Waive
                  </button>
                )}
              </div>
            ) : null}

            {/* Payment history for this fine */}
            {Number(fine.amount_paid) > 0 && (
              <div className="mt-3 pt-3 border-t border-lsc-border/50 dark:border-earth-700/50">
                <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">Partial payments recorded</p>
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

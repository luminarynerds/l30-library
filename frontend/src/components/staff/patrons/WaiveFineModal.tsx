/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React, { useState, useCallback } from 'react'
import { X, Loader2, AlertCircle, AlertTriangle } from 'lucide-react'
import FocusTrap from 'focus-trap-react'
import { waiveFine } from '@/api/staff-api'
import { getAccessToken } from '@/utils/tokenStore'
import toast from 'react-hot-toast'
import { useTranslation, formatCurrency } from '@/i18n'

/** Waivers above this amount require typing the amount to confirm. */
const HIGH_VALUE_WAIVER_THRESHOLD = 50.0

interface WaiveFineModalProps {
  isOpen: boolean
  onClose: () => void
  onWaiveSuccess?: () => void
  balance: number
  patronId: number
  fineId: number
}

/** Per-fine waive reason must be at least this many characters (FE-only). */
const MIN_REASON_LENGTH = 5

export function WaiveFineModal({
  isOpen,
  onClose,
  onWaiveSuccess,
  balance,
  patronId: _patronId,
  fineId,
}: WaiveFineModalProps) {
  const { t, language } = useTranslation()
  const fmt = (amount: number): string => formatCurrency(amount, language, 'USD')
  const [reason, setReason] = useState('')
  const [isProcessing, setIsProcessing] = useState(false)
  const [confirmAmount, setConfirmAmount] = useState('')
  const [waiveAmount, setWaiveAmount] = useState<string>(Number(balance).toFixed(2))
  const [requiresApproval, setRequiresApproval] = useState(false)

  const numericWaive = Number(waiveAmount)
  const validAmount =
    !isNaN(numericWaive) &&
    numericWaive > 0 &&
    numericWaive <= Number(balance) + 1e-9
  const isHighValue = numericWaive >= HIGH_VALUE_WAIVER_THRESHOLD
  const amountConfirmed = !isHighValue || confirmAmount === numericWaive.toFixed(2)

  // Reset form when modal opens
  React.useEffect(() => {
    if (isOpen) {
      setReason('')
      setConfirmAmount('')
      setWaiveAmount(Number(balance).toFixed(2))
      setRequiresApproval(false)
    }
  }, [isOpen, balance])

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault()

      if (!reason.trim()) {
        toast.error(t('toast.reasonRequired'))
        return
      }

      if (reason.trim().length < MIN_REASON_LENGTH) {
        toast.error(t('toast.reasonTooShort'))
        return
      }

      if (!validAmount) {
        toast.error('Waive amount must be greater than zero and at most the outstanding balance.')
        return
      }

      if (isHighValue && !amountConfirmed) {
        toast.error(t('toast.confirmationRequired', { amount: numericWaive.toFixed(2) }))
        return
      }

      setIsProcessing(true)
      try {
        const token = getAccessToken()
        if (!token) {
          toast.error(t('toast.authenticationRequired'))
          return
        }

        const result = await waiveFine(token, fineId, {
          reason: reason.trim(),
          amount: numericWaive.toFixed(2),
          requires_approval: requiresApproval,
        })

        if (result.status === 'pending_approval') {
          toast.success(`Waiver of ${formatCurrency(numericWaive, language, 'USD')} submitted for approval.`)
        } else {
          toast.success(
            t('toast.fineWaivedAmount', { amount: formatCurrency(numericWaive, language, 'USD') })
          )
        }
        onWaiveSuccess?.()
        onClose()
      } catch (error: unknown) {
        toast.error(error instanceof Error ? error.message : t('toast.fineWaiveFailed'))
      } finally {
        setIsProcessing(false)
      }
    },
    [
      reason,
      numericWaive,
      fineId,
      isHighValue,
      amountConfirmed,
      validAmount,
      requiresApproval,
      onWaiveSuccess,
      onClose,
      t,
      language,
    ]
  )

  if (!isOpen) return null

  return (
    <FocusTrap
      focusTrapOptions={{
        initialFocus: 'body',
        allowOutsideClick: true,
        escapeDeactivates: false,
        fallbackFocus: () => document.body,
        returnFocusOnDeactivate: true,
      }}
    >
      <div className="fixed inset-0 motion-safe:backdrop-blur-md bg-black/50 flex items-center justify-center z-50 p-4" role="presentation">
        <div
          role="dialog"
          aria-modal="true"
          className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-md w-full"
        >
          <div className="flex items-center justify-between p-4 border-b border-lsc-border dark:border-earth-700">
            <h2 className="text-lg font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
              Waive Fine
            </h2>
            <button
              onClick={onClose}
              className="p-1 hover:bg-lsc-cream dark:hover:bg-lsc-brown rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-lsc-rose"
              aria-label={t('aria.staff.closeWaiveModal')}
            >
              <X className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
            </button>
          </div>

          <div className="p-4">
            {/* Warning banner */}
            <div className="p-3 bg-status-danger-50 dark:bg-status-danger-900 border border-status-danger-200 dark:border-status-danger-800 rounded-xl mb-4 flex gap-3">
              <AlertCircle className="w-5 h-5 text-status-danger-600 dark:text-status-danger-400 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-status-danger-900 dark:text-status-danger-100">
                  This action cannot be undone
                </p>
                <p className="text-xs text-status-danger-800 dark:text-status-danger-200 mt-1">
                  The fine will be marked as waived and removed from patron's balance.
                </p>
              </div>
            </div>

            {/* High-value warning banner */}
            {isHighValue && (
              <div className="p-3 bg-status-warning-50 dark:bg-status-warning-900 border-2 border-status-warning-400 dark:border-status-warning-600 rounded-xl mb-4 flex gap-3">
                <AlertTriangle className="w-5 h-5 text-status-warning-600 dark:text-status-warning-400 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-bold text-status-warning-900 dark:text-status-warning-100">
                    High-value waiver: {fmt(Number(balance))}
                  </p>
                  <p className="text-xs text-status-warning-800 dark:text-status-warning-200 mt-1">
                    This waiver exceeds {fmt(HIGH_VALUE_WAIVER_THRESHOLD)}.
                    Type the exact amount below to confirm.
                  </p>
                </div>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="p-3 bg-lsc-cream dark:bg-lsc-brown/30 rounded-xl">
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                  Outstanding balance
                </p>
                <p className="text-2xl font-bold text-lsc-rose dark:text-lsc-rose-light">
                  {fmt(Number(balance))}
                </p>
              </div>

              <div>
                <label htmlFor="waive-amount" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-2">
                  Amount to Waive <span className="text-status-danger-600">*</span>
                </label>
                <input
                  id="waive-amount"
                  type="number"
                  inputMode="decimal"
                  step="0.01"
                  min="0.01"
                  max={Number(balance).toFixed(2)}
                  value={waiveAmount}
                  onChange={(e) => setWaiveAmount(e.target.value)}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent font-mono"
                  required
                  aria-required="true"
                />
                <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                  Defaults to the full balance. Lower for a partial waiver.
                </p>
              </div>

              <div>
                <label htmlFor="waive-reason" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-2">
                  Reason for Waiving <span className="text-status-danger-600">*</span>
                </label>
                <textarea
                  id="waive-reason"
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent resize-none"
                  rows={4}
                  placeholder={t('placeholder.staff.egCustomerDisputeResolved')}
                  required
                  aria-required="true"
                  minLength={MIN_REASON_LENGTH}
                />
                <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                  Minimum {MIN_REASON_LENGTH} characters. This will be recorded in the audit log.
                </p>
              </div>

              <div className="flex items-start gap-2">
                <input
                  id="requires-approval"
                  type="checkbox"
                  checked={requiresApproval}
                  onChange={(e) => setRequiresApproval(e.target.checked)}
                  className="mt-1 h-4 w-4 rounded border-lsc-border focus:ring-lsc-rose"
                />
                <label htmlFor="requires-approval" className="text-sm text-lsc-dark dark:text-lsc-cream/80">
                  Requires director approval
                  <span className="block text-xs text-lsc-dark/60 dark:text-lsc-cream/60">
                    Send to the pending-waivers queue for an admin to review.
                  </span>
                </label>
              </div>

              {/* High-value amount confirmation field */}
              {isHighValue && (
                <div>
                  <label htmlFor="confirm-amount" className="block text-sm font-medium text-status-warning-800 dark:text-status-warning-200 mb-2">
                    Type &ldquo;{numericWaive.toFixed(2)}&rdquo; to confirm <span className="text-status-danger-600">*</span>
                  </label>
                  <input
                    id="confirm-amount"
                    type="text"
                    inputMode="decimal"
                    value={confirmAmount}
                    onChange={(e) => setConfirmAmount(e.target.value)}
                    className={`w-full px-3 py-2 border-2 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-status-warning-500 focus:border-transparent font-mono text-lg ${
                      confirmAmount && !amountConfirmed
                        ? 'border-status-danger-400 dark:border-status-danger-600'
                        : amountConfirmed
                          ? 'border-status-success-400 dark:border-status-success-600'
                          : 'border-status-warning-300 dark:border-status-warning-700'
                    }`}
                    placeholder={numericWaive.toFixed(2)}
                    autoComplete="off"
                  />
                  {confirmAmount && !amountConfirmed && (
                    <p className="text-xs text-status-danger-600 dark:text-status-danger-400 mt-1">
                      Amount does not match. Please type exactly: {numericWaive.toFixed(2)}
                    </p>
                  )}
                </div>
              )}

              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={onClose}
                  disabled={isProcessing}
                  className="flex-1 px-4 py-2 border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream/80 rounded-xl hover:bg-lsc-cream dark:hover:bg-lsc-brown transition-colors disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isProcessing || !reason.trim() || !validAmount || !amountConfirmed}
                  className="flex-1 px-4 py-2 bg-status-danger-600 hover:bg-status-danger-700 disabled:bg-status-danger-600/50 text-white rounded-xl transition-colors flex items-center justify-center gap-2 font-medium"
                >
                  {isProcessing ? (
                    <>
                      <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
                      Waiving...
                    </>
                  ) : (
                    'Confirm Waive'
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </FocusTrap>
  )
}

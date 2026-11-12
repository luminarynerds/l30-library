/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React, { useState, useCallback } from 'react'
import { X, Loader2 } from 'lucide-react'
import FocusTrap from 'focus-trap-react'
import { makePartialPayment, type PaymentMethod } from '@/api/staff-api'
import { getAccessToken } from '@/utils/tokenStore'
import toast from 'react-hot-toast'
import { useTranslation, formatCurrency } from '@/i18n'
import { clean } from '@/lib/utils'

interface FinePaymentModalProps {
  isOpen: boolean
  onClose: () => void
  onPaymentSuccess?: () => void
  balance: number
  patronId: number
  fineId: number
}

const PAYMENT_METHODS: PaymentMethod[] = ['cash', 'card', 'check', 'online', 'other']

export function FinePaymentModal({
  isOpen,
  onClose,
  onPaymentSuccess,
  balance,
  patronId: _patronId,
  fineId,
}: FinePaymentModalProps) {
  const { t, language } = useTranslation()
  const fmt = (amount: number): string => formatCurrency(amount, language, 'USD')
  const [paymentAmount, setPaymentAmount] = useState<string>(Number(balance).toFixed(2))
  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod>('cash')
  const [notes, setNotes] = useState('')
  const [isProcessing, setIsProcessing] = useState(false)

  // Reset form when modal opens
  React.useEffect(() => {
    if (isOpen) {
      setPaymentAmount(Number(balance).toFixed(2))
      setPaymentMethod('cash')
      setNotes('')
    }
  }, [isOpen, balance])

  const handlePayFull = useCallback(() => {
    setPaymentAmount(Number(balance).toFixed(2))
  }, [balance])

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault()

      const amount = parseFloat(paymentAmount)
      if (isNaN(amount) || amount <= 0) {
        toast.error(t('components.staff.finePayment.pleaseEnterAValidPayment'))
        return
      }

      if (amount > Number(balance)) {
        toast.error(t('toast.paymentExceedsBalance', { balance: fmt(Number(balance)) }))
        return
      }

      setIsProcessing(true)
      try {
        const token = getAccessToken()
        if (!token) {
          toast.error(t('components.staff.finePayment.authenticationRequiredPleaseLogIn'))
          return
        }

        await makePartialPayment(token, fineId, clean({
          amount,
          payment_method: paymentMethod,
          notes: notes || undefined,
        }))

        toast.success(t('toast.paymentRecorded', { amount: fmt(amount) }))
        onPaymentSuccess?.()
        onClose()
      } catch (error: unknown) {
        toast.error(error instanceof Error ? error.message : t('toast.paymentFailed'))
      } finally {
        setIsProcessing(false)
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [paymentAmount, balance, paymentMethod, notes, fineId, onPaymentSuccess, onClose]
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
              Record Fine Payment
            </h2>
            <button
              onClick={onClose}
              className="p-1 hover:bg-lsc-cream dark:hover:bg-lsc-brown rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-lsc-rose"
              aria-label={t('aria.staff.closePaymentModal')}
            >
              <X className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
            </button>
          </div>

          <div className="p-4">
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="p-3 bg-lsc-cream dark:bg-lsc-brown/30 rounded-xl">
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Outstanding Balance</p>
                <p className="text-2xl font-bold text-lsc-rose dark:text-lsc-rose-light">
                  {fmt(Number(balance))}
                </p>
              </div>

              <div>
                <label htmlFor="payment-amount" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-2">
                  Payment Amount <span className="text-status-danger-600">*</span>
                </label>
                <div className="flex gap-2">
                  <div className="flex-1 relative">
                    <span className="absolute left-3 top-1/2 -translate-y-1/2 text-lsc-dark/70 dark:text-lsc-cream/70 font-medium">
                      $
                    </span>
                    <input
                      id="payment-amount"
                      type="number"
                      step="0.01"
                      min="0"
                      value={paymentAmount}
                      onChange={(e) => setPaymentAmount(e.target.value)}
                      className="w-full pl-8 pr-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                      placeholder={t('placeholder.staff.000')}
                      required
                      aria-required="true"
                    />
                  </div>
                  <button
                    type="button"
                    onClick={handlePayFull}
                    className="px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white text-sm font-medium rounded-xl transition-colors whitespace-nowrap"
                  >
                    Full Amount
                  </button>
                </div>
              </div>

              <div>
                <label htmlFor="payment-method" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-2">
                  Payment Method <span className="text-status-danger-600">*</span>
                </label>
                <select
                  id="payment-method"
                  value={paymentMethod}
                  onChange={(e) => setPaymentMethod(e.target.value as PaymentMethod)}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                  required
                  aria-required="true"
                >
                  {PAYMENT_METHODS.map((method) => (
                    <option key={method} value={method}>
                      {method.charAt(0).toUpperCase() + method.slice(1)}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label htmlFor="notes" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-2">
                  Notes (optional)
                </label>
                <textarea
                  id="notes"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent resize-none"
                  rows={2}
                  placeholder={t('components.staff.finePayment.paymentReferenceCheckNumberEtc')}
                />
              </div>

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
                  disabled={isProcessing}
                  className="flex-1 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 disabled:bg-lsc-rose/50 text-white rounded-xl transition-colors flex items-center justify-center gap-2"
                >
                  {isProcessing ? (
                    <>
                      <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
                      Processing...
                    </>
                  ) : (
                    'Record Payment'
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

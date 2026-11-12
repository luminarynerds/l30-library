/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * QuickCheckoutModal Component
 *
 * A modal for quickly checking out items to a patron.
 * Allows barcode entry and immediate checkout without navigating away.
 */

import { useState, useRef, useEffect } from 'react'
import { ShoppingCart, Loader2, CheckCircle, AlertTriangle, Barcode } from 'lucide-react'
import { staffCheckoutItem } from '@/api/staff-api'
import type { Patron } from '@/api/staff-api'
import toast from 'react-hot-toast'
import { Modal } from '../ui/Modal'
import { useTranslation} from '@/i18n'

// ==================== Types ====================

interface QuickCheckoutModalProps {
  isOpen: boolean
  patron: Patron | null
  token: string | null
  onClose: () => void
  onCheckoutComplete: () => void
}

interface CheckoutResult {
  success: boolean
  itemTitle?: string
  error?: string
}

// ==================== Component ====================

export default function QuickCheckoutModal({
  isOpen,
  patron,
  token,
  onClose,
  onCheckoutComplete,
}: QuickCheckoutModalProps): React.ReactElement | null {
  const { t } = useTranslation()
  const [barcode, setBarcode] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [recentCheckouts, setRecentCheckouts] = useState<CheckoutResult[]>([])
  const inputRef = useRef<HTMLInputElement>(null)
  const previousActiveElement = useRef<HTMLElement | null>(null)

  // Store and restore focus
  useEffect(() => {
    if (isOpen) {
      previousActiveElement.current = document.activeElement as HTMLElement
      const timer = setTimeout(() => {
        inputRef.current?.focus()
      }, 100)
      return () => clearTimeout(timer)
    } else {
      // Reset state when closing
      setBarcode('')
      setRecentCheckouts([])
      if (previousActiveElement.current) {
        previousActiveElement.current.focus()
      }
    }
  }, [isOpen])

  // Handle checkout submission
  const handleCheckout = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!token || !patron || !barcode.trim() || isLoading) return

    setIsLoading(true)
    try {
      const checkout = await staffCheckoutItem(token, patron.id, barcode.trim())
      const result: CheckoutResult = {
        success: true,
        itemTitle: checkout.item_title || barcode.trim(),
      }
      setRecentCheckouts(prev => [result, ...prev].slice(0, 5))
      setBarcode('')
      toast.success(t('toast.checkoutSuccess', { itemTitle: result.itemTitle }))
      onCheckoutComplete()
      // Focus back to input for next scan
      inputRef.current?.focus()
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : 'Checkout failed'
      const result: CheckoutResult = {
        success: false,
        itemTitle: barcode.trim(),
        error: errorMessage,
      }
      setRecentCheckouts(prev => [result, ...prev].slice(0, 5))
      toast.error(errorMessage)
    } finally {
      setIsLoading(false)
    }
  }

  if (!isOpen || !patron) return null

  const modalTitle = `Quick Checkout - ${patron.first_name} ${patron.last_name}`

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={modalTitle}
      size="md"
    >
      {/* Content */}
      <div>
              {/* Patron Info */}
              <div className="mb-4 p-3 bg-lsc-cream/50 dark:bg-lsc-brown/30 rounded-xl">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Library Card:</span>
                  <span className="font-mono text-lsc-dark dark:text-lsc-cream">
                    {patron.library_card || 'N/A'}
                  </span>
                </div>
                <div className="flex items-center justify-between text-sm mt-1">
                  <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Current Checkouts:</span>
                  <span className="text-lsc-dark dark:text-lsc-cream">
                    {patron.current_checkouts || 0}
                  </span>
                </div>
                {(patron.fines_balance ?? 0) > 0 && (
                  <div className="flex items-center justify-between text-sm mt-1">
                    <span className="text-lsc-rose dark:text-lsc-rose-light">Outstanding Fines:</span>
                    <span className="font-medium text-lsc-rose dark:text-lsc-rose-light">
                      ${(patron.fines_balance ?? 0).toFixed(2)}
                    </span>
                  </div>
                )}
              </div>

              {/* Barcode Input Form */}
              <form onSubmit={handleCheckout} className="mb-4">
                <label
                  htmlFor="checkout-barcode"
                  className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2"
                >
                  Scan or enter item barcode
                </label>
                <div className="relative">
                  <Barcode className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" aria-hidden="true" />
                  <input
                    ref={inputRef}
                    id="checkout-barcode"
                    type="text"
                    value={barcode}
                    onChange={(e) => setBarcode(e.target.value)}
                    placeholder={t('placeholder.staff.enterBarcode')}
                    autoComplete="off"
                    disabled={isLoading}
                    className="w-full pl-10 pr-4 py-3 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent disabled:opacity-50"
                  />
                </div>
                <button
                  type="submit"
                  disabled={!barcode.trim() || isLoading}
                  className="mt-3 w-full flex items-center justify-center gap-2 px-4 py-3 bg-lsc-rose hover:bg-lsc-rose/90 disabled:bg-lsc-rose/50 text-white rounded-xl font-medium transition-colors disabled:cursor-not-allowed"
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="w-5 h-5 motion-safe:animate-spin" aria-hidden="true" />
                      <span>Processing...</span>
                    </>
                  ) : (
                    <>
                      <ShoppingCart className="w-5 h-5" aria-hidden="true" />
                      <span>Check Out Item</span>
                    </>
                  )}
                </button>
              </form>

              {/* Recent Checkouts */}
              {recentCheckouts.length > 0 && (
                <div>
                  <h3 className="text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
                    Recent
                  </h3>
                  <div className="space-y-2 max-h-40 overflow-y-auto">
                    {recentCheckouts.map((result, index) => (
                      <div
                        key={index}
                        className={`flex items-center gap-2 p-2 rounded-lg text-sm ${
                          result.success
                            ? 'bg-status-success-50 dark:bg-status-success-900/20 text-status-success-800 dark:text-status-success-200'
                            : 'bg-status-danger-50 dark:bg-status-danger-900/20 text-status-danger-800 dark:text-status-danger-200'
                        }`}
                      >
                        {result.success ? (
                          <CheckCircle className="w-4 h-4 flex-shrink-0" aria-hidden="true" />
                        ) : (
                          <AlertTriangle className="w-4 h-4 flex-shrink-0" aria-hidden="true" />
                        )}
                        <span className="truncate" title={result.success
                            ? result.itemTitle
                            : `${result.itemTitle}: ${result.error}`}>
                          {result.success
                            ? result.itemTitle
                            : `${result.itemTitle}: ${result.error}`}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

      {/* Footer */}
      <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 text-center pt-4 border-t border-lsc-border dark:border-earth-700">
        <p>{t('components.staff.quickCheckout.tipAfterCheckoutFocusReturns')}</p>
      </div>
    </Modal>
  )
}

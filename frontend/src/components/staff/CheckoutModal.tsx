/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useRef } from 'react'
import { X, Loader2 } from 'lucide-react'
import FocusTrap from 'focus-trap-react'
import toast from 'react-hot-toast'
import { useTranslation } from '@/i18n'
import { type Equipment } from '../../api/equipment-api'
import { getEquipmentIcon } from './equipment-utils'

interface CheckoutModalProps {
  equipment: Equipment
  patronId: string
  notes: string
  depositCollected: boolean
  isPending: boolean
  onPatronIdChange: (val: string) => void
  onNotesChange: (val: string) => void
  onDepositChange: (val: boolean) => void
  onSubmit: (equipmentId: number, patronId: number, notes?: string, deposit?: boolean) => void
  onClose: () => void
}

export function CheckoutModal({
  equipment,
  patronId,
  notes,
  depositCollected,
  isPending,
  onPatronIdChange,
  onNotesChange,
  onDepositChange,
  onSubmit,
  onClose,
}: CheckoutModalProps): React.ReactElement {
  const { t } = useTranslation()
  const previousActiveElement = useRef<HTMLElement | null>(null)

  useEffect(() => {
    previousActiveElement.current = document.activeElement as HTMLElement
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = ''
      previousActiveElement.current?.focus()
    }
  }, [])

  return (
    <FocusTrap focusTrapOptions={{ escapeDeactivates: false, allowOutsideClick: true, returnFocusOnDeactivate: false, fallbackFocus: () => document.body }}>
      <div
        className="fixed inset-0 motion-safe:backdrop-blur-md bg-black/50 flex items-center justify-center z-50 p-4"
        role="presentation"
        onKeyDown={(e) => { if (e.key === 'Escape') onClose() }}
      >
      <div
        className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg w-full max-w-md"
        role="dialog"
        aria-modal="true"
        aria-labelledby="checkout-modal-title"
      >
        <div className="px-6 py-4 border-b border-lsc-border dark:border-earth-700 flex items-center justify-between">
          <h2 id="checkout-modal-title" className="text-xl font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
            Checkout Equipment
          </h2>
          <button
            onClick={onClose}
            className="p-2 text-lsc-dark/70 hover:text-lsc-dark dark:text-lsc-cream/70 dark:hover:text-lsc-cream rounded-lg"
            aria-label={t('aria.authModals.close')}
          >
            <X className="w-5 h-5" aria-hidden="true" />
          </button>
        </div>
        <form
          onSubmit={(e) => {
            e.preventDefault()
            if (!patronId) {
              toast.error(t('staffEquipment.pleaseEnterAPatronId'))
              return
            }
            onSubmit(
              equipment.id,
              parseInt(patronId),
              notes || undefined,
              depositCollected,
            )
          }}
          className="p-6 space-y-4"
        >
          <div className="bg-lsc-cream dark:bg-earth-700/50 rounded-lg p-4">
            <div className="flex items-center gap-3">
              {getEquipmentIcon(equipment.equipment_type)}
              <div>
                <p className="font-medium text-lsc-dark dark:text-lsc-cream">{equipment.name}</p>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{equipment.barcode}</p>
              </div>
            </div>
          </div>
          <div>
            <label htmlFor="checkout-patron-id" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Patron ID *</label>
            <input
              id="checkout-patron-id"
              type="number"
              value={patronId}
              onChange={(e) => onPatronIdChange(e.target.value)}
              className="w-full px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
              required
            />
          </div>
          <div>
            <label htmlFor="checkout-notes" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Notes</label>
            <textarea
              id="checkout-notes"
              value={notes}
              onChange={(e) => onNotesChange(e.target.value)}
              rows={2}
              className="w-full px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream resize-none"
            />
          </div>
          {equipment.deposit_required && Number(equipment.deposit_required) > 0 && (
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={depositCollected}
                onChange={(e) => onDepositChange(e.target.checked)}
                className="rounded border-lsc-border"
              />
              <span className="text-sm text-lsc-dark dark:text-lsc-cream">
                Deposit collected (${equipment.deposit_required})
              </span>
            </label>
          )}
          <div className="flex justify-end gap-3 pt-4 border-t border-lsc-border dark:border-earth-700">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-lg"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isPending}
              className="px-4 py-2 bg-status-success-600 hover:bg-status-success-700 text-white rounded-lg font-medium flex items-center gap-2"
            >
              {isPending && <Loader2 className="w-4 h-4 motion-safe:animate-spin" />}
              Checkout
            </button>
          </div>
        </form>
      </div>
      </div>
    </FocusTrap>
  )
}

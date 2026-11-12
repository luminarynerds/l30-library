/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { ShoppingCart, X } from "lucide-react"
import { useState } from "react"
import { useTranslation } from "@/i18n"
import type { Fund, Vendor } from "./types"
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

interface Props {
  selectedCount: number
  vendors: Vendor[]
  funds: Fund[]
  onClose: () => void
  onConfirm: (vendorId: number, fundId: number) => Promise<void>
  formatMoney: (n: number) => string
}

export default function CreatePOModal({ selectedCount, vendors, funds, onClose, onConfirm, formatMoney }: Props) {
  const { t } = useTranslation()
  const [vendorId, setVendorId] = useState<number>(vendors[0]?.id || 0)
  const [fundId, setFundId] = useState<number>(funds[0]?.id || 0)

  const handleConfirm = () => {
    if (vendorId === 0 || fundId === 0) return
    void onConfirm(vendorId, fundId)
  }

  const selectClass =
    "w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"

  return (
    <ModalBackdrop onClose={onClose} title="Create Purchase Order">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg w-full max-w-md">
        <div className="px-6 py-4 border-b border-lsc-border dark:border-earth-700 flex items-center justify-between">
          <h2 className="text-xl font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
            Create Purchase Order
          </h2>
          <button
            onClick={onClose}
            className="p-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark rounded-xl"
            aria-label={t('aria.authModals.close')}
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="p-6 space-y-4">
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
            Creating PO from {selectedCount} upcoming release{selectedCount !== 1 ? "s" : ""}
          </p>
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1">Vendor *</label>
            <select value={vendorId} onChange={(e) => setVendorId(parseInt(e.target.value))} className={selectClass}>
              <option value={0}>Select vendor...</option>
              {vendors.map((v) => (
                <option key={v.id} value={v.id}>
                  {v.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1">Fund *</label>
            <select value={fundId} onChange={(e) => setFundId(parseInt(e.target.value))} className={selectClass}>
              <option value={0}>Select fund...</option>
              {funds.map((f) => (
                <option key={f.id} value={f.id}>
                  {f.name} (Available: {formatMoney(f.available_amount)})
                </option>
              ))}
            </select>
          </div>
          <div className="flex justify-end gap-3 pt-4 border-t border-lsc-border dark:border-earth-700">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-lsc-brown rounded-xl font-medium"
            >
              Cancel
            </button>
            <button
              onClick={handleConfirm}
              disabled={vendorId === 0 || fundId === 0}
              className="px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              <ShoppingCart className="w-4 h-4" />
              Create PO
            </button>
          </div>
        </div>
      </div>
    </ModalBackdrop>
  )
}

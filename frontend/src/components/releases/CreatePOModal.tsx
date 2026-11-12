/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { X, ShoppingCart, Loader2 } from 'lucide-react'
import type { Vendor, Fund } from '../../api/acquisition-api'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

interface CreatePOModalProps {
  selectedCount: number
  vendors: Vendor[]
  funds: Fund[]
  selectedVendor: number
  selectedFund: number
  useExistingDraft: boolean
  isSubmitting: boolean
  onClose: () => void
  onSubmit: () => void
  onVendorChange: (id: number) => void
  onFundChange: (id: number) => void
  onUseExistingDraftChange: (v: boolean) => void
}

export function CreatePOModal({
  selectedCount,
  vendors,
  funds,
  selectedVendor,
  selectedFund,
  useExistingDraft,
  isSubmitting,
  onClose,
  onSubmit,
  onVendorChange,
  onFundChange,
  onUseExistingDraftChange,
}: CreatePOModalProps): React.ReactElement {
  return (
    <ModalBackdrop onClose={onClose} title="Create Purchase Order">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg w-full max-w-md">
        <div className="flex items-center justify-between p-4 border-b border-lsc-border dark:border-earth-700">
          <h2 className="text-lg font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
            Create Purchase Order
          </h2>
          <button
            onClick={onClose}
            className="p-1 hover:bg-lsc-cream dark:hover:bg-lsc-brown rounded-full"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="p-6 space-y-4">
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
            Creating a purchase order for <strong>{selectedCount}</strong> selected releases.
          </p>
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
              Vendor *
            </label>
            <select
              value={selectedVendor}
              onChange={(e) => onVendorChange(parseInt(e.target.value))}
              className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
            >
              <option value={0}>Select a vendor...</option>
              {vendors.map((v) => (
                <option key={v.id} value={v.id}>
                  {v.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
              Fund *
            </label>
            <select
              value={selectedFund}
              onChange={(e) => onFundChange(parseInt(e.target.value))}
              className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
            >
              <option value={0}>Select a fund...</option>
              {funds.map((f) => (
                <option key={f.id} value={f.id}>
                  {f.name} (${(f.current_balance ?? 0).toLocaleString()} available)
                </option>
              ))}
            </select>
          </div>
          <label className="flex items-center gap-2 text-sm text-lsc-dark dark:text-lsc-cream">
            <input
              type="checkbox"
              checked={useExistingDraft}
              onChange={(e) => onUseExistingDraftChange(e.target.checked)}
              className="rounded border-lsc-border"
            />
            Add to existing draft PO if available
          </label>
          <div className="flex justify-end gap-3 pt-4 border-t border-lsc-border dark:border-earth-700">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-lsc-brown rounded-xl disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              onClick={onSubmit}
              disabled={isSubmitting || !selectedVendor || !selectedFund}
              className="px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl flex items-center gap-2 disabled:opacity-50"
            >
              {isSubmitting ? (
                <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
              ) : (
                <ShoppingCart className="w-4 h-4" />
              )}
              {isSubmitting ? 'Creating...' : 'Create PO'}
            </button>
          </div>
        </div>
      </div>
    </ModalBackdrop>
  )
}

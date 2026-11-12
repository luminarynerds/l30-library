/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React from "react"
import { Loader2, Check } from "lucide-react"
import { ITEM_STATUSES } from "./constants"
import { t } from '@/i18n'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

interface BulkActionModalProps {
  modal: {
    type: 'status' | 'location'
    ids: number[]
  }
  value: string
  onChange: (value: string) => void
  onSubmit: () => void
  onCancel: () => void
  isUpdating: boolean
}

const BulkActionModal: React.FC<BulkActionModalProps> = ({
  modal,
  value,
  onChange,
  onSubmit,
  onCancel,
  isUpdating,
}) => {
  return (
    <ModalBackdrop onClose={onCancel} title="Dialog">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-md w-full p-6">
        <h2 className="text-lg font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">
          {modal.type === 'status' ? 'Change Status' : 'Change Location'}
        </h2>
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
          Updating {modal.ids.length} selected item{modal.ids.length !== 1 ? 's' : ''}
        </p>

        {modal.type === 'status' ? (
          <div>
            <label htmlFor="bulk-status" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
              New Status
            </label>
            <select
              id="bulk-status"
              value={value}
              onChange={(e) => onChange(e.target.value)}
              className="w-full px-4 py-2.5 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
              autoFocus
            >
              <option value="">Select a status...</option>
              {ITEM_STATUSES.map((s) => (
                <option key={s.value} value={s.value}>{s.label}</option>
              ))}
            </select>
          </div>
        ) : (
          <div>
            <label htmlFor="bulk-location" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
              New Location
            </label>
            <input
              id="bulk-location"
              type="text"
              value={value}
              onChange={(e) => onChange(e.target.value)}
              placeholder={t('placeholder.bulkActionModal.egMainLibraryChildrens')}
              className="w-full px-4 py-2.5 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
              maxLength={100}
              autoFocus
            />
          </div>
        )}

        <div className="flex gap-3 justify-end mt-6">
          <button
            onClick={onCancel}
            className="px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream/80 hover:bg-lsc-cream dark:hover:bg-lsc-brown font-medium transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={onSubmit}
            disabled={!value.trim() || isUpdating}
            className="px-4 py-2 rounded-xl bg-lsc-rose hover:bg-lsc-rose/90 disabled:opacity-50 text-white font-medium flex items-center gap-2 transition-colors"
          >
            {isUpdating ? <Loader2 className="w-4 h-4 motion-safe:animate-spin" /> : <Check className="w-4 h-4" />}
            Apply
          </button>
        </div>
      </div>
    </ModalBackdrop>
  )
}

export default BulkActionModal

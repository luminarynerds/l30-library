/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { X } from 'lucide-react'
import { useTranslation } from '@/i18n'
import type { PartnerStatus, BulkActionType } from './outreach-types'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

interface Props {
  bulkActionType: BulkActionType
  selectedPartners: number[]
  selectedVisits: number[]
  selectedCheckouts: number[]
  selectedDeposits: number[]
  newPartnerStatus: PartnerStatus
  setNewPartnerStatus: (s: PartnerStatus) => void
  cancellationReason: string
  setCancellationReason: (r: string) => void
  extensionDays: number
  setExtensionDays: (d: number) => void
  forfeitReason: string
  setForfeitReason: (r: string) => void
  isPending: boolean
  onConfirm: () => void
  onClose: () => void
}

export function BulkActionModal({
  bulkActionType, selectedPartners, selectedVisits, selectedCheckouts, selectedDeposits,
  newPartnerStatus, setNewPartnerStatus, cancellationReason, setCancellationReason,
  extensionDays, setExtensionDays, forfeitReason, setForfeitReason,
  isPending, onConfirm, onClose,
}: Props) {
  const { t } = useTranslation()
  const title = {
    partner_status: 'Update Partner Status',
    cancel_visits: 'Cancel Visits',
    extend_due: 'Extend Due Dates',
    forfeit_deposits: 'Forfeit Deposits',
  }[bulkActionType]

  return (
    <ModalBackdrop onClose={onClose} title="Update Partner Status">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-md w-full">
        <div className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream">{title}</h2>
            <button onClick={onClose} className="text-lsc-dark/70 hover:text-lsc-dark dark:text-lsc-cream/70 dark:hover:text-lsc-cream">
              <X className="w-5 h-5" />
            </button>
          </div>

          <div className="space-y-4">
            {bulkActionType === "partner_status" && (
              <>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                  Update status for {selectedPartners.length} partner(s)
                </p>
                <select
                  value={newPartnerStatus}
                  onChange={(e) => setNewPartnerStatus(e.target.value as PartnerStatus)}
                  className="w-full px-3 py-2 bg-lsc-white dark:bg-earth-700 border border-lsc-border dark:border-earth-700 rounded-lg text-lsc-dark dark:text-lsc-cream"
                >
                  <option value="active">Active</option>
                  <option value="inactive">Inactive</option>
                  <option value="pending">Pending</option>
                  <option value="suspended">Suspended</option>
                </select>
              </>
            )}

            {bulkActionType === "cancel_visits" && (
              <>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                  Cancel {selectedVisits.length} visit(s)
                </p>
                <textarea
                  value={cancellationReason}
                  onChange={(e) => setCancellationReason(e.target.value)}
                  placeholder={t('placeholder.staffOutreach.cancellationReason')}
                  rows={3}
                  className="w-full px-3 py-2 bg-lsc-white dark:bg-earth-700 border border-lsc-border dark:border-earth-700 rounded-lg text-lsc-dark dark:text-lsc-cream"
                />
              </>
            )}

            {bulkActionType === "extend_due" && (
              <>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                  Extend due dates for {selectedCheckouts.length} checkout(s)
                </p>
                <div>
                  <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                    Extension Days (1-90)
                  </label>
                  <input
                    type="number"
                    min={1}
                    max={90}
                    value={extensionDays}
                    onChange={(e) => setExtensionDays(Number(e.target.value))}
                    className="w-full px-3 py-2 bg-lsc-white dark:bg-earth-700 border border-lsc-border dark:border-earth-700 rounded-lg text-lsc-dark dark:text-lsc-cream"
                  />
                </div>
              </>
            )}

            {bulkActionType === "forfeit_deposits" && (
              <>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                  Forfeit {selectedDeposits.length} deposit(s)
                </p>
                <textarea
                  value={forfeitReason}
                  onChange={(e) => setForfeitReason(e.target.value)}
                  placeholder={t('placeholder.staffOutreach.reasonForForfeiture')}
                  rows={3}
                  className="w-full px-3 py-2 bg-lsc-white dark:bg-earth-700 border border-lsc-border dark:border-earth-700 rounded-lg text-lsc-dark dark:text-lsc-cream"
                />
              </>
            )}
          </div>

          <div className="flex justify-end gap-3 mt-6">
            <button onClick={onClose} className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70">
              Cancel
            </button>
            <button
              onClick={onConfirm}
              disabled={isPending}
              className="px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg"
            >
              Confirm
            </button>
          </div>
        </div>
      </div>
    </ModalBackdrop>
  )
}

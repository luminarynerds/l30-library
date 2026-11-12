/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { X, AlertCircle } from 'lucide-react'
import { useTranslation } from '@/i18n'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

interface RejectPOModalProps {
  isOpen: boolean
  onClose: () => void
  onConfirm: (notes: string) => void
  poNumber: string
}

export default function RejectPOModal({
  isOpen,
  onClose,
  onConfirm,
  poNumber
}: RejectPOModalProps) {
  const { t } = useTranslation()
  const [notes, setNotes] = useState('')
  
  const handleConfirm = () => {
    if (!notes.trim()) {
      return
    }
    onConfirm(notes)
    setNotes('')
  }
  
  const handleClose = () => {
    setNotes('')
    onClose()
  }
  
  if (!isOpen) return null
  
  return (
    <ModalBackdrop onClose={handleClose} title="Reject Purchase Order">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-md w-full">
        {/* Header */}
        <div className="bg-status-danger-50 dark:bg-status-danger-900/20 border-b border-status-danger-200 dark:border-status-danger-800 p-6 flex items-center justify-between rounded-t-2xl">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-status-danger-100 dark:bg-status-danger-900/30 rounded-full">
              <AlertCircle className="w-6 h-6 text-status-danger-600 dark:text-status-danger-400" />
            </div>
            <div>
              <h2 className="text-xl font-serif font-bold text-status-danger-900 dark:text-status-danger-200">
                Reject Purchase Order
              </h2>
              <p className="text-sm text-status-danger-700 dark:text-status-danger-300">
                {poNumber}
              </p>
            </div>
          </div>
          <button
            onClick={handleClose}
            className="p-2 hover:bg-status-danger-100 dark:bg-status-danger-900/30 dark:hover:bg-status-danger-900/30 rounded-full transition-colors"
          >
            <X className="w-5 h-5 text-status-danger-600 dark:text-status-danger-400" />
          </button>
        </div>
        
        {/* Body */}
        <div className="p-6">
          <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-2">
            Rejection Notes *
          </label>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder={t('components.acquisition.rejectPO.pleaseProvideAReasonFor')}
            rows={4}
            className="w-full px-4 py-3 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-status-danger-500"
            autoFocus
          />
          <p className="mt-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
            The staff member will receive an email with these rejection notes.
          </p>
        </div>
        
        {/* Footer */}
        <div className="bg-lsc-cream dark:bg-lsc-dark/30 p-6 flex items-center justify-end gap-3 rounded-b-2xl">
          <button
            onClick={handleClose}
            className="px-6 py-2 bg-lsc-cream hover:bg-lsc-border dark:bg-lsc-brown dark:hover:bg-earth-600 text-lsc-dark dark:text-lsc-cream rounded-xl font-medium transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleConfirm}
            disabled={!notes.trim()}
            className="px-6 py-2 bg-status-danger-600 hover:bg-status-danger-700 text-white rounded-xl font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Reject Purchase Order
          </button>
        </div>
      </div>
    </ModalBackdrop>
  )
}

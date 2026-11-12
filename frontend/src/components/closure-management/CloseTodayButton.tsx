/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React, { useState } from 'react'
import { AlertCircle, AlertTriangle } from 'lucide-react'
import { createBranchClosure, type BranchClosure } from '../../api/branch-api'
import { useTranslation} from '@/i18n'
import { clean } from '@/lib/utils'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

interface CloseTodayButtonProps {
  branchId: number
  onSuccess?: (closure: BranchClosure) => void
  onError?: (error: string) => void
}

export const CloseTodayButton: React.FC<CloseTodayButtonProps> = ({
  branchId,
  onSuccess,
  onError,
}) => {
  const { t } = useTranslation()
  const [isOpen, setIsOpen] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [reason, setReason] = useState('')
  const [documentation, setDocumentation] = useState('')
  const [sendNotifications, setSendNotifications] = useState(true)
  const [cancelEvents, setCancelEvents] = useState(true)
  const [updateServices, setUpdateServices] = useState(true)

  const handleSubmit = async () => {
    if (!reason.trim()) {
      onError?.('Please provide a reason for closure')
      return
    }

    setIsLoading(true)
    try {
      const today = new Date().toISOString().split('T')[0] ?? ''
      const closure = await createBranchClosure(branchId, clean({
        start_date: today,
        end_date: today,
        reason,
        description: documentation || undefined,
        is_system_wide: false,
        is_annual: false,
      }))

      onSuccess?.(closure)
      setIsOpen(false)
      setReason('')
      setDocumentation('')
    } catch (err: unknown) {
      onError?.(
        err instanceof Error ? err.message : 'Failed to close branch'
      )
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <>
      <button
        onClick={() => setIsOpen(true)}
        className="flex items-center gap-2 px-4 py-2 bg-status-danger-600 hover:bg-status-danger-700 text-white rounded font-medium transition"
      >
        <AlertCircle className="w-5 h-5" />
        Close Today
      </button>

      {isOpen && (
        <ModalBackdrop onClose={() => setIsOpen(false)} title="Close Branch Today" role="alertdialog">
          <div className="bg-lsc-white dark:bg-earth-800 rounded-lg max-w-md w-full">
            {/* Header */}
            <div className="bg-status-danger-600 text-white p-6">
              <div className="flex items-center gap-2 mb-2">
                <AlertTriangle className="w-6 h-6" />
                <h2 className="font-serif text-xl font-bold">Close Branch Today</h2>
              </div>
              <p className="text-status-danger-100 text-sm">
                This action will immediately close the branch for today and notify
                patrons and staff.
              </p>
            </div>

            {/* Content */}
            <div className="p-6 space-y-4">
              <div>
                <label htmlFor="close-today-reason" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
                  Reason for Closure *
                </label>
                <input
                  id="close-today-reason"
                  type="text"
                  aria-required="true"
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  placeholder={t('placeholder.closure-management.egEmergencyEquipmentFailure')}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded focus:outline-none focus:ring-2 focus:ring-status-danger-500 dark:bg-earth-700 dark:text-lsc-cream"
                  disabled={isLoading}
                />
              </div>

              <div>
                <label htmlFor="close-today-documentation" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
                  Additional Documentation
                </label>
                <textarea
                  id="close-today-documentation"
                  value={documentation}
                  onChange={(e) => setDocumentation(e.target.value)}
                  placeholder={t('components.closureManagement.closeTodayButton.detailedExplanationOfTheClosure')}
                  rows={3}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded focus:outline-none focus:ring-2 focus:ring-status-danger-500 dark:bg-earth-700 dark:text-lsc-cream"
                  disabled={isLoading}
                />
              </div>

              <div className="space-y-2">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={sendNotifications}
                    onChange={(e) => setSendNotifications(e.target.checked)}
                    disabled={isLoading}
                    className="w-4 h-4 rounded border-lsc-border dark:border-earth-700"
                  />
                  <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                    Send notifications to patrons and staff
                  </span>
                </label>

                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={cancelEvents}
                    onChange={(e) => setCancelEvents(e.target.checked)}
                    disabled={isLoading}
                    className="w-4 h-4 rounded border-lsc-border dark:border-earth-700"
                  />
                  <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                    Cancel today's events
                  </span>
                </label>

                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={updateServices}
                    onChange={(e) => setUpdateServices(e.target.checked)}
                    disabled={isLoading}
                    className="w-4 h-4 rounded border-lsc-border dark:border-earth-700"
                  />
                  <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                    Update external services (website, maps, etc.)
                  </span>
                </label>
              </div>
            </div>

            {/* Footer */}
            <div className="bg-earth-50 dark:bg-earth-900 border-t border-lsc-border dark:border-earth-700 p-6 flex justify-end gap-4">
              <button
                onClick={() => setIsOpen(false)}
                disabled={isLoading}
                className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70 bg-earth-100 dark:bg-earth-700 hover:bg-earth-200 dark:hover:bg-earth-600 rounded font-medium transition disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleSubmit}
                disabled={isLoading || !reason.trim()}
                className="px-4 py-2 bg-status-danger-600 hover:bg-status-danger-700 text-white rounded font-medium transition disabled:opacity-50"
              >
                {isLoading ? 'Closing...' : 'Close Today'}
              </button>
            </div>
          </div>
        </ModalBackdrop>
      )}
    </>
  )
}

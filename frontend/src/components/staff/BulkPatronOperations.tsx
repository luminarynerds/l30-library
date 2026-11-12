/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/* eslint-disable react-hooks/exhaustive-deps */
/* eslint-disable react-refresh/only-export-components */
/**
 * BulkPatronOperations Component
 *
 * Provides bulk operations specific to patron management:
 * - Bulk block/unblock patrons
 * - Bulk waive fines
 * - Bulk send notifications
 * - Bulk update patron status
 * - Bulk export patrons
 */

import { useState, useCallback, useMemo, useEffect, useRef } from 'react'
import FocusTrap from 'focus-trap-react'
import {
  Ban,
  CheckCircle,
  DollarSign,
  Bell,
  Download,
  Mail,
  AlertTriangle,
} from 'lucide-react'
import toast from 'react-hot-toast'
import BulkOperationsPanel, {
  type BulkAction,
  type BulkOperationResult,
  useBulkSelection,
} from './BulkOperationsPanel'
import {
  bulkBlockPatrons,
  bulkWaiveFines,
  bulkSendNotification,
  exportPatrons,
  type Patron,
  type BulkBlockResponse,
  type BulkWaiveFinesResponse,
  type BulkNotificationResponse,
} from '@/api/staff-api'
import { useTranslation} from '@/i18n'

// ==================== Types ====================

interface BulkPatronOperationsProps {
  /** List of patrons currently displayed */
  patrons: Patron[]
  /** All patron IDs in the current filtered list */
  allPatronIds: number[]
  /** Auth token */
  token: string
  /** Callback when operations complete (to refresh data) */
  onOperationComplete?: () => void
  /** Optional: Custom class name */
  className?: string
  /** Optional: Compact mode */
  compact?: boolean
}

interface NotificationFormData {
  subject: string
  message: string
  notificationType: 'general' | 'reminder' | 'alert'
}

// ==================== Component ====================

export default function BulkPatronOperations({
  patrons,
  allPatronIds,
  token,
  onOperationComplete,
  className = '',
  compact = false,
}: BulkPatronOperationsProps): React.ReactElement {
  const { t } = useTranslation()
  // Selection state
  const {
    selectedIds,
    setSelectedIds,
    selectedCount,
  } = useBulkSelection()

  // Modal states
  const [showNotificationModal, setShowNotificationModal] = useState(false)
  const [showWaiveFinesModal, setShowWaiveFinesModal] = useState(false)
  const [notificationData, setNotificationData] = useState<NotificationFormData>({
    subject: '',
    message: '',
    notificationType: 'general',
  })
  const [waiveFinesReason, setWaiveFinesReason] = useState('')
  const [lastResult, setLastResult] = useState<BulkOperationResult | null>(null)

  // Refs to store Promise resolvers for modal-based actions so the
  // BulkOperationsPanel can await the actual operation result.
  const waiveFinesResolverRef = useRef<((result: BulkOperationResult) => void) | null>(null)
  const notificationResolverRef = useRef<((result: BulkOperationResult) => void) | null>(null)

  // Get page patron IDs
  const pagePatronIds = useMemo(() => patrons.map(p => p.id), [patrons])

  // Get selected patrons info
  const selectedPatrons = useMemo(() => {
    return patrons.filter(p => selectedIds.includes(p.id))
  }, [patrons, selectedIds])

  // Count active/blocked in selection
  const activeCount = useMemo(() => {
    return selectedPatrons.filter(p => p.is_active).length
  }, [selectedPatrons])

  const blockedCount = useMemo(() => {
    return selectedPatrons.filter(p => !p.is_active).length
  }, [selectedPatrons])

  // Bulk block patrons
  const handleBulkBlock = useCallback(async (ids: number[]): Promise<BulkOperationResult<BulkBlockResponse>> => {
    try {
      const result = await bulkBlockPatrons(token, {
        patron_ids: ids,
        blocked: true,
        reason: 'Bulk operation by staff',
      })

      const opResult: BulkOperationResult<BulkBlockResponse> = {
        success: result.success,
        successCount: result.processed_count,
        failureCount: result.failed_ids.length,
        message: result.message,
        failedIds: result.failed_ids,
        details: result,
      }

      if (result.success) {
        toast.success(result.message)
        onOperationComplete?.()
      }

      setLastResult(opResult)
      return opResult
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to block patrons'
      toast.error(message)
      throw error
    }
  }, [token, onOperationComplete])

  // Bulk unblock patrons
  const handleBulkUnblock = useCallback(async (ids: number[]): Promise<BulkOperationResult<BulkBlockResponse>> => {
    try {
      const result = await bulkBlockPatrons(token, {
        patron_ids: ids,
        blocked: false,
      })

      const opResult: BulkOperationResult<BulkBlockResponse> = {
        success: result.success,
        successCount: result.processed_count,
        failureCount: result.failed_ids.length,
        message: result.message,
        failedIds: result.failed_ids,
        details: result,
      }

      if (result.success) {
        toast.success(result.message)
        onOperationComplete?.()
      }

      setLastResult(opResult)
      return opResult
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to unblock patrons'
      toast.error(message)
      throw error
    }
  }, [token, onOperationComplete])

  // Bulk waive fines
  const handleBulkWaiveFines = useCallback(async (ids: number[]): Promise<BulkOperationResult<BulkWaiveFinesResponse>> => {
    try {
      const result = await bulkWaiveFines(token, {
        patron_ids: ids,
        reason: waiveFinesReason || 'Bulk waiver by staff',
      })

      const opResult: BulkOperationResult<BulkWaiveFinesResponse> = {
        success: result.success,
        successCount: result.patrons_processed,
        failureCount: result.failed_ids.length,
        message: result.message,
        failedIds: result.failed_ids,
        details: result,
      }

      if (result.success) {
        toast.success(t('toast.finesWaivedBulk', { count: result.fines_waived, amount: `$${result.total_amount_waived.toFixed(2)}` }))
        onOperationComplete?.()
      }

      setShowWaiveFinesModal(false)
      setWaiveFinesReason('')
      setLastResult(opResult)
      waiveFinesResolverRef.current?.(opResult)
      waiveFinesResolverRef.current = null
      return opResult
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to waive fines'
      toast.error(message)
      const errorResult = {
        success: false,
        successCount: 0,
        failureCount: ids.length,
        message,
      } as BulkOperationResult<BulkWaiveFinesResponse>
      waiveFinesResolverRef.current?.(errorResult)
      waiveFinesResolverRef.current = null
      return errorResult
    }
  }, [token, waiveFinesReason, onOperationComplete])

  // Bulk send notification
  const handleBulkNotify = useCallback(async (ids: number[]): Promise<BulkOperationResult<BulkNotificationResponse>> => {
    if (!notificationData.subject.trim() || !notificationData.message.trim()) {
      throw new Error('Please fill in subject and message')
    }

    try {
      const result = await bulkSendNotification(token, {
        patron_ids: ids,
        subject: notificationData.subject,
        message: notificationData.message,
        notification_type: notificationData.notificationType,
      })

      const opResult: BulkOperationResult<BulkNotificationResponse> = {
        success: result.success,
        successCount: result.sent_count,
        failureCount: result.failed_ids.length,
        message: result.message,
        failedIds: result.failed_ids,
        details: result,
      }

      if (result.success) {
        toast.success(result.message)
        onOperationComplete?.()
      }

      setShowNotificationModal(false)
      setNotificationData({ subject: '', message: '', notificationType: 'general' })
      setLastResult(opResult)
      notificationResolverRef.current?.(opResult)
      notificationResolverRef.current = null
      return opResult
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to send notifications'
      toast.error(message)
      const errorResult = {
        success: false,
        successCount: 0,
        failureCount: ids.length,
        message,
      } as BulkOperationResult<BulkNotificationResponse>
      notificationResolverRef.current?.(errorResult)
      notificationResolverRef.current = null
      return errorResult
    }
  }, [token, notificationData, onOperationComplete])

  // Bulk export
  const handleBulkExport = useCallback(async (ids: number[]): Promise<BulkOperationResult> => {
    try {
      const blob = await exportPatrons(token, {
        patronIds: ids,
        format: 'csv',
      })

      // Handle blob download
      if (blob instanceof Blob) {
        const url = window.URL.createObjectURL(blob)
        const link = document.createElement('a')
        link.href = url
        link.download = `patrons-export-${new Date().toISOString().split('T')[0]}.csv`
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
        window.URL.revokeObjectURL(url)
      }

      const opResult: BulkOperationResult = {
        success: true,
        successCount: ids.length,
        failureCount: 0,
        message: `Exported ${ids.length} patrons to CSV`,
      }

      toast.success(t('toast.patronsExported', { count: ids.length }))
      setLastResult(opResult)
      return opResult
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to export patrons'
      toast.error(message)
      throw error
    }
  }, [token])

  // Track if any modal is open
  const anyModalOpen = showNotificationModal || showWaiveFinesModal

  // Handle Escape key for modals
  useEffect(() => {
    if (!anyModalOpen) return

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault()
        setShowNotificationModal(false)
        setShowWaiveFinesModal(false)
        const cancelResult: BulkOperationResult = { success: true, successCount: 0, failureCount: 0, message: 'Cancelled' }
        waiveFinesResolverRef.current?.(cancelResult)
        waiveFinesResolverRef.current = null
        notificationResolverRef.current?.(cancelResult)
        notificationResolverRef.current = null
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [anyModalOpen])

  // Lock body scroll when any modal is open
  useEffect(() => {
    if (anyModalOpen) {
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = ''
    }
    return () => {
      document.body.style.overflow = ''
    }
  }, [anyModalOpen])

  // Define bulk actions
  const bulkActions: BulkAction[] = useMemo(() => [
    {
      id: 'block',
      label: 'Block Patrons',
      icon: <Ban className="w-4 h-4" />,
      description: t('components.staff.bulkPatronOperations.blockSelectedPatronAccounts'),
      variant: 'danger',
      confirmMessage: (count) => `Are you sure you want to block ${count} patron accounts? They will not be able to check out items or access their accounts.`,
      onExecute: handleBulkBlock,
      disabled: activeCount === 0,
      disabledReason: 'No active patrons selected',
    },
    {
      id: 'unblock',
      label: 'Unblock Patrons',
      icon: <CheckCircle className="w-4 h-4" />,
      description: t('components.staff.bulkPatronOperations.unblockSelectedPatronAccounts'),
      onExecute: handleBulkUnblock,
      confirmMessage: (count) => `Unblock ${count} patron accounts?`,
      disabled: blockedCount === 0,
      disabledReason: 'No blocked patrons selected',
    },
    {
      id: 'waive-fines',
      label: 'Waive All Fines',
      icon: <DollarSign className="w-4 h-4" />,
      description: t('components.staff.bulkPatronOperations.waiveAllOutstandingFinesFor'),
      variant: 'warning',
      onExecute: async () => {
        setShowWaiveFinesModal(true)
        return new Promise<BulkOperationResult>((resolve) => {
          waiveFinesResolverRef.current = resolve
        })
      },
      requiresInput: true,
    },
    {
      id: 'notify',
      label: 'Send Notification',
      icon: <Bell className="w-4 h-4" />,
      description: t('components.staff.bulkPatronOperations.sendANotificationToSelected'),
      onExecute: async () => {
        setShowNotificationModal(true)
        return new Promise<BulkOperationResult>((resolve) => {
          notificationResolverRef.current = resolve
        })
      },
      requiresInput: true,
    },
    {
      id: 'export',
      label: 'Export to CSV',
      icon: <Download className="w-4 h-4" />,
      description: t('components.staff.bulkPatronOperations.exportSelectedPatronDataTo'),
      onExecute: handleBulkExport,
     
     
    },
   
  ], [handleBulkBlock, handleBulkUnblock, handleBulkExport, activeCount, blockedCount])

  return (
    <div className={className}>
      <BulkOperationsPanel
        selectedIds={selectedIds}
        totalItems={allPatronIds.length}
        actions={bulkActions}
        onSelectionChange={setSelectedIds}
        allItemIds={allPatronIds}
        pageItemIds={pagePatronIds}
        itemLabel="patrons"
        {...(lastResult != null ? { lastResult } : {})}
        onResultDismiss={() => setLastResult(null)}
        compact={compact}
      />

      {/* Selection Summary */}
      {selectedCount > 0 && !compact && (
        <div className="mt-3 flex flex-wrap gap-2 text-xs">
          {activeCount > 0 && (
            <span className="px-2 py-1 bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-400 rounded-full">
              {activeCount} active
            </span>
          )}
          {blockedCount > 0 && (
            <span className="px-2 py-1 bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-700 dark:text-status-danger-400 rounded-full">
              {blockedCount} blocked
            </span>
          )}
        </div>
      )}

      {/* Waive Fines Modal */}
      {showWaiveFinesModal && (
        <FocusTrap active={showWaiveFinesModal} focusTrapOptions={{ escapeDeactivates: true }}>
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div
            className="fixed inset-0 bg-black/50 motion-safe:backdrop-blur-md"
            onClick={() => {
              setShowWaiveFinesModal(false)
              setWaiveFinesReason('')
              waiveFinesResolverRef.current?.({ success: true, successCount: 0, failureCount: 0, message: 'Cancelled' })
              waiveFinesResolverRef.current = null
            }}
            aria-hidden="true"
          />
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="waive-fines-title"
            className="relative bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-md w-full p-6"
          >
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 rounded-full bg-status-warning-100 dark:bg-status-warning-900/30">
                <DollarSign className="w-6 h-6 text-status-warning-600 dark:text-status-warning-400" aria-hidden="true" />
              </div>
              <div>
                <h3
                  id="waive-fines-title"
                  className="font-serif text-lg font-bold text-lsc-dark dark:text-lsc-cream"
                >
                  Waive Fines
                </h3>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                  For {selectedCount} selected patrons
                </p>
              </div>
            </div>

            <div className="space-y-4">
              <div>
                <label
                  htmlFor="waive-reason"
                  className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2"
                >
                  Reason for waiving fines
                </label>
                <input
                  id="waive-reason"
                  type="text"
                  value={waiveFinesReason}
                  onChange={(e) => setWaiveFinesReason(e.target.value)}
                  placeholder={t('placeholder.staff.egAmnestyDaySystem')}
                  className="w-full px-3 py-2.5 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                />
              </div>

              <div className="p-3 bg-status-warning-50 dark:bg-status-warning-900/20 rounded-xl">
                <div className="flex items-start gap-2">
                  <AlertTriangle className="w-5 h-5 text-status-warning-600 dark:text-status-warning-400 flex-shrink-0 mt-0.5" aria-hidden="true" />
                  <p className="text-sm text-status-warning-700 dark:text-status-warning-300">
                    This will waive all outstanding fines for the selected patrons. This action cannot be undone.
                  </p>
                </div>
              </div>

              <div className="flex gap-3">
                <button
                  onClick={() => {
                    setShowWaiveFinesModal(false)
                    setWaiveFinesReason('')
                    waiveFinesResolverRef.current?.({ success: true, successCount: 0, failureCount: 0, message: 'Cancelled' })
                    waiveFinesResolverRef.current = null
                  }}
                  className="flex-1 px-4 py-2.5 bg-lsc-cream dark:bg-lsc-brown hover:bg-lsc-border dark:hover:bg-lsc-brown/80 text-lsc-dark dark:text-lsc-cream rounded-xl font-medium transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={() => handleBulkWaiveFines(selectedIds)}
                  className="flex-1 px-4 py-2.5 bg-status-warning-700 hover:bg-status-warning-800 text-white rounded-xl font-medium transition-colors"
                >
                  Waive Fines
                </button>
              </div>
            </div>
          </div>
        </div>
        </FocusTrap>
      )}

      {/* Notification Modal */}
      {showNotificationModal && (
        <FocusTrap active={showNotificationModal} focusTrapOptions={{ escapeDeactivates: true }}>
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div
            className="fixed inset-0 bg-black/50 motion-safe:backdrop-blur-md"
            onClick={() => {
              setShowNotificationModal(false)
              setNotificationData({ subject: '', message: '', notificationType: 'general' })
              notificationResolverRef.current?.({ success: true, successCount: 0, failureCount: 0, message: 'Cancelled' })
              notificationResolverRef.current = null
            }}
            aria-hidden="true"
          />
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="notification-title"
            className="relative bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-lg w-full p-6"
          >
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 rounded-full bg-earth-100 dark:bg-earth-800/30">
                <Bell className="w-6 h-6 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
              </div>
              <div>
                <h3
                  id="notification-title"
                  className="font-serif text-lg font-bold text-lsc-dark dark:text-lsc-cream"
                >
                  Send Notification
                </h3>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                  To {selectedCount} selected patrons
                </p>
              </div>
            </div>

            <div className="space-y-4">
              {/* Notification Type */}
              <div>
                <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
                  Notification Type
                </label>
                <div className="grid grid-cols-3 gap-2">
                  {(['general', 'reminder', 'alert'] as const).map((type) => (
                    <button
                      key={type}
                      type="button"
                      onClick={() => setNotificationData(prev => ({ ...prev, notificationType: type }))}
                      className={`px-3 py-2 rounded-xl border text-sm font-medium capitalize transition-colors ${
                        notificationData.notificationType === type
                          ? 'bg-lsc-rose text-white border-lsc-rose'
                          : 'bg-lsc-white dark:bg-lsc-brown border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream hover:border-lsc-rose'
                      }`}
                    >
                      {type}
                    </button>
                  ))}
                </div>
              </div>

              {/* Subject */}
              <div>
                <label
                  htmlFor="notification-subject"
                  className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2"
                >
                  Subject
                </label>
                <input
                  id="notification-subject"
                  type="text"
                  value={notificationData.subject}
                  onChange={(e) => setNotificationData(prev => ({ ...prev, subject: e.target.value }))}
                  placeholder={t('placeholder.staff.notificationSubject')}
                  className="w-full px-3 py-2.5 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                />
              </div>

              {/* Message */}
              <div>
                <label
                  htmlFor="notification-message"
                  className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2"
                >
                  Message
                </label>
                <textarea
                  id="notification-message"
                  value={notificationData.message}
                  onChange={(e) => setNotificationData(prev => ({ ...prev, message: e.target.value }))}
                  placeholder={t('placeholder.staff.enterYourMessage')}
                  rows={4}
                  className="w-full px-3 py-2.5 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent resize-none"
                />
              </div>

              <div className="flex gap-3">
                <button
                  onClick={() => {
                    setShowNotificationModal(false)
                    setNotificationData({ subject: '', message: '', notificationType: 'general' })
                    notificationResolverRef.current?.({ success: true, successCount: 0, failureCount: 0, message: 'Cancelled' })
                    notificationResolverRef.current = null
                  }}
                  className="flex-1 px-4 py-2.5 bg-lsc-cream dark:bg-lsc-brown hover:bg-lsc-border dark:hover:bg-lsc-brown/80 text-lsc-dark dark:text-lsc-cream rounded-xl font-medium transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={() => handleBulkNotify(selectedIds)}
                  disabled={!notificationData.subject.trim() || !notificationData.message.trim()}
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-lsc-rose hover:bg-lsc-rose/90 disabled:bg-lsc-rose/50 text-white rounded-xl font-medium transition-colors disabled:cursor-not-allowed"
                >
                  <Mail className="w-4 h-4" aria-hidden="true" />
                  Send
                </button>
              </div>
            </div>
          </div>
        </div>
        </FocusTrap>
      )}
    </div>
  )
}

// ==================== Export Selection Handler ====================

/**
 * Export helper for integrating with existing patron tables
 */
export { useBulkSelection }

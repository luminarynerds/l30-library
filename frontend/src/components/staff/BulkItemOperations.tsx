/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/* eslint-disable react-hooks/exhaustive-deps */
/* eslint-disable react-refresh/only-export-components */
/**
 * BulkItemOperations Component
 *
 * Provides bulk operations specific to item management (lost/damaged):
 * - Bulk mark items as lost
 * - Bulk write-off lost items
 * - Bulk assign items to mending queue
 * - Bulk update mending priority
 * - Bulk update item status
 */

import { useState, useCallback, useMemo, useEffect, useRef } from 'react'
import FocusTrap from 'focus-trap-react'
import {
  AlertTriangle,
  Trash2,
  Wrench,
  ArrowUpDown,
  FileWarning,
  Users,
} from 'lucide-react'
import toast from 'react-hot-toast'
import type { LostItemClassification } from '@/api/staff-api'
import BulkOperationsPanel, {
  type BulkAction,
  type BulkOperationResult,
  useBulkSelection,
} from './BulkOperationsPanel'
import {
  bulkMarkLost,
  bulkWriteOffLostItems,
  bulkAssignMending,
  bulkUpdateMendingPriority,
  type BulkMarkLostResponse,
  type BulkWriteOffResponse,
  type BulkMendingAssignResponse,
} from '@/api/staff-api'
import { useTranslation} from '@/i18n'

// ==================== Types ====================

export interface LostItem {
  id: number
  checkout_id?: number
  item_copy_id?: number
  catalog_item_id?: number
  patron_id?: number
  status: string
  lost_type?: string
  replacement_cost?: number
  item_title?: string
  patron_name?: string
}

export interface DamagedItem {
  id: number
  item_copy_id?: number
  catalog_item_id?: number
  patron_id?: number
  status: string
  severity?: string
  damage_types?: string[]
  estimated_repair_cost?: number
  item_title?: string
  patron_name?: string
}

export interface MendingQueueItem {
  id: number
  damaged_item_record_id?: number
  item_copy_id?: number
  priority: number
  repair_type?: string
  is_in_progress?: boolean
  is_completed?: boolean
  item_title?: string
  assigned_to_name?: string
}

interface BulkItemOperationsProps {
  /** Type of items being managed */
  itemType: 'lost' | 'damaged' | 'mending'
  /** List of items currently displayed */
  items: (LostItem | DamagedItem | MendingQueueItem)[]
  /** All item IDs in the current filtered list */
  allItemIds: number[]
  /** Auth token */
  token: string
  /** Callback when operations complete (to refresh data) */
  onOperationComplete?: () => void
  /** Optional: Available staff members for assignment */
  staffMembers?: Array<{ id: number; name: string }>
  /** Optional: Available lost item classifications */
  availableClassifications?: LostItemClassification[]
  /** Optional: Custom class name */
  className?: string
  /** Optional: Compact mode */
  compact?: boolean
}

// ==================== Component ====================

export default function BulkItemOperations({
  itemType,
  items,
  allItemIds,
  token,
  onOperationComplete,
  staffMembers = [],
  availableClassifications = [],
  className = '',
  compact = false,
}: BulkItemOperationsProps): React.ReactElement {
  const { t } = useTranslation()
  // Selection state
  const {
    selectedIds,
    setSelectedIds,
    selectedCount,
  } = useBulkSelection()

  // Modal states
  const [showMarkLostModal, setShowMarkLostModal] = useState(false)
  const [showAssignMendingModal, setShowAssignMendingModal] = useState(false)
  const [showPriorityModal, setShowPriorityModal] = useState(false)

  // Form states
  const defaultLostType = availableClassifications.length > 0
    ? availableClassifications[0]!.value
    : 'lost_by_patron'
  const [lostType, setLostType] = useState<string>(defaultLostType)
  const [lostNotes, setLostNotes] = useState('')
  const [sendNotifications, setSendNotifications] = useState(true)
  const [writeOffNotes, setWriteOffNotes] = useState('')
  const [assignToStaffId, setAssignToStaffId] = useState<number | ''>('')
  const [mendingPriority, setMendingPriority] = useState<number>(3)
  const [newPriority, setNewPriority] = useState<number>(3)

  const [lastResult, setLastResult] = useState<BulkOperationResult | null>(null)

  // Refs to store Promise resolvers for modal-based actions
  const assignMendingResolverRef = useRef<((result: BulkOperationResult) => void) | null>(null)
  const priorityResolverRef = useRef<((result: BulkOperationResult) => void) | null>(null)

  // Get page item IDs
  const pageItemIds = useMemo(() => items.map(item => item.id), [items])

  // Bulk mark items as lost
  const handleBulkMarkLost = useCallback(async (ids: number[]): Promise<BulkOperationResult<BulkMarkLostResponse>> => {
    try {
      const result = await bulkMarkLost(token, {
        checkout_ids: ids,
        lost_type: lostType,
        ...(lostNotes ? { notes: lostNotes } : {}),
        send_notifications: sendNotifications,
      })

      const opResult: BulkOperationResult<BulkMarkLostResponse> = {
        success: result.success_count > 0,
        successCount: result.success_count,
        failureCount: result.failure_count,
        message: `Marked ${result.success_count} items as lost. Total charges: $${result.total_charges.toFixed(2)}`,
        details: result,
        errors: result.results
          .filter(r => !r.success)
          .map(r => ({ id: r.checkout_id, error: r.message })),
      }

      if (result.success_count > 0) {
        toast.success(t('toast.staff.markedSuccesscountItemsAsLost', { successcount: result.success_count }))
        onOperationComplete?.()
      }

      setShowMarkLostModal(false)
      setLostNotes('')
      setLastResult(opResult)
      return opResult
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to mark items as lost'
      toast.error(message)
      throw error
    }
  }, [token, lostType, lostNotes, sendNotifications, onOperationComplete])

  // Bulk write-off lost items
  const handleBulkWriteOff = useCallback(async (ids: number[]): Promise<BulkOperationResult<BulkWriteOffResponse>> => {
    try {
      const result = await bulkWriteOffLostItems(token, {
        lost_record_ids: ids,
        ...(writeOffNotes ? { notes: writeOffNotes } : {}),
      })

      const opResult: BulkOperationResult<BulkWriteOffResponse> = {
        success: result.success_count > 0,
        successCount: result.success_count,
        failureCount: result.failure_count,
        message: `Wrote off ${result.success_count} lost items`,
        details: result,
        errors: result.results
          .filter(r => !r.success)
          .map(r => ({ id: r.record_id, error: r.message })),
      }

      if (result.success_count > 0) {
        toast.success(t('toast.staff.wroteOffSuccesscountItems', { successcount: result.success_count }))
        onOperationComplete?.()
      }

      setWriteOffNotes('')
      setLastResult(opResult)
      return opResult
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to write off items'
      toast.error(message)
      throw error
    }
  }, [token, writeOffNotes, onOperationComplete])

  // Bulk assign to mending
  const handleBulkAssignMending = useCallback(async (ids: number[]): Promise<BulkOperationResult<BulkMendingAssignResponse>> => {
    if (!assignToStaffId) {
      throw new Error('Please select a staff member')
    }

    try {
      const result = await bulkAssignMending(token, {
        mending_entry_ids: ids,
        assigned_to_id: Number(assignToStaffId),
        priority: mendingPriority,
      })

      const opResult: BulkOperationResult<BulkMendingAssignResponse> = {
        success: result.success_count > 0,
        successCount: result.success_count,
        failureCount: result.failure_count,
        message: `Assigned ${result.success_count} items to mending queue`,
        details: result,
        errors: result.results
          .filter(r => !r.success)
          .map(r => ({ id: r.entry_id, error: r.message })),
      }

      if (result.success_count > 0) {
        toast.success(t('toast.staff.assignedSuccesscountItems', { successcount: result.success_count }))
        onOperationComplete?.()
      }

      setShowAssignMendingModal(false)
      setAssignToStaffId('')
      setMendingPriority(3)
      setLastResult(opResult)
      assignMendingResolverRef.current?.(opResult)
      assignMendingResolverRef.current = null
      return opResult
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to assign items'
      toast.error(message)
      const errorResult = {
        success: false,
        successCount: 0,
        failureCount: ids.length,
        message,
      } as BulkOperationResult<BulkMendingAssignResponse>
      assignMendingResolverRef.current?.(errorResult)
      assignMendingResolverRef.current = null
      return errorResult
    }
  }, [token, assignToStaffId, mendingPriority, onOperationComplete])

  // Bulk update mending priority
  const handleBulkUpdatePriority = useCallback(async (ids: number[]): Promise<BulkOperationResult> => {
    try {
      const result = await bulkUpdateMendingPriority(token, ids, newPriority)

      const opResult: BulkOperationResult = {
        success: result.updated_count > 0,
        successCount: result.updated_count,
        failureCount: result.requested_count - result.updated_count,
        message: `Updated priority for ${result.updated_count} items to ${newPriority}`,
      }

      if (result.updated_count > 0) {
        toast.success(t('toast.staff.updatedUpdatedcountItems', { updatedcount: result.updated_count }))
        onOperationComplete?.()
      }

      setShowPriorityModal(false)
      setNewPriority(3)
      setLastResult(opResult)
      priorityResolverRef.current?.(opResult)
      priorityResolverRef.current = null
      return opResult
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to update priority'
      toast.error(message)
      const errorResult: BulkOperationResult = {
        success: false,
        successCount: 0,
        failureCount: ids.length,
        message,
      }
      priorityResolverRef.current?.(errorResult)
      priorityResolverRef.current = null
      return errorResult
    }
  }, [token, newPriority, onOperationComplete])

  // Define bulk actions based on item type
  const bulkActions: BulkAction[] = useMemo(() => {
    const actions: BulkAction[] = []

    if (itemType === 'lost') {
      actions.push(
        {
          id: 'write-off',
          label: 'Write Off Items',
          icon: <Trash2 className="w-4 h-4" />,
          description: t('components.staff.bulkItemOperations.writeOffItemsThatWill'),
          variant: 'danger',
          confirmMessage: (count) => `Are you sure you want to write off ${count} lost items? This action cannot be undone.`,
          onExecute: handleBulkWriteOff,
        }
      )
    }

    if (itemType === 'damaged') {
      actions.push(
        {
          id: 'assign-mending',
          label: 'Assign to Mending',
          icon: <Wrench className="w-4 h-4" />,
          description: t('components.staff.bulkItemOperations.addItemsToTheMending'),
          onExecute: async () => {
            setShowAssignMendingModal(true)
            return new Promise<BulkOperationResult>((resolve) => {
              assignMendingResolverRef.current = resolve
            })
          },
          requiresInput: true,
        }
      )
    }

    if (itemType === 'mending') {
      actions.push(
        {
          id: 'reassign',
          label: 'Reassign Staff',
          icon: <Users className="w-4 h-4" />,
          description: t('components.staff.bulkItemOperations.reassignItemsToADifferent'),
          onExecute: async () => {
            setShowAssignMendingModal(true)
            return new Promise<BulkOperationResult>((resolve) => {
              assignMendingResolverRef.current = resolve
            })
          },
          requiresInput: true,
        },
        {
          id: 'update-priority',
          label: 'Update Priority',
          icon: <ArrowUpDown className="w-4 h-4" />,
          description: t('components.staff.bulkItemOperations.changeThePriorityLevelFor'),
          onExecute: async () => {
            setShowPriorityModal(true)
            return new Promise<BulkOperationResult>((resolve) => {
              priorityResolverRef.current = resolve
            })
          },
          requiresInput: true,
        }
      )
    }

     
     
    return actions
   
  }, [itemType, handleBulkWriteOff])

  // Track if any modal is open
  const anyModalOpen = showMarkLostModal || showAssignMendingModal || showPriorityModal

  // Handle Escape key for modals
  useEffect(() => {
    if (!anyModalOpen) return

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault()
        setShowMarkLostModal(false)
        setShowAssignMendingModal(false)
        setShowPriorityModal(false)
        const cancelResult: BulkOperationResult = { success: true, successCount: 0, failureCount: 0, message: 'Cancelled' }
        assignMendingResolverRef.current?.(cancelResult)
        assignMendingResolverRef.current = null
        priorityResolverRef.current?.(cancelResult)
        priorityResolverRef.current = null
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

  // Get label for item type
  const itemLabel = useMemo(() => {
    switch (itemType) {
      case 'lost':
        return 'lost items'
      case 'damaged':
        return 'damaged items'
      case 'mending':
        return 'mending queue items'
      default:
        return 'items'
    }
  }, [itemType])

  // Get item type icon
  const TypeIcon = itemType === 'lost' ? AlertTriangle : itemType === 'damaged' ? FileWarning : Wrench

  return (
    <div className={className}>
      <BulkOperationsPanel
        selectedIds={selectedIds}
        totalItems={allItemIds.length}
        actions={bulkActions}
        onSelectionChange={setSelectedIds}
        allItemIds={allItemIds}
        pageItemIds={pageItemIds}
        itemLabel={itemLabel}
        {...(lastResult != null ? { lastResult } : {})}
        onResultDismiss={() => setLastResult(null)}
        compact={compact}
      />

      {/* Selection Summary */}
      {selectedCount > 0 && !compact && (
        <div className="mt-3 flex items-center gap-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
          <TypeIcon className="w-4 h-4" aria-hidden="true" />
          <span>{selectedCount} {itemLabel} selected</span>
        </div>
      )}

      {/* Mark Lost Modal */}
      {showMarkLostModal && (
        <FocusTrap active={showMarkLostModal} focusTrapOptions={{ escapeDeactivates: true }}>
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div
            className="fixed inset-0 bg-black/50 motion-safe:backdrop-blur-md"
            onClick={() => setShowMarkLostModal(false)}
            aria-hidden="true"
          />
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="mark-lost-title"
            className="relative bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-md w-full p-6"
          >
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 rounded-full bg-status-danger-100 dark:bg-status-danger-900/30">
                <AlertTriangle className="w-6 h-6 text-status-danger-600 dark:text-status-danger-400" aria-hidden="true" />
              </div>
              <div>
                <h3
                  id="mark-lost-title"
                  className="font-serif text-lg font-bold text-lsc-dark dark:text-lsc-cream"
                >
                  Mark Items as Lost
                </h3>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                  {selectedCount} items selected
                </p>
              </div>
            </div>

            <div className="space-y-4">
              {/* Lost Type */}
              <div>
                <label htmlFor="lost-type" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
                  Lost Type
                </label>
                {availableClassifications.length > 0 ? (
                  <select
                    id="lost-type"
                    value={lostType}
                    onChange={(e) => setLostType(e.target.value)}
                    className="w-full px-3 py-2.5 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                  >
                    {availableClassifications.map((classification) => (
                      <option key={classification.value} value={classification.value}>
                        {classification.label}
                      </option>
                    ))}
                  </select>
                ) : (
                  <select
                    id="lost-type"
                    value={lostType}
                    onChange={(e) => setLostType(e.target.value)}
                    className="w-full px-3 py-2.5 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                  >
                    <option value="lost_by_patron">Lost by Patron</option>
                    <option value="lost_in_transit">Lost in Transit</option>
                    <option value="missing">Missing (Inventory)</option>
                    <option value="long_overdue">Long Overdue</option>
                  </select>
                )}
              </div>

              {/* Notes */}
              <div>
                <label
                  htmlFor="lost-notes"
                  className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2"
                >
                  Notes (optional)
                </label>
                <textarea
                  id="lost-notes"
                  value={lostNotes}
                  onChange={(e) => setLostNotes(e.target.value)}
                  placeholder={t('placeholder.staff.additionalNotes')}
                  rows={3}
                  className="w-full px-3 py-2.5 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent resize-none"
                />
              </div>

              {/* Send Notifications */}
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={sendNotifications}
                  onChange={(e) => setSendNotifications(e.target.checked)}
                  className="w-5 h-5 rounded border-lsc-border dark:border-earth-700 text-lsc-rose focus:ring-lsc-rose"
                />
                <span className="text-sm text-lsc-dark dark:text-lsc-cream">
                  Send notifications to patrons
                </span>
              </label>

              <div className="flex gap-3">
                <button
                  onClick={() => {
                    setShowMarkLostModal(false)
                    setLostNotes('')
                  }}
                  className="flex-1 px-4 py-2.5 bg-lsc-cream dark:bg-lsc-brown hover:bg-lsc-border dark:hover:bg-lsc-brown/80 text-lsc-dark dark:text-lsc-cream rounded-xl font-medium transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={() => handleBulkMarkLost(selectedIds)}
                  className="flex-1 px-4 py-2.5 bg-status-danger-600 hover:bg-status-danger-700 text-white rounded-xl font-medium transition-colors"
                >
                  Mark as Lost
                </button>
              </div>
            </div>
          </div>
        </div>
        </FocusTrap>
      )}

      {/* Assign Mending Modal */}
      {showAssignMendingModal && (
        <FocusTrap active={showAssignMendingModal} focusTrapOptions={{ escapeDeactivates: true }}>
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div
            className="fixed inset-0 bg-black/50 motion-safe:backdrop-blur-md"
            onClick={() => {
              setShowAssignMendingModal(false)
              setAssignToStaffId('')
              setMendingPriority(3)
              assignMendingResolverRef.current?.({ success: true, successCount: 0, failureCount: 0, message: 'Cancelled' })
              assignMendingResolverRef.current = null
            }}
            aria-hidden="true"
          />
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="assign-mending-title"
            className="relative bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-md w-full p-6"
          >
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 rounded-full bg-earth-100 dark:bg-earth-800/30">
                <Wrench className="w-6 h-6 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
              </div>
              <div>
                <h3
                  id="assign-mending-title"
                  className="font-serif text-lg font-bold text-lsc-dark dark:text-lsc-cream"
                >
                  {itemType === 'mending' ? 'Reassign Items' : 'Assign to Mending'}
                </h3>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                  {selectedCount} items selected
                </p>
              </div>
            </div>

            <div className="space-y-4">
              {/* Staff Assignment */}
              <div>
                <label
                  htmlFor="assign-staff"
                  className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2"
                >
                  Assign to Staff Member
                </label>
                <select
                  id="assign-staff"
                  value={assignToStaffId}
                  onChange={(e) => setAssignToStaffId(e.target.value ? Number(e.target.value) : '')}
                  className="w-full px-3 py-2.5 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                >
                  <option value="">{t('components.staff.bulkItemOperations.selectAStaffMember')}</option>
                  {staffMembers.map((staff) => (
                    <option key={staff.id} value={staff.id}>
                      {staff.name}
                    </option>
                  ))}
                </select>
              </div>

              {/* Priority */}
              <div>
                <label
                  htmlFor="mending-priority"
                  className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2"
                >
                  Priority (1 = Highest, 5 = Lowest)
                </label>
                <input
                  id="mending-priority"
                  type="range"
                  min="1"
                  max="5"
                  value={mendingPriority}
                  onChange={(e) => setMendingPriority(Number(e.target.value))}
                  className="w-full"
                />
                <div className="flex justify-between text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                  <span>1 - Urgent</span>
                  <span className="font-medium text-lsc-rose">{mendingPriority}</span>
                  <span>5 - Low</span>
                </div>
              </div>

              <div className="flex gap-3">
                <button
                  onClick={() => {
                    setShowAssignMendingModal(false)
                    setAssignToStaffId('')
                    setMendingPriority(3)
                    assignMendingResolverRef.current?.({ success: true, successCount: 0, failureCount: 0, message: 'Cancelled' })
                    assignMendingResolverRef.current = null
                  }}
                  className="flex-1 px-4 py-2.5 bg-lsc-cream dark:bg-lsc-brown hover:bg-lsc-border dark:hover:bg-lsc-brown/80 text-lsc-dark dark:text-lsc-cream rounded-xl font-medium transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={() => handleBulkAssignMending(selectedIds)}
                  disabled={!assignToStaffId}
                  className="flex-1 px-4 py-2.5 bg-lsc-rose hover:bg-lsc-rose/90 disabled:bg-lsc-rose/50 text-white rounded-xl font-medium transition-colors disabled:cursor-not-allowed"
                >
                  Assign
                </button>
              </div>
            </div>
          </div>
        </div>
        </FocusTrap>
      )}

      {/* Priority Update Modal */}
      {showPriorityModal && (
        <FocusTrap active={showPriorityModal} focusTrapOptions={{ escapeDeactivates: true }}>
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div
            className="fixed inset-0 bg-black/50 motion-safe:backdrop-blur-md"
            onClick={() => {
              setShowPriorityModal(false)
              setNewPriority(3)
              priorityResolverRef.current?.({ success: true, successCount: 0, failureCount: 0, message: 'Cancelled' })
              priorityResolverRef.current = null
            }}
            aria-hidden="true"
          />
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="priority-title"
            className="relative bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-md w-full p-6"
          >
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 rounded-full bg-status-warning-100 dark:bg-status-warning-900/30">
                <ArrowUpDown className="w-6 h-6 text-status-warning-600 dark:text-status-warning-400" aria-hidden="true" />
              </div>
              <div>
                <h3
                  id="priority-title"
                  className="font-serif text-lg font-bold text-lsc-dark dark:text-lsc-cream"
                >
                  Update Priority
                </h3>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                  {selectedCount} items selected
                </p>
              </div>
            </div>

            <div className="space-y-4">
              {/* Priority Selector */}
              <div>
                <label
                  htmlFor="new-priority"
                  className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2"
                >
                  New Priority (1 = Highest, 5 = Lowest)
                </label>
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-2">
                  {[1, 2, 3, 4, 5].map((p) => (
                    <button
                      key={p}
                      type="button"
                      onClick={() => setNewPriority(p)}
                      aria-pressed={newPriority === p}
                      className={`py-3 rounded-xl font-medium text-lg transition-colors ${
                        newPriority === p
                          ? p === 1
                            ? 'bg-status-danger-600 text-white'
                            : p === 2
                            ? 'bg-status-warning-700 text-white'
                            : p === 3
                            ? 'bg-status-warning-700 text-white'
                            : p === 4
                            ? 'bg-earth-500 text-white'
                            : 'bg-earth-500 text-white'
                          : 'bg-lsc-cream dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream hover:bg-lsc-border dark:hover:bg-lsc-brown/80'
                      }`}
                    >
                      {p}
                    </button>
                  ))}
                </div>
                <div className="flex justify-between text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-2">
                  <span>Urgent</span>
                  <span>Low</span>
                </div>
              </div>

              <div className="flex gap-3">
                <button
                  onClick={() => {
                    setShowPriorityModal(false)
                    setNewPriority(3)
                    priorityResolverRef.current?.({ success: true, successCount: 0, failureCount: 0, message: 'Cancelled' })
                    priorityResolverRef.current = null
                  }}
                  className="flex-1 px-4 py-2.5 bg-lsc-cream dark:bg-lsc-brown hover:bg-lsc-border dark:hover:bg-lsc-brown/80 text-lsc-dark dark:text-lsc-cream rounded-xl font-medium transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={() => handleBulkUpdatePriority(selectedIds)}
                  className="flex-1 px-4 py-2.5 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl font-medium transition-colors"
                >
                  Update Priority
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

export { useBulkSelection }

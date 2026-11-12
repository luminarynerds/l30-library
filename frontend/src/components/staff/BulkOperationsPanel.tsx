/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/* eslint-disable react-hooks/exhaustive-deps */
/* eslint-disable react-refresh/only-export-components */
/**
 * BulkOperationsPanel Component
 *
 * A reusable component for bulk operations with:
 * - Multi-select functionality with select all/none
 * - Bulk action dropdown menu
 * - Progress indicator for ongoing operations
 * - Results summary with success/failure counts
 */

import { useState, useRef, useEffect, useCallback, useMemo } from 'react'
import FocusTrap from 'focus-trap-react'
import {
  CheckSquare,
  Square,
  MinusSquare,
  ChevronDown,
  Loader2,
  CheckCircle,
  XCircle,
  AlertTriangle,
  X,
} from 'lucide-react'
import { t } from '@/i18n'

// ==================== Types ====================

export interface BulkAction<T = unknown> {
  id: string
  label: string
  icon?: React.ReactNode
  description?: string
  variant?: 'default' | 'danger' | 'warning'
  /** Function to execute the action on selected items */
  onExecute: (selectedIds: number[]) => Promise<BulkOperationResult<T>>
  /** Optional confirmation message */
  confirmMessage?: string | ((count: number) => string)
  /** Whether this action requires additional input */
  requiresInput?: boolean
  /** Minimum number of items required */
  minItems?: number
  /** Maximum number of items allowed */
  maxItems?: number
  /** Disable condition */
  disabled?: boolean
  /** Disable reason tooltip */
  disabledReason?: string
}

export interface BulkOperationResult<T = unknown> {
  success: boolean
  successCount: number
  failureCount: number
  message: string
  details?: T | undefined
  failedIds?: number[] | undefined
  errors?: Array<{ id: number; error: string }> | undefined
}

export interface BulkOperationProgress {
  current: number
  total: number
  status: 'idle' | 'processing' | 'completed' | 'error'
  message?: string
}

interface BulkOperationsPanelProps<T = unknown> {
  /** Currently selected item IDs */
  selectedIds: number[]
  /** Total number of items in the list */
  totalItems: number
  /** Available bulk actions */
  actions: BulkAction<T>[]
  /** Callback when selection changes */
  onSelectionChange: (selectedIds: number[]) => void
  /** All item IDs for select all functionality */
  allItemIds: number[]
  /** Optional: Current page item IDs for page selection */
  pageItemIds?: number[]
  /** Optional: Label for items (e.g., "patrons", "items") */
  itemLabel?: string
  /** Optional: Custom progress state */
  progress?: BulkOperationProgress
  /** Optional: Last operation result */
  lastResult?: BulkOperationResult<T>
  /** Optional: Callback when result is dismissed */
  onResultDismiss?: () => void
  /** Optional: className for styling */
  className?: string
  /** Optional: Show selection count badge */
  showSelectionBadge?: boolean
  /** Optional: Compact mode */
  compact?: boolean
}

// ==================== Component ====================

// eslint-disable-next-line complexity
export default function BulkOperationsPanel<T = unknown>({
  selectedIds,
  totalItems: _totalItems,
  actions,
  onSelectionChange,
  allItemIds,
  pageItemIds,
  itemLabel = 'items',
  progress,
  lastResult,
  onResultDismiss,
  className = '',
  showSelectionBadge = true,
  compact = false,
}: BulkOperationsPanelProps<T>): React.ReactElement {
  const [isDropdownOpen, setIsDropdownOpen] = useState(false)
  const [confirmAction, setConfirmAction] = useState<BulkAction<T> | null>(null)
  const [isExecuting, setIsExecuting] = useState(false)
  const [operationResult, setOperationResult] = useState<BulkOperationResult<T> | null>(lastResult || null)
  const [internalProgress, setInternalProgress] = useState<BulkOperationProgress>({
    current: 0,
    total: 0,
    status: 'idle',
  })
  const dropdownRef = useRef<HTMLDivElement>(null)
  const triggerRef = useRef<HTMLButtonElement>(null)

  // Handle keyboard navigation for dropdown menu
  const handleDropdownKeyDown = useCallback((event: React.KeyboardEvent) => {
    if (!isDropdownOpen) return

    const items = dropdownRef.current?.querySelectorAll('[role="menuitem"]') as NodeListOf<HTMLElement> | undefined
    if (!items?.length) return

    const currentIndex = Array.from(items).indexOf(document.activeElement as HTMLElement)

    switch (event.key) {
      case 'ArrowDown':
        event.preventDefault()
        items[(currentIndex + 1) % items.length]!.focus()
        break
      case 'ArrowUp':
        event.preventDefault()
        items[(currentIndex - 1 + items.length) % items.length]!.focus()
        break
      case 'Home':
        event.preventDefault()
        items[0]!.focus()
        break
      case 'End':
        event.preventDefault()
        items[items.length - 1]!.focus()
        break
      case 'Escape':
        event.preventDefault()
        setIsDropdownOpen(false)
        triggerRef.current?.focus()
        break
    }
  }, [isDropdownOpen])

  // Use external progress if provided
  const currentProgress = progress || internalProgress

  // Update operation result when lastResult changes
  useEffect(() => {
    if (lastResult) {
      setOperationResult(lastResult)
    }
  }, [lastResult])

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsDropdownOpen(false)
      }
    }

    if (isDropdownOpen) {
      document.addEventListener('mousedown', handleClickOutside)
      return () => document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [isDropdownOpen])

  // Selection state
  const selectedCount = selectedIds.length
  const isAllSelected = selectedCount > 0 && selectedCount === allItemIds.length
  const isSomeSelected = selectedCount > 0 && selectedCount < allItemIds.length

  // Handle select all
  const handleSelectAll = useCallback(() => {
    if (isAllSelected) {
      onSelectionChange([])
    } else {
      onSelectionChange([...allItemIds])
    }
  }, [isAllSelected, allItemIds, onSelectionChange])

  // Handle select page
  const handleSelectPage = useCallback(() => {
    if (!pageItemIds) return
    const newSelection = new Set(selectedIds)
    pageItemIds.forEach(id => newSelection.add(id))
    onSelectionChange(Array.from(newSelection))
  }, [pageItemIds, selectedIds, onSelectionChange])

  // Handle clear selection
  const handleClearSelection = useCallback(() => {
    onSelectionChange([])
  }, [onSelectionChange])

  // Execute action
  const executeAction = useCallback(async (action: BulkAction<T>) => {
    setConfirmAction(null)
    setIsExecuting(true)
    setInternalProgress({
      current: 0,
      total: selectedIds.length,
      status: 'processing',
      message: `Processing ${selectedIds.length} ${itemLabel}...`,
    })

    try {
      const result = await action.onExecute(selectedIds)
      setOperationResult(result)
      setInternalProgress({
        current: selectedIds.length,
        total: selectedIds.length,
        status: result.success ? 'completed' : 'error',
        message: result.message,
      })

      // Clear selection on success if desired
      if (result.success && result.successCount > 0) {
        // Remove successful items from selection
        if (result.failedIds && result.failedIds.length > 0) {
          onSelectionChange(result.failedIds)
        } else {
          onSelectionChange([])
        }
      }
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Operation failed'
      setOperationResult({
        success: false,
        successCount: 0,
        failureCount: selectedIds.length,
        message,
      })
      setInternalProgress({
        current: 0,
        total: selectedIds.length,
        status: 'error',
        message,
      })
    } finally {
      setIsExecuting(false)
    }
  }, [selectedIds, itemLabel, onSelectionChange])


  // Handle action click
  const handleActionClick = useCallback((action: BulkAction<T>) => {
    setIsDropdownOpen(false)

    if (action.confirmMessage) {
      setConfirmAction(action)
    } else {
      executeAction(action)


    }

  }, [selectedIds])

  // Dismiss result
  const handleDismissResult = useCallback(() => {
    setOperationResult(null)
    setInternalProgress({ current: 0, total: 0, status: 'idle' })
    onResultDismiss?.()
  }, [onResultDismiss])

  // Get confirmation message
  const getConfirmMessage = (action: BulkAction<T>): string => {
    if (typeof action.confirmMessage === 'function') {
      return action.confirmMessage(selectedCount)
    }
    return action.confirmMessage || `Are you sure you want to ${action.label.toLowerCase()} ${selectedCount} ${itemLabel}?`
  }

  // Check if action is enabled
  const isActionEnabled = (action: BulkAction<T>): boolean => {
    if (action.disabled) return false
    if (selectedCount === 0) return false
    if (action.minItems && selectedCount < action.minItems) return false
    if (action.maxItems && selectedCount > action.maxItems) return false
    return true
  }

  // Render checkbox icon
  const CheckboxIcon = isAllSelected ? CheckSquare : isSomeSelected ? MinusSquare : Square

  return (
    <div className={`${className}`}>
      {/* Selection Bar */}
      <div className={`flex items-center ${compact ? 'gap-2' : 'gap-3'} flex-wrap`}>
        {/* Select All Checkbox */}
        <button
          onClick={handleSelectAll}
          className="flex items-center gap-2 p-2 rounded-lg hover:bg-lsc-cream dark:hover:bg-lsc-brown/50 transition-colors"
          aria-label={isAllSelected ? 'Deselect all' : 'Select all'}
        >
          <CheckboxIcon
            className={`w-5 h-5 ${
              isAllSelected || isSomeSelected
                ? 'text-lsc-rose dark:text-lsc-rose-light'
                : 'text-lsc-dark/70 dark:text-lsc-cream/70'
            }`}
            aria-hidden="true"
          />
          {!compact && (
            <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
              {isAllSelected ? 'Deselect all' : 'Select all'}
            </span>
          )}
        </button>

        {/* Selection Info */}
        {showSelectionBadge && selectedCount > 0 && (
          <div className="flex items-center gap-2 px-3 py-1.5 bg-lsc-rose/10 dark:bg-lsc-rose/20 rounded-full">
            <span className="text-sm font-medium text-lsc-rose dark:text-lsc-rose-light">
              {selectedCount} selected
            </span>
            <button
              onClick={handleClearSelection}
              className="p-0.5 rounded hover:bg-lsc-rose/20 dark:hover:bg-lsc-rose/30 transition-colors"
              aria-label={t('aria.staff.clearSelection')}
            >
              <X className="w-3.5 h-3.5 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
            </button>
          </div>
        )}

        {/* Page Selection (if page items provided) */}
        {pageItemIds && pageItemIds.length > 0 && !compact && (
          <button
            onClick={handleSelectPage}
            className="text-sm text-lsc-rose dark:text-lsc-rose-light hover:underline"
          >
            Select this page
          </button>
        )}

        {/* Spacer */}
        <div className="flex-1" />

        {/* Actions Dropdown */}
        {selectedCount > 0 && actions.length > 0 && (
          <div ref={dropdownRef} className="relative" onKeyDown={handleDropdownKeyDown}>
            <button
              ref={triggerRef}
              onClick={() => setIsDropdownOpen(!isDropdownOpen)}
              disabled={isExecuting}
              className={`flex items-center gap-2 px-4 py-2 ${
                compact ? 'text-sm' : ''
              } bg-lsc-rose hover:bg-lsc-rose/90 disabled:bg-lsc-rose/50 text-white rounded-xl font-medium transition-colors`}
              aria-expanded={isDropdownOpen}
              aria-haspopup="menu"
            >
              {isExecuting ? (
                <>
                  <Loader2 className="w-4 h-4 motion-safe:animate-spin" aria-hidden="true" />
                  <span>Processing...</span>
                </>
              ) : (
                <>
                  <span>Bulk Actions</span>
                  <ChevronDown className={`w-4 h-4 transition-transform ${isDropdownOpen ? 'rotate-180' : ''}`} aria-hidden="true" />
                </>
              )}
            </button>

            {/* Dropdown Menu */}
            {isDropdownOpen && !isExecuting && (
              <div
                role="menu"
                aria-label={t('aria.staff.bulkActions')}
                className="absolute right-0 top-full mt-2 w-64 bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg border border-lsc-border dark:border-earth-700 py-2 z-50"
              >
                {actions.map((action) => {
                  const enabled = isActionEnabled(action)
                  return (
                    <button
                      key={action.id}
                      role="menuitem"
                      tabIndex={-1}
                      onClick={() => enabled && handleActionClick(action)}
                      disabled={!enabled}
                      className={`w-full flex items-start gap-3 px-4 py-2.5 text-left transition-colors ${
                        enabled
                          ? action.variant === 'danger'
                            ? 'hover:bg-status-danger-50 dark:bg-status-danger-900/20 dark:hover:bg-status-danger-900/20'
                            : action.variant === 'warning'
                            ? 'hover:bg-status-warning-50 dark:bg-status-warning-900/20 dark:hover:bg-status-warning-900/20'
                            : 'hover:bg-lsc-cream dark:hover:bg-lsc-brown/50'
                          : 'opacity-50 cursor-not-allowed'
                      }`}
                      title={!enabled && action.disabledReason ? action.disabledReason : undefined}
                    >
                      {action.icon && (
                        <span
                          className={`flex-shrink-0 ${
                            action.variant === 'danger'
                              ? 'text-status-danger-500 dark:text-status-danger-400'
                              : action.variant === 'warning'
                              ? 'text-status-warning-500 dark:text-status-warning-400'
                              : 'text-lsc-dark/70 dark:text-lsc-cream/70'
                          }`}
                          aria-hidden="true"
                        >
                          {action.icon}
                        </span>
                      )}
                      <div className="flex-1 min-w-0">
                        <p
                          className={`text-sm font-medium ${
                            action.variant === 'danger'
                              ? 'text-status-danger-600 dark:text-status-danger-400'
                              : action.variant === 'warning'
                              ? 'text-status-warning-600 dark:text-status-warning-400'
                              : 'text-lsc-dark dark:text-lsc-cream'
                          }`}
                        >
                          {action.label}
                        </p>
                        {action.description && (
                          <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-0.5">
                            {action.description}
                          </p>
                        )}
                      </div>
                    </button>
                  )
                })}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Progress Indicator */}
      {currentProgress.status === 'processing' && (
        <div className="mt-4 p-4 bg-earth-50 dark:bg-earth-800/20 rounded-xl">
          <div className="flex items-center gap-3">
            <Loader2 className="w-5 h-5 motion-safe:animate-spin text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
            <div className="flex-1">
              <p className="text-sm font-medium text-earth-800 dark:text-lsc-rose-light">
                {currentProgress.message || 'Processing...'}
              </p>
              <div className="mt-2 w-full bg-earth-200 dark:bg-earth-800 rounded-full h-2">
                <div
                  className="bg-lsc-rose dark:bg-earth-400 h-2 rounded-full transition-all duration-300"
                  style={{
                    width: `${currentProgress.total > 0 ? (currentProgress.current / currentProgress.total) * 100 : 0}%`,
                  }}
                />
              </div>
              <p className="mt-1 text-xs text-lsc-rose dark:text-lsc-rose-light">
                {currentProgress.current} of {currentProgress.total}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Operation Result */}
      {operationResult && currentProgress.status !== 'processing' && (
        <div
          className={`mt-4 p-4 rounded-xl ${
            operationResult.success
              ? 'bg-status-success-50 dark:bg-status-success-900/20 border border-status-success-200 dark:border-status-success-800'
              : 'bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800'
          }`}
        >
          <div className="flex items-start gap-3">
            {operationResult.success ? (
              <CheckCircle className="w-5 h-5 text-status-success-600 dark:text-status-success-400 flex-shrink-0 mt-0.5" aria-hidden="true" />
            ) : (
              <XCircle className="w-5 h-5 text-status-danger-600 dark:text-status-danger-400 flex-shrink-0 mt-0.5" aria-hidden="true" />
            )}
            <div className="flex-1 min-w-0">
              <p
                className={`text-sm font-medium ${
                  operationResult.success
                    ? 'text-status-success-800 dark:text-status-success-300'
                    : 'text-status-danger-800 dark:text-status-danger-300'
                }`}
              >
                {operationResult.message}
              </p>
              <div className="mt-2 flex items-center gap-4 text-xs">
                {operationResult.successCount > 0 && (
                  <span className="flex items-center gap-1 text-status-success-600 dark:text-status-success-400">
                    <CheckCircle className="w-3.5 h-3.5" aria-hidden="true" />
                    {operationResult.successCount} succeeded
                  </span>
                )}
                {operationResult.failureCount > 0 && (
                  <span className="flex items-center gap-1 text-status-danger-600 dark:text-status-danger-400">
                    <XCircle className="w-3.5 h-3.5" aria-hidden="true" />
                    {operationResult.failureCount} failed
                  </span>
                )}
              </div>
              {operationResult.errors && operationResult.errors.length > 0 && (
                <div className="mt-2 space-y-1">
                  <p className="text-xs font-medium text-status-danger-700 dark:text-status-danger-400">Errors:</p>
                  <ul className="text-xs text-status-danger-600 dark:text-status-danger-400 space-y-0.5 max-h-24 overflow-y-auto">
                    {operationResult.errors.slice(0, 5).map((err, idx) => (
                      <li key={idx}>ID {err.id}: {err.error}</li>
                    ))}
                    {operationResult.errors.length > 5 && (
                      <li>...and {operationResult.errors.length - 5} more</li>
                    )}
                  </ul>
                </div>
              )}
            </div>
            <button
              onClick={handleDismissResult}
              className={`p-1 rounded hover:bg-black/10 transition-colors ${
                operationResult.success
                  ? 'text-status-success-600 dark:text-status-success-400'
                  : 'text-status-danger-600 dark:text-status-danger-400'
              }`}
              aria-label={t('aria.account.dismiss')}
            >
              <X className="w-4 h-4" aria-hidden="true" />
            </button>
          </div>
        </div>
      )}

      {/* Confirmation Dialog */}
      {confirmAction && (
        <FocusTrap active={!!confirmAction} focusTrapOptions={{ escapeDeactivates: true }}>
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div
            className="fixed inset-0 bg-black/50 motion-safe:backdrop-blur-md"
            onClick={() => setConfirmAction(null)}
            aria-hidden="true"
          />
          <div
            role="alertdialog"
            aria-modal="true"
            aria-labelledby="confirm-title"
            aria-describedby="confirm-description"
            className="relative bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-md w-full p-6"
          >
            <div className="flex items-start gap-4">
              <div
                className={`p-2 rounded-full ${
                  confirmAction.variant === 'danger'
                    ? 'bg-status-danger-100 dark:bg-status-danger-900/30'
                    : confirmAction.variant === 'warning'
                    ? 'bg-status-warning-100 dark:bg-status-warning-900/30'
                    : 'bg-earth-100 dark:bg-earth-800/30'
                }`}
              >
                <AlertTriangle
                  className={`w-6 h-6 ${
                    confirmAction.variant === 'danger'
                      ? 'text-status-danger-600 dark:text-status-danger-400'
                      : confirmAction.variant === 'warning'
                      ? 'text-status-warning-600 dark:text-status-warning-400'
                      : 'text-lsc-rose dark:text-lsc-rose-light'
                  }`}
                  aria-hidden="true"
                />
              </div>
              <div className="flex-1">
                <h3
                  id="confirm-title"
                  className="font-serif text-lg font-bold text-lsc-dark dark:text-lsc-cream"
                >
                  Confirm {confirmAction.label}
                </h3>
                <p
                  id="confirm-description"
                  className="mt-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70"
                >
                  {getConfirmMessage(confirmAction)}
                </p>
                <div className="mt-4 flex gap-3">
                  <button
                    onClick={() => setConfirmAction(null)}
                    className="flex-1 px-4 py-2.5 bg-lsc-cream dark:bg-lsc-brown hover:bg-lsc-border dark:hover:bg-lsc-brown/80 text-lsc-dark dark:text-lsc-cream rounded-xl font-medium transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={() => executeAction(confirmAction)}
                    className={`flex-1 px-4 py-2.5 rounded-xl font-medium transition-colors ${
                      confirmAction.variant === 'danger'
                        ? 'bg-status-danger-600 hover:bg-status-danger-700 text-white'
                        : confirmAction.variant === 'warning'
                        ? 'bg-status-warning-500 hover:bg-status-warning-600 text-white'
                        : 'bg-lsc-rose hover:bg-lsc-rose/90 text-white'
                    }`}
                  >
                    {confirmAction.label}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
        </FocusTrap>
      )}
    </div>
  )
}

// ==================== Utility Hook ====================

export function useBulkSelection(initialIds: number[] = []) {
  const [selectedIds, setSelectedIds] = useState<number[]>(initialIds)
  const [lastSelectedIndex, setLastSelectedIndex] = useState<number | null>(null)

  // O(1) lookup set, derived from selectedIds
  const selectedSet = useMemo(() => new Set(selectedIds), [selectedIds])

  const toggleSelection = useCallback((id: number) => {
    setSelectedIds((prev) => {
      const set = new Set(prev)
      if (set.has(id)) {
        set.delete(id)
      } else {
        set.add(id)
      }
      return Array.from(set)
    })
  }, [])

  /**
   * Toggle selection with shift-click range selection support.
   * @param id - The ID of the item to toggle
   * @param index - The index of the item in the list
   * @param allIds - Array of all item IDs in display order
   * @param shiftKey - Whether the shift key was held during the click
   */
  const toggleSelectionWithRange = useCallback((
    id: number,
    index: number,
    allIds: number[],
    shiftKey: boolean = false
  ) => {
    if (shiftKey && lastSelectedIndex !== null && lastSelectedIndex !== index) {
      const start = Math.min(lastSelectedIndex, index)
      const end = Math.max(lastSelectedIndex, index)
      const rangeIds = allIds.slice(start, end + 1)

      setSelectedIds((prev) => {
        const newSet = new Set([...prev, ...rangeIds])
        return Array.from(newSet)
      })
    } else {
      setSelectedIds((prev) => {
        const set = new Set(prev)
        if (set.has(id)) {
          set.delete(id)
        } else {
          set.add(id)
        }
        return Array.from(set)
      })
    }
    setLastSelectedIndex(index)
  }, [lastSelectedIndex])

  const selectAll = useCallback((ids: number[]) => {
    setSelectedIds(ids)
    setLastSelectedIndex(null)
  }, [])

  const clearSelection = useCallback(() => {
    setSelectedIds([])
    setLastSelectedIndex(null)
  }, [])

  const isSelected = useCallback((id: number) => {
    return selectedSet.has(id)
  }, [selectedSet])

  return {
    selectedIds,
    setSelectedIds,
    toggleSelection,
    toggleSelectionWithRange,
    selectAll,
    clearSelection,
    isSelected,
    selectedCount: selectedIds.length,
  }
}

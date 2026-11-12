/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Staff Components Index
 *
 * Export all staff-related components for easy import
 */

// Bulk Operations Components
export { default as BulkOperationsPanel, useBulkSelection } from './BulkOperationsPanel'
export type { BulkAction, BulkOperationResult, BulkOperationProgress } from './BulkOperationsPanel'

export { default as BulkPatronOperations } from './BulkPatronOperations'
export { default as BulkItemOperations } from './BulkItemOperations'
export type { LostItem, DamagedItem, MendingQueueItem } from './BulkItemOperations'

// Quick Actions Components
export { default as PatronQuickActionsMenu } from './PatronQuickActionsMenu'
export { default as QuickCheckoutModal } from './QuickCheckoutModal'
export { default as SendNotificationModal } from './SendNotificationModal'
export { default as KeyboardShortcutsHelpModal } from './KeyboardShortcutsHelpModal'
export { default as KeyboardShortcutsPanel } from './KeyboardShortcutsPanel'

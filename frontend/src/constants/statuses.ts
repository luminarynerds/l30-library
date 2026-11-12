/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Status String Constants
 *
 * Centralized status string literals used across the frontend.
 * Using constants prevents typos and enables refactoring.
 *
 * Note: These are generic workflow/lifecycle statuses that appear across
 * many different entity types (tasks, sessions, items, etc.).
 * Domain-specific statuses should remain in their respective modules.
 */

// ==================== Generic Workflow Statuses ====================

/** Common task/workflow lifecycle statuses */
export const WorkflowStatus = {
  PENDING: "pending",
  ACTIVE: "active",
  COMPLETED: "completed",
  FAILED: "failed",
  PROCESSING: "processing",
  CANCELLED: "cancelled",
} as const

export type WorkflowStatusType = (typeof WorkflowStatus)[keyof typeof WorkflowStatus]

// ==================== Sync / Data Transfer Statuses ====================

/** Statuses for data synchronization operations */
export const SyncStatus = {
  PENDING: "pending",
  PROCESSING: "processing",
  COMPLETED: "completed",
  FAILED: "failed",
} as const

export type SyncStatusType = (typeof SyncStatus)[keyof typeof SyncStatus]

// ==================== Approval Statuses ====================

/** Statuses for items requiring approval */
export const ApprovalStatus = {
  PENDING: "pending",
  APPROVED: "approved",
  REJECTED: "rejected",
  DRAFT: "draft",
} as const

export type ApprovalStatusType = (typeof ApprovalStatus)[keyof typeof ApprovalStatus]

// ==================== Entity Statuses ====================

/** Common active/inactive entity statuses */
export const EntityStatus = {
  ACTIVE: "active",
  INACTIVE: "inactive",
  ARCHIVED: "archived",
} as const

export type EntityStatusType = (typeof EntityStatus)[keyof typeof EntityStatus]

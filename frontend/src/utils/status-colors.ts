/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Unified status color helpers for Lost & Damaged domain.
 *
 * Each map returns Tailwind utility classes that include both light and dark
 * mode variants so the badges render correctly regardless of theme.
 */

import type {
  LostItemStatus,
  LostItemType,
  DamagedItemStatus,
  DamageSeverity,
  ClaimDisputeStatus,
} from "../api/staff-api"

// ---------------------------------------------------------------------------
// Color constants (reused across several maps)
// ---------------------------------------------------------------------------
const YELLOW = "bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-400"
const BLUE   = "bg-earth-100 text-earth-800 dark:bg-earth-800/30 dark:text-lsc-rose-light"
const GREEN  = "bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-400"
const RED    = "bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900/30 dark:text-status-danger-400"
const ORANGE = "bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-400"
const PURPLE = "bg-category-100 text-category-800 dark:bg-category-900/30 dark:text-category-400"
const TEAL   = "bg-teal-100 text-teal-800 dark:bg-teal-900/30 dark:text-teal-400"
const EARTH  = "bg-earth-100 text-earth-800 dark:bg-earth-900/30 dark:text-earth-300"

const EARTH_FALLBACK = "bg-earth-100 text-earth-800 dark:bg-earth-900/30 dark:text-earth-300"

// ---------------------------------------------------------------------------
// Lost item status
// ---------------------------------------------------------------------------
const LOST_STATUS_COLORS: Record<LostItemStatus, string> = {
  reported:    YELLOW,
  confirmed:   BLUE,
  charged:     ORANGE,
  found:       GREEN,
  written_off: EARTH,
}

export function getLostStatusColor(status: LostItemStatus): string {
  return LOST_STATUS_COLORS[status] ?? EARTH_FALLBACK
}

// ---------------------------------------------------------------------------
// Lost item type labels
// ---------------------------------------------------------------------------
const LOST_TYPE_LABELS: Record<LostItemType, string> = {
  lost_by_patron:    "Lost by Patron",
  lost_in_transit:   "Lost in Transit",
  missing_inventory: "Missing (Inventory)",
  claims_returned:   "Claims Returned",
}

export function getLostTypeLabel(type: LostItemType): string {
  return LOST_TYPE_LABELS[type] ?? type
}

// ---------------------------------------------------------------------------
// Damaged item status
// ---------------------------------------------------------------------------
const DAMAGED_STATUS_COLORS: Record<DamagedItemStatus, string> = {
  reported:   YELLOW,
  assessing:  BLUE,
  in_mending: PURPLE,
  repaired:   GREEN,
  withdrawn:  EARTH,
}

export function getDamagedStatusColor(status: DamagedItemStatus): string {
  return DAMAGED_STATUS_COLORS[status] ?? EARTH_FALLBACK
}

// ---------------------------------------------------------------------------
// Damage severity
// ---------------------------------------------------------------------------
const SEVERITY_COLORS: Record<DamageSeverity, string> = {
  minor:     GREEN,
  moderate:  YELLOW,
  severe:    ORANGE,
  destroyed: RED,
}

export function getSeverityColor(severity: DamageSeverity): string {
  return SEVERITY_COLORS[severity] ?? EARTH_FALLBACK
}

// ---------------------------------------------------------------------------
// Claim dispute status
// ---------------------------------------------------------------------------
const CLAIM_STATUS_COLORS: Record<ClaimDisputeStatus, string> = {
  filed:             YELLOW,
  under_review:      BLUE,
  searching:         PURPLE,
  resolved_approved: GREEN,
  resolved_denied:   RED,
  resolved_found:    TEAL,
}

export function getClaimStatusColor(status: ClaimDisputeStatus): string {
  return CLAIM_STATUS_COLORS[status] ?? EARTH_FALLBACK
}

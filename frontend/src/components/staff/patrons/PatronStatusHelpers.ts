/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Patron } from "../../../api/api"

export type PatronStatus = "active" | "suspended" | "blocked" | "deceased"

export function getEffectivePatronStatus(patron: Patron): PatronStatus {
  if (patron.patron_status) {
    return patron.patron_status
  }
  // Fallback: derive from is_active for backwards compatibility
  return patron.is_active ? "active" : "blocked"
}

export function getStatusBadgeClasses(status: PatronStatus): string {
  switch (status) {
    case "active":
      return "bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-400"
    case "suspended":
      return "bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-700 dark:text-status-warning-400"
    case "blocked":
      return "bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-700 dark:text-status-danger-400"
    case "deceased":
      return "bg-earth-100 dark:bg-earth-700/50 text-earth-600 dark:text-earth-300"
    default:
      return "bg-earth-100 dark:bg-earth-700/50 text-earth-600 dark:text-earth-300"
  }
}

export function getStatusLabel(status: PatronStatus): string {
  switch (status) {
    case "active":
      return "Active"
    case "suspended":
      return "Suspended"
    case "blocked":
      return "Blocked"
    case "deceased":
      return "Deceased"
    default:
      return "Unknown"
  }
}

export function getStatusDescription(status: PatronStatus): string {
  switch (status) {
    case "active":
      return "Patron can check out items and place holds"
    case "suspended":
      return "Temporarily restricted - may auto-lift when conditions are met"
    case "blocked":
      return "Administratively blocked - requires staff action to unblock"
    case "deceased":
      return "Account restricted - estate follow-up may be required"
    default:
      return "Status unknown"
  }
}

export function getStatusAvatarClasses(status: PatronStatus): { bg: string; icon: string } {
  switch (status) {
    case "active":
      return {
        bg: "bg-lsc-cream dark:bg-lsc-brown/30",
        icon: "text-lsc-rose dark:text-lsc-rose-light",
      }
    case "suspended":
      return {
        bg: "bg-status-warning-100 dark:bg-status-warning-900/30",
        icon: "text-status-warning-600 dark:text-status-warning-400",
      }
    case "blocked":
      return {
        bg: "bg-status-danger-100 dark:bg-status-danger-900/30",
        icon: "text-status-danger-600 dark:text-status-danger-400",
      }
    case "deceased":
      return {
        bg: "bg-earth-100 dark:bg-earth-700/50",
        icon: "text-earth-600 dark:text-earth-300",
      }
    default:
      return {
        bg: "bg-lsc-cream dark:bg-lsc-brown/30",
        icon: "text-lsc-rose dark:text-lsc-rose-light",
      }
  }
}

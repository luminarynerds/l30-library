/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Patron filtering utility functions
 */

import { Patron, PatronStatistics } from "../../../../api/api"
import { StatusFilter } from "../types"

export function getAtRiskPatronIds(
  statistics: PatronStatistics | null,
  activeAlertFilter: "none" | "overdue" | "fines" | "inactive"
): number[] {
  if (!statistics || activeAlertFilter === "none") return []
  switch (activeAlertFilter) {
    case "overdue":
      return statistics.patrons_with_many_overdue.map((p) => p.id)
    case "fines":
      return statistics.patrons_with_high_fines.map((p) => p.id)
    case "inactive":
      return statistics.inactive_patrons.map((p) => p.id)
    default:
      return []
  }
}

export function filterPatronsByAlertStatus(
  patrons: Patron[],
  statistics: PatronStatistics | null,
  activeAlertFilter: "none" | "overdue" | "fines" | "inactive"
): Patron[] {
  const atRiskIds = getAtRiskPatronIds(statistics, activeAlertFilter)
  return activeAlertFilter !== "none"
    ? patrons.filter((p) => atRiskIds.includes(p.id))
    : patrons
}

export function filterPatronsByStatus(
  patrons: Patron[],
  statusFilter: StatusFilter
): Patron[] {
  if (statusFilter === "all") return patrons
  if (statusFilter === "active") return patrons.filter((p) => !p.blocked)
  if (statusFilter === "blocked") return patrons.filter((p) => p.blocked)
  return patrons
}

export function filterPatronsBySearch(
  patrons: Patron[],
  searchQuery: string
): Patron[] {
  if (!searchQuery.trim()) return patrons

  const query = searchQuery.toLowerCase()
  return patrons.filter(
    (patron) =>
      (patron.first_name && patron.first_name.toLowerCase().includes(query)) ||
      (patron.last_name && patron.last_name.toLowerCase().includes(query)) ||
      (patron.email && patron.email.toLowerCase().includes(query)) ||
      (patron.phone && patron.phone.includes(query)) ||
      (patron.library_card_number && patron.library_card_number.includes(query))
  )
}

export function applyAllFilters(
  patrons: Patron[],
  searchQuery: string,
  statusFilter: StatusFilter,
  statistics: PatronStatistics | null,
  activeAlertFilter: "none" | "overdue" | "fines" | "inactive"
): Patron[] {
  let filtered = patrons

  // Apply search filter
  filtered = filterPatronsBySearch(filtered, searchQuery)

  // Apply status filter
  filtered = filterPatronsByStatus(filtered, statusFilter)

  // Apply alert/risk filter
  filtered = filterPatronsByAlertStatus(filtered, statistics, activeAlertFilter)

  return filtered
}

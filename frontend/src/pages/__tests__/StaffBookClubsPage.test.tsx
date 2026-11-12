/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect } from "vitest"
import { STATUS_COLORS, STATUS_COLOR_FALLBACK } from "../StaffBookClubsPage"

// Mirrors backend BookClubStatus enum
// (backend/app/models/book_club.py: BookClubStatus = active | inactive | archived).
const BACKEND_STATUSES = ["active", "inactive", "archived"] as const

describe("StaffBookClubsPage STATUS_COLORS", () => {
  it("has an entry for every BookClubStatus enum value", () => {
    for (const status of BACKEND_STATUSES) {
      expect(STATUS_COLORS[status], `missing color for status "${status}"`).toBeDefined()
    }
  })

  it("maps active to success palette", () => {
    expect(STATUS_COLORS.active).toMatch(/status-success/)
  })

  it("maps inactive to muted earth palette (not draft fallthrough)", () => {
    expect(STATUS_COLORS.inactive).toMatch(/bg-earth-100/)
    expect(STATUS_COLORS.inactive).toMatch(/dark:bg-earth-800/)
  })

  it("maps archived to warning palette", () => {
    expect(STATUS_COLORS.archived).toMatch(/status-warning/)
  })

  it("does not define a 'draft' entry (no such backend status)", () => {
    expect(STATUS_COLORS.draft).toBeUndefined()
  })

  it("fallback for unknown statuses is defined and resolves to the inactive palette", () => {
    expect(STATUS_COLOR_FALLBACK).toBe(STATUS_COLORS.inactive)
    const unknown = "totally_made_up_status"
    expect(STATUS_COLORS[unknown] ?? STATUS_COLOR_FALLBACK).toBe(STATUS_COLORS.inactive)
  })
})

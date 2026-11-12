/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect } from "vitest"
import { expirySeverity } from "@/pages/staff/patrons/utils/patronChipSeverity"

describe("expirySeverity", () => {
  // Fixed reference date so this never flakes around timezone boundaries.
  const now = new Date("2026-05-17T12:00:00Z").getTime()

  it("returns 'default' when the card has no expiry", () => {
    expect(expirySeverity(null, now)).toBe("default")
    expect(expirySeverity(undefined, now)).toBe("default")
    expect(expirySeverity("", now)).toBe("default")
  })

  it("returns 'default' for a malformed date", () => {
    expect(expirySeverity("not-a-date", now)).toBe("default")
  })

  it("returns 'error' when the card has already expired", () => {
    expect(expirySeverity("2026-05-16T12:00:00Z", now)).toBe("error")
    expect(expirySeverity("2025-01-01T00:00:00Z", now)).toBe("error")
  })

  it("returns 'error' for an expiry today (daysUntil <= 0)", () => {
    expect(expirySeverity("2026-05-17T11:00:00Z", now)).toBe("error")
  })

  it("returns 'warning' for an expiry within 30 days", () => {
    expect(expirySeverity("2026-05-25T12:00:00Z", now)).toBe("warning")
    expect(expirySeverity("2026-06-15T12:00:00Z", now)).toBe("warning")
  })

  it("returns 'default' for an expiry beyond 30 days", () => {
    expect(expirySeverity("2026-08-01T12:00:00Z", now)).toBe("default")
    expect(expirySeverity("2030-01-01T12:00:00Z", now)).toBe("default")
  })
})

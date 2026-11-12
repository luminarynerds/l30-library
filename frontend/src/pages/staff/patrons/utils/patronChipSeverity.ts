/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
// Severity logic for the patron-header chip row. Lives outside the page so
// the rules are independently unit-testable -- the chip wall has bitten
// staff before when a "calm" expiry quietly turned urgent overnight.

export type ChipSeverity = "default" | "warning" | "error"

export function expirySeverity(
  cardExpiresAt: string | null | undefined,
  now: number = Date.now()
): ChipSeverity {
  if (!cardExpiresAt) return "default"
  const expiry = new Date(cardExpiresAt).getTime()
  if (Number.isNaN(expiry)) return "default"
  const daysUntil = Math.ceil((expiry - now) / (1000 * 60 * 60 * 24))
  if (daysUntil <= 0) return "error"
  if (daysUntil <= 30) return "warning"
  return "default"
}

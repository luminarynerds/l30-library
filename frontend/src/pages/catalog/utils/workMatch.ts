/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */

/**
 * Case-insensitive, trimmed, whitespace-collapsed comparison key for
 * deciding whether two records describe the same work. Matching must be
 * exact normalized title AND author -- substring matching previously fed
 * wrong-work formats into the hold modal (see useRelatedFormats).
 */
export function normalizeWorkKey(value: string | null | undefined): string {
  return (value ?? "").trim().toLowerCase().replace(/\s+/g, " ")
}

/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Public log of corrected AI mistakes — hallucinations, misattributions,
 * missed handoffs. The maintainer edits this file directly to add new entries.
 *
 * Add a new entry by prepending an object to the `wrongnessLog` array.
 * Keep entries in reverse chronological order (newest first).
 *
 * Entries are plain strings (not i18n keys) so this stays a single source of
 * truth and edits are one-file commits. Section chrome (heading, lead copy,
 * empty state, page-reviewed date) IS translated.
 */

export interface WrongnessEntry {
  /** ISO date YYYY-MM-DD. Rendered in a <time datetime="..."> element. */
  date: string
  /** Which AI surface got it wrong, e.g. "Ask Ernie", "What Should I Read Next?". */
  tool: string
  /** What the AI got wrong. Keep to <= 200 chars; one fact per entry. */
  summary: string
  /** What's actually true, or how the record was corrected. */
  correction: string
  /** Optional: what the team changed in response (prompt edit, KB update, escalation rule). */
  response?: string
}

export const wrongnessLog: WrongnessEntry[] = [
  // No entries yet. When we find a mistake worth publishing, prepend it here.
  // Keep newest-first. Don't backfill; entries are for things we noticed and
  // corrected, not a comprehensive audit.
]

/** Date this section was last reviewed by a human. ISO YYYY-MM-DD. */
export const wrongnessLogReviewedDate = '2026-05-24'

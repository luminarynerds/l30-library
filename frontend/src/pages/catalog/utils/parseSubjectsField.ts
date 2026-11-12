/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Mirror of the backend ``parse_subjects_field`` helper in
 * ``backend/app/services/catalog_subjects.py``.
 *
 * The ``catalog_items.subjects`` column has accumulated three shapes across
 * the table's history:
 *
 * - comma-delimited:        ``"Fiction, Memoir"``
 * - semicolon-delimited:    ``"Fiction; Memoir"``
 * - Python array literal:   ``"['Fiction', 'Memoir']"``
 *
 * Frontend callers (most notably the patron sidebar's ``itemMatchesTopic``
 * fallback when SQL didn't already pre-narrow) need to handle all three so
 * patrons toggling "Sci-Fi" or "LGBTQ+" don't silently miss items whose
 * subjects field is in a non-comma shape.
 */

export function parseSubjectsField(raw: string | null | undefined): string[] {
  if (!raw) return []
  const text = raw.trim()
  if (text === '') return []

  // Array-literal shape -- try to read both single- and double-quoted forms.
  if (text.startsWith('[') && text.endsWith(']')) {
    const inner = text.slice(1, -1).trim()
    // Empty list literal (``[]`` or ``[   ]``) is a real signal that the
    // row carries no subjects, NOT a fallback to the bracket-wrapped raw
    // text path.
    if (inner === '') return []
    // Quoted-string list: ``'Fiction','Memoir'`` or ``"Fiction","Memoir"``.
    const matches = inner.match(/(["'])(?:\\.|(?!\1).)*\1/g)
    if (matches !== null && matches.length > 0) {
      return matches
        .map((m) => m.slice(1, -1).trim())
        .filter((s) => s !== '')
    }
  }

  return text
    .split(/[,;]/)
    .map((s) => s.trim())
    .filter((s) => s !== '')
}

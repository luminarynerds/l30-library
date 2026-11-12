/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
export const AGE_RANGES = [
  { value: '0-5', label: 'Child (0-5)' },
  { value: '6-12', label: 'Child (6-12)' },
  { value: '13-17', label: 'Teen (13-17)' },
  { value: '18-34', label: 'Adult (18-34)' },
  { value: '35-54', label: 'Adult (35-54)' },
  { value: '55-64', label: 'Adult (55-64)' },
  { value: '65+', label: 'Senior (65+)' },
  { value: 'unknown', label: 'Unknown' },
]

export const METHOD_LABELS: Record<string, string> = {
  qr_code: 'QR Code',
  library_card: 'Library Card',
  walk_in: 'Walk-In',
  head_count: 'Head Count',
  pre_registered: 'Pre-Registered',
}

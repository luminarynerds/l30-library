/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Capacity-signal helpers for book club cards/rows.
 *
 * Kept out of page components so they are unit-testable and so the page
 * files do not accrue non-component exports (react-refresh).
 *
 * Field names match the live PR #914 patron API
 * (`backend/app/schemas/book_club_patron.py`): `current_member_count`,
 * `max_members`, `waitlist_count`, `is_full`.
 */
import { t } from '@/i18n'

export interface CapacityInput {
  currentMemberCount: number
  maxMembers: number | null | undefined
  waitlistCount: number
  isFull: boolean
}

export function patronCapacityBadge(
  input: CapacityInput,
  waitlistFlagEnabled: boolean,
): string | null {
  const { currentMemberCount, maxMembers, waitlistCount, isFull } = input
  if (maxMembers == null) return null
  if (isFull) {
    if (waitlistFlagEnabled && waitlistCount > 0) {
      return t('bookClubs.capacity.fullWithWaiting', { count: waitlistCount })
    }
    return t('bookClubs.capacity.full')
  }
  return t('bookClubs.capacity.members', {
    count: currentMemberCount,
    max: maxMembers,
  })
}

export type CapacityTone = 'none' | 'normal' | 'warn' | 'full'

export function staffCapacityTone(
  currentMemberCount: number,
  maxMembers: number | null | undefined,
): CapacityTone {
  if (maxMembers == null || maxMembers <= 0) return 'none'
  if (currentMemberCount >= maxMembers) return 'full'
  if (currentMemberCount / maxMembers >= 0.8) return 'warn'
  return 'normal'
}

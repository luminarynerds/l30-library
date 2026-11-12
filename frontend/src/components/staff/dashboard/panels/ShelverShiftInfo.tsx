/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { ShiftInfo } from '@/api/staff-api/shelver-dashboard'

interface Props {
  firstName: string
  shift: ShiftInfo | null
}

export default function ShelverShiftInfo({ firstName, shift }: Props) {
  if (!shift) {
    return (
      <div className="py-4">
        <p className="text-lg font-serif text-lsc-dark dark:text-lsc-cream">
          Hi {firstName}. No shift scheduled today.
        </p>
      </div>
    )
  }

  const hours = Math.round(shift.scheduled_hours)

  return (
    <div className="py-4">
      <p className="text-lg font-serif text-lsc-dark dark:text-lsc-cream">
        Hi {firstName}. Your assignments for this {hours}hr shift:
      </p>
      <p className="text-sm text-lsc-dark/50 dark:text-lsc-cream/50 mt-1">
        {shift.scheduled_start} -- {shift.scheduled_end}
      </p>
    </div>
  )
}

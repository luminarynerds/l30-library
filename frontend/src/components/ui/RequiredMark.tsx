/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
export function RequiredMark({ className = '' }: { className?: string }) {
  return (
    <span aria-hidden="true" className={`text-status-danger-600 ${className}`}>
      *
    </span>
  )
}

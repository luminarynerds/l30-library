/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { X } from 'lucide-react'

interface FilterChipProps {
  label: string
  onRemove: () => void
}

export default function FilterChip({ label, onRemove }: FilterChipProps): React.ReactElement {
  return (
    <span className="inline-flex items-center gap-1 px-3 py-2 bg-lsc-rose/10 text-lsc-rose rounded-full text-sm">
      {label}
      <button
        onClick={onRemove}
        className="hover:bg-lsc-rose/20 rounded-full p-2 min-w-[32px] min-h-[32px] flex items-center justify-center -mr-1 touch-manipulation"
        aria-label={`Remove ${label} filter`}
      >
        <X className="w-4 h-4" aria-hidden="true" />
      </button>
    </span>
  )
}

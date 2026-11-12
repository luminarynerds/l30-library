/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Loader2, LayoutGrid } from "lucide-react"

interface HoldShelfHeaderProps {
  batchAssigning: boolean
  onBatchAssign: () => void
}

export function HoldShelfHeader({ batchAssigning, onBatchAssign }: HoldShelfHeaderProps) {
  return (
    <div className="mb-8 flex items-start justify-between">
      <div>
        <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
          Smart Hold Shelf
        </h1>
        <p className="mt-2 text-lsc-dark/70 dark:text-lsc-cream/70">
          Automated shelf management with slot assignment, QR pickup, and expiry tracking
        </p>
      </div>
      <div className="flex gap-2">
        <button
          onClick={onBatchAssign}
          disabled={batchAssigning}
          className="flex items-center gap-2 px-4 py-2 bg-status-success-50 dark:bg-status-success-900/20 text-status-success-700 dark:text-status-success-300 rounded-lg hover:bg-status-success-100 transition-colors disabled:opacity-50"
        >
          {batchAssigning ? (
            <Loader2 className="h-4 w-4 motion-safe:animate-spin" />
          ) : (
            <LayoutGrid className="h-4 w-4" />
          )}
          Assign All Slots
        </button>
      </div>
    </div>
  )
}

/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { CheckCircle2 } from "lucide-react"

export function EmptyState() {
  return (
    <div className="rounded-lg border border-lsc-border dark:border-earth-700 p-12 text-center">
      <CheckCircle2 className="h-12 w-12 text-earth-300 mx-auto mb-4" />
      <p className="font-serif text-lsc-dark/70 dark:text-lsc-cream/70 font-medium">
        No ready holds at this time
      </p>
      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
        All patrons have picked up their items
      </p>
    </div>
  )
}

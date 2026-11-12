/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Star } from "lucide-react"

export function RatingBar({ rating, count, total }: { rating: number; count: number; total: number }) {
  const pct = total > 0 ? Math.round((count / total) * 100) : 0
  return (
    <div className="flex items-center gap-2 text-sm">
      <div className="flex items-center gap-1 w-12">
        {Array.from({ length: rating }).map((_, i) => (
          <Star key={i} className="w-3 h-3 text-status-warning-500 fill-yellow-500" />
        ))}
      </div>
      <div className="flex-1 bg-lsc-border dark:bg-earth-700 rounded-full h-1.5">
        <div className="bg-status-warning-500 h-1.5 rounded-full" style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 w-10 text-right">{count}</span>
    </div>
  )
}

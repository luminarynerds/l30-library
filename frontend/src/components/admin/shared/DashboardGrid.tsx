/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import type { ReactNode } from 'react'

interface DashboardGridProps {
  label: string
  loading?: boolean
  skeletonCount?: number
  children: ReactNode
}

export function DashboardGrid({ label, loading, skeletonCount = 6, children }: DashboardGridProps) {
  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4" aria-busy="true" aria-label={`Loading ${label}`}>
        {Array.from({ length: skeletonCount }).map((_, i) => (
          <div key={i} className="h-44 bg-lsc-cream/50 dark:bg-earth-800 rounded-xl motion-safe:animate-pulse" />
        ))}
      </div>
    )
  }

  return (
    <nav aria-label={label}>
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {children}
      </div>
    </nav>
  )
}

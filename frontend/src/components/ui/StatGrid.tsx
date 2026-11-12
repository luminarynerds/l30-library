/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React from 'react'

export interface StatGridProps {
  children: React.ReactNode
  columns?: 2 | 3 | 4 | 5
  className?: string
}

const columnClasses: Record<number, string> = {
  2: 'grid grid-cols-1 sm:grid-cols-2 gap-4',
  3: 'grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4',
  4: 'grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4',
  5: 'grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-4',
}

export function StatGrid({ children, columns = 4, className = '' }: StatGridProps) {
  return (
    <div className={`${columnClasses[columns]} ${className}`}>
      {children}
    </div>
  )
}

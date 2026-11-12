/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React from 'react'

export interface SettingsCardProps {
  title: string
  icon?: React.ElementType
  description?: React.ReactNode
  children: React.ReactNode
}

export function SettingsCard({
  title,
  icon: Icon,
  description,
  children,
}: SettingsCardProps): React.ReactElement {
  return (
    <section className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm p-6 space-y-4 border border-lsc-border dark:border-earth-700">
      <div className="flex items-start gap-2">
        {Icon && (
          <Icon className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light mt-0.5 shrink-0" aria-hidden="true" />
        )}
        <div className="min-w-0">
          <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">{title}</h2>
          {description && (
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">{description}</p>
          )}
        </div>
      </div>
      {children}
    </section>
  )
}

export interface SettingsGridProps {
  children: React.ReactNode
  cols?: 1 | 2 | 3
}

const GRID: Record<NonNullable<SettingsGridProps['cols']>, string> = {
  1: 'grid-cols-1',
  2: 'grid-cols-1 md:grid-cols-2',
  3: 'grid-cols-1 md:grid-cols-3',
}

export function SettingsGrid({ children, cols = 2 }: SettingsGridProps): React.ReactElement {
  return <div className={`grid gap-4 ${GRID[cols]}`}>{children}</div>
}

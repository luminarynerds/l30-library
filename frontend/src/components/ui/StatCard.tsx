/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React from 'react'

// Palette synced 2026-05-17: accepts semantic names (accent/success/warning/
// danger/category) and the legacy literal palette (blue/green/amber/red/purple/
// orange/earth) used elsewhere in the codebase, so call sites that mix
// vocabularies type-check without a separate runtime mapper.
export type StatCardColor =
  | 'accent' | 'success' | 'warning' | 'danger' | 'category'
  | 'blue' | 'green' | 'amber' | 'red' | 'purple' | 'orange' | 'earth'

export interface StatCardProps {
  title: string
  value: string | number
  icon: React.ElementType
  trend?: { value: number; label?: string }
  color?: StatCardColor
  className?: string
  onClick?: () => void
}

const iconColorClasses: Record<StatCardColor, string> = {
  accent: 'bg-earth-100 text-lsc-rose dark:text-lsc-rose-light dark:bg-earth-800/30',
  success: 'bg-status-success-100 text-status-success-600 dark:bg-status-success-900/30 dark:text-status-success-400',
  warning: 'bg-status-warning-100 text-status-warning-600 dark:bg-status-warning-900/30 dark:text-status-warning-400',
  danger: 'bg-status-danger-100 text-status-danger-600 dark:bg-status-danger-900/30 dark:text-status-danger-400',
  category: 'bg-category-100 text-category-600 dark:bg-category-900/30 dark:text-category-400',
  // Legacy literal aliases mapping to the semantic palette above
  blue: 'bg-earth-100 text-lsc-rose dark:text-lsc-rose-light dark:bg-earth-800/30',
  green: 'bg-status-success-100 text-status-success-600 dark:bg-status-success-900/30 dark:text-status-success-400',
  amber: 'bg-status-warning-100 text-status-warning-600 dark:bg-status-warning-900/30 dark:text-status-warning-400',
  red: 'bg-status-danger-100 text-status-danger-600 dark:bg-status-danger-900/30 dark:text-status-danger-400',
  purple: 'bg-category-100 text-category-600 dark:bg-category-900/30 dark:text-category-400',
  orange: 'bg-status-warning-100 text-status-warning-600 dark:bg-status-warning-900/30 dark:text-status-warning-400',
  earth: 'bg-earth-100 dark:bg-earth-700/30 text-lsc-dark/70 dark:text-lsc-cream/70',
}

export function StatCard({
  title,
  value,
  icon: Icon,
  trend,
  color = 'accent',
  className = '',
  onClick,
}: StatCardProps) {
  const Component = onClick ? 'button' : 'div'

  return (
    <Component
      className={`bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm p-6 border border-lsc-border dark:border-earth-700 text-left ${
        onClick ? 'cursor-pointer hover:shadow-md hover:border-lsc-rose/50 transition-all' : ''
      } ${className}`}
      onClick={onClick}
    >
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{title}</p>
          <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream mt-1">{value}</p>
          {trend && (
            <p className={`text-xs mt-1 ${trend.value >= 0 ? 'text-status-success-600 dark:text-status-success-400' : 'text-status-danger-600 dark:text-status-danger-400'}`}>
              {trend.value >= 0 ? '+' : ''}{trend.value}%{trend.label ? ` ${trend.label}` : ''}
            </p>
          )}
        </div>
        <div className={`p-3 rounded-full ${iconColorClasses[color]}`}>
          <Icon className="w-6 h-6" />
        </div>
      </div>
    </Component>
  )
}

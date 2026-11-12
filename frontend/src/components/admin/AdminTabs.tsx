/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React from 'react'
import { clsx } from '../../utils/helpers'

export interface AdminTab<TId extends string = string> {
  id: TId
  label: string
  icon?: React.ElementType
  count?: number
  disabled?: boolean
}

export interface AdminTabsProps<TId extends string = string> {
  tabs: ReadonlyArray<AdminTab<TId>>
  active: TId
  onChange: (id: TId) => void
  ariaLabel?: string
}

export function AdminTabs<TId extends string = string>({
  tabs,
  active,
  onChange,
  ariaLabel,
}: AdminTabsProps<TId>): React.ReactElement {
  return (
    <div
      role="tablist"
      aria-label={ariaLabel}
      className="flex gap-4 border-b border-lsc-border dark:border-earth-700 overflow-x-auto"
    >
      {tabs.map((tab) => {
        const Icon = tab.icon
        const isActive = tab.id === active
        return (
          <button
            key={tab.id}
            type="button"
            role="tab"
            aria-selected={isActive}
            aria-controls={`admin-tabpanel-${tab.id}`}
            id={`admin-tab-${tab.id}`}
            disabled={tab.disabled}
            onClick={() => !tab.disabled && onChange(tab.id)}
            className={clsx(
              'flex items-center gap-2 px-4 py-3 text-sm font-medium whitespace-nowrap transition-colors border-b-2 -mb-px',
              isActive
                ? 'text-lsc-rose border-lsc-rose dark:text-lsc-rose-light dark:border-lsc-rose-light'
                : 'text-lsc-dark/70 border-transparent hover:text-lsc-dark hover:border-lsc-border dark:text-lsc-cream/60 dark:hover:text-lsc-cream',
              tab.disabled && 'opacity-50 cursor-not-allowed',
            )}
          >
            {Icon && <Icon className="h-4 w-4" aria-hidden="true" />}
            <span>{tab.label}</span>
            {typeof tab.count === 'number' && (
              <span
                className={clsx(
                  'inline-flex items-center justify-center px-2 py-0.5 text-xs font-semibold rounded-full',
                  isActive
                    ? 'bg-lsc-rose/10 text-lsc-rose dark:bg-lsc-rose-light/20 dark:text-lsc-rose-light'
                    : 'bg-earth-100 text-earth-700 dark:bg-earth-700 dark:text-earth-200',
                )}
              >
                {tab.count}
              </span>
            )}
          </button>
        )
      })}
    </div>
  )
}

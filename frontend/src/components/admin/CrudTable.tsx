/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React from 'react'
import { RefreshCw } from 'lucide-react'
import { clsx } from '../../utils/helpers'

export interface CrudTableColumn<T> {
  key: string
  header: React.ReactNode
  render: (row: T) => React.ReactNode
  align?: 'left' | 'right' | 'center'
  width?: string
  className?: string
}

export interface CrudTableAction<T> {
  label: string
  icon: React.ElementType
  onClick: (row: T) => void
  tone?: 'default' | 'primary' | 'danger'
  disabled?: (row: T) => boolean
  ariaLabel?: (row: T) => string
}

export interface CrudTableProps<T> {
  rows: ReadonlyArray<T> | undefined
  columns: ReadonlyArray<CrudTableColumn<T>>
  actions?: ReadonlyArray<CrudTableAction<T>>
  getRowKey: (row: T) => string | number
  loading?: boolean
  emptyLabel?: React.ReactNode
  emptyIcon?: React.ElementType
  ariaLabel?: string
}

const ALIGN_CLASSES: Record<NonNullable<CrudTableColumn<unknown>['align']>, string> = {
  left: 'text-left',
  right: 'text-right',
  center: 'text-center',
}

const ACTION_TONE: Record<NonNullable<CrudTableAction<unknown>['tone']>, string> = {
  default: 'text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose',
  primary: 'text-lsc-rose hover:text-lsc-rose/80',
  danger: 'text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-status-danger-600',
}

export function CrudTable<T>({
  rows,
  columns,
  actions,
  getRowKey,
  loading = false,
  emptyLabel = 'No records found.',
  emptyIcon: EmptyIcon,
  ariaLabel,
}: CrudTableProps<T>): React.ReactElement {
  if (loading) {
    return (
      <div className="flex justify-center py-12 bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700">
        <RefreshCw
          className="h-8 w-8 text-lsc-rose dark:text-lsc-rose-light motion-safe:animate-spin"
          aria-hidden="true"
        />
      </div>
    )
  }

  if (!rows || rows.length === 0) {
    return (
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 py-12 text-center">
        {EmptyIcon && (
          <EmptyIcon
            className="h-12 w-12 mx-auto text-earth-600 dark:text-earth-400 mb-3"
            aria-hidden="true"
          />
        )}
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{emptyLabel}</p>
      </div>
    )
  }

  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full" aria-label={ariaLabel}>
          <thead className="bg-earth-50 dark:bg-earth-700">
            <tr>
              {columns.map((col) => (
                <th
                  key={col.key}
                  scope="col"
                  style={col.width ? { width: col.width } : undefined}
                  className={clsx(
                    'px-4 py-3 text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase tracking-wider',
                    ALIGN_CLASSES[col.align ?? 'left'],
                    col.className,
                  )}
                >
                  {col.header}
                </th>
              ))}
              {actions && actions.length > 0 && (
                <th
                  scope="col"
                  className="px-4 py-3 text-right text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase tracking-wider"
                >
                  Actions
                </th>
              )}
            </tr>
          </thead>
          <tbody className="divide-y divide-lsc-border dark:divide-earth-700">
            {rows.map((row) => (
              <tr
                key={getRowKey(row)}
                className="hover:bg-earth-50 dark:bg-earth-900 dark:hover:bg-earth-700/50"
              >
                {columns.map((col) => (
                  <td
                    key={col.key}
                    className={clsx('px-4 py-4 text-sm', ALIGN_CLASSES[col.align ?? 'left'])}
                  >
                    {col.render(row)}
                  </td>
                ))}
                {actions && actions.length > 0 && (
                  <td className="px-4 py-4">
                    <div className="flex items-center justify-end gap-2">
                      {actions.map((action) => {
                        const Icon = action.icon
                        const isDisabled = action.disabled?.(row) ?? false
                        return (
                          <button
                            key={action.label}
                            type="button"
                            onClick={() => action.onClick(row)}
                            disabled={isDisabled}
                            aria-label={action.ariaLabel?.(row) ?? action.label}
                            title={action.label}
                            className={clsx(
                              'p-2 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed',
                              ACTION_TONE[action.tone ?? 'default'],
                            )}
                          >
                            <Icon className="h-4 w-4" aria-hidden="true" />
                          </button>
                        )
                      })}
                    </div>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

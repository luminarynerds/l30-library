/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React, { useState, useEffect } from 'react'
import { clsx } from '../../../utils/helpers'

export interface DiffFieldProps {
  label: string
  description?: React.ReactNode
  value: number
  beforeValue: number
  onChange: (next: number) => void
  type?: 'number' | 'currency'
  min?: number
  max?: number
  step?: number
  unit?: string
  formatCurrency?: (n: number) => string
  id?: string
}

const defaultCurrencyFormat = (n: number): string =>
  new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(n)

export function DiffField({
  label,
  description,
  value,
  beforeValue,
  onChange,
  type = 'number',
  min,
  max,
  step,
  unit,
  formatCurrency = defaultCurrencyFormat,
  id,
}: DiffFieldProps): React.ReactElement {
  const isChanged = value !== beforeValue
  const inputId = id ?? `difffield-${label.replace(/\s+/g, '-').toLowerCase()}`
  const format = type === 'currency' ? formatCurrency : (n: number) => String(n)
  const [rawValue, setRawValue] = useState(String(value))

  useEffect(() => {
    setRawValue(String(value))
  }, [value])

  return (
    <div
      className={clsx(
        'border rounded-lg p-4 transition-colors',
        isChanged
          ? 'border-status-warning-300 dark:border-status-warning-700 bg-status-warning-50 dark:bg-status-warning-900/20'
          : 'border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800',
      )}
    >
      <label
        htmlFor={inputId}
        className="block text-sm font-semibold text-lsc-dark dark:text-lsc-cream mb-1"
      >
        {label}
        {isChanged && (
          <span className="ml-2 px-2 py-0.5 text-xs bg-status-warning-200 dark:bg-status-warning-700 text-status-warning-900 dark:text-status-warning-100 rounded">
            Modified
          </span>
        )}
      </label>
      {description && (
        <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">{description}</p>
      )}

      {isChanged && (
        <div className="mb-3 p-2 bg-earth-100 dark:bg-earth-700/50 rounded text-xs space-y-1">
          <div className="flex justify-between">
            <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Before:</span>
            <span className="font-semibold text-status-danger-600 dark:text-status-danger-400">
              {format(beforeValue)}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-lsc-dark/70 dark:text-lsc-cream/70">After:</span>
            <span className="font-semibold text-status-success-600 dark:text-status-success-400">
              {format(value)}
            </span>
          </div>
        </div>
      )}

      <div className="flex items-center gap-2">
        {type === 'currency' && (
          <span className="text-lsc-dark/70 dark:text-lsc-cream/70" aria-hidden="true">
            $
          </span>
        )}
        <input
          id={inputId}
          type="number"
          min={min}
          max={max}
          step={step}
          value={rawValue}
          onChange={(e) => setRawValue(e.target.value)}
          onBlur={() => {
            const n = parseFloat(rawValue)
            if (!isNaN(n)) {
              const clamped = Math.min(max ?? n, Math.max(min ?? n, n))
              onChange(clamped)
              setRawValue(String(clamped))
            } else {
              setRawValue(String(value))
            }
          }}
          className="flex-1 px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream text-sm"
        />
        {unit && <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{unit}</span>}
      </div>
    </div>
  )
}

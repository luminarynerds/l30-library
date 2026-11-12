/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React, { useState, useEffect } from 'react'

export interface NumberFieldProps {
  label: string
  value: number
  onChange: (next: number) => void
  min?: number
  max?: number
  step?: number
  help?: React.ReactNode
  unit?: string
  disabled?: boolean
  id?: string
}

export function NumberField({
  label,
  value,
  onChange,
  min,
  max,
  step,
  help,
  unit,
  disabled = false,
  id,
}: NumberFieldProps): React.ReactElement {
  const inputId = id ?? `numfield-${label.replace(/\s+/g, '-').toLowerCase()}`
  const [rawValue, setRawValue] = useState(String(value))

  useEffect(() => {
    setRawValue(String(value))
  }, [value])

  return (
    <div>
      <label
        htmlFor={inputId}
        className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1"
      >
        {label}
        {unit && <span className="text-earth-600 dark:text-earth-400 ml-1">({unit})</span>}
      </label>
      <input
        id={inputId}
        type="number"
        min={min}
        max={max}
        step={step}
        value={rawValue}
        disabled={disabled}
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
        className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent disabled:opacity-50"
      />
      {help && <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">{help}</p>}
    </div>
  )
}

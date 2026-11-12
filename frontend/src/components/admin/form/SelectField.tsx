/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React from 'react'

export interface SelectOption<T extends string | number = string> {
  value: T
  label: string
}

export interface SelectFieldProps<T extends string | number = string> {
  label: string
  value: T
  onChange: (next: T) => void
  options: ReadonlyArray<SelectOption<T>>
  help?: React.ReactNode
  disabled?: boolean
  id?: string
}

export function SelectField<T extends string | number = string>({
  label,
  value,
  onChange,
  options,
  help,
  disabled = false,
  id,
}: SelectFieldProps<T>): React.ReactElement {
  const inputId = id ?? `selectfield-${label.replace(/\s+/g, '-').toLowerCase()}`
  return (
    <div>
      <label
        htmlFor={inputId}
        className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1"
      >
        {label}
      </label>
      <select
        id={inputId}
        value={value}
        disabled={disabled}
        onChange={(e) => {
          const raw = e.target.value
          const parsed = typeof options[0]?.value === 'number' ? (Number(raw) as T) : (raw as T)
          onChange(parsed)
        }}
        className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent disabled:opacity-50"
      >
        {options.map((opt) => (
          <option key={String(opt.value)} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
      {help && <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">{help}</p>}
    </div>
  )
}

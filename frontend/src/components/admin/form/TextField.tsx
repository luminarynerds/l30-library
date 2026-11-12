/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React from 'react'

export interface TextFieldProps {
  label: string
  value: string
  onChange: (next: string) => void
  type?: 'text' | 'email' | 'url' | 'password'
  placeholder?: string
  help?: React.ReactNode
  disabled?: boolean
  id?: string
}

export function TextField({
  label,
  value,
  onChange,
  type = 'text',
  placeholder,
  help,
  disabled = false,
  id,
}: TextFieldProps): React.ReactElement {
  const inputId = id ?? `textfield-${label.replace(/\s+/g, '-').toLowerCase()}`
  return (
    <div>
      <label
        htmlFor={inputId}
        className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1"
      >
        {label}
      </label>
      <input
        id={inputId}
        type={type}
        value={value}
        placeholder={placeholder}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value)}
        className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent disabled:opacity-50"
      />
      {help && <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">{help}</p>}
    </div>
  )
}

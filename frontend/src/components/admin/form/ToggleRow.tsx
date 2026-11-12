/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React from 'react'
import { clsx } from '../../../utils/helpers'

export interface ToggleRowProps {
  label: string
  description?: React.ReactNode
  checked: boolean
  onChange: (next: boolean) => void
  disabled?: boolean
  ariaLabel?: string
}

export function ToggleRow({
  label,
  description,
  checked,
  onChange,
  disabled = false,
  ariaLabel,
}: ToggleRowProps): React.ReactElement {
  return (
    <div className="flex items-center justify-between gap-4 py-3">
      <div className="min-w-0">
        <h3 className="font-medium text-lsc-dark dark:text-lsc-cream">{label}</h3>
        {description && (
          <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{description}</div>
        )}
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        aria-label={ariaLabel ?? label}
        disabled={disabled}
        onClick={() => !disabled && onChange(!checked)}
        className={clsx(
          'relative inline-flex h-6 w-11 items-center rounded-full transition-colors shrink-0',
          checked ? 'bg-lsc-rose dark:bg-lsc-rose-light' : 'bg-earth-200 dark:bg-earth-700',
          disabled && 'opacity-50 cursor-not-allowed',
        )}
      >
        <span
          className={clsx(
            'inline-block h-4 w-4 transform rounded-full bg-lsc-white dark:bg-earth-800 transition-transform',
            checked ? 'translate-x-6' : 'translate-x-1',
          )}
        />
      </button>
    </div>
  )
}

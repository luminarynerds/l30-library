/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React from 'react'
import { t } from '@/i18n'

interface FormInputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  /** Label text */
  label?: string
  /** Error message to display below input */
  error?: string
  /** Show required indicator (*) */
  isRequired?: boolean
  /** Custom className for outer container */
  containerClassName?: string
  /** Custom className for label */
  labelClassName?: string
  /** Custom className for input element */
  inputClassName?: string
  /** Custom className for error message */
  errorClassName?: string
  /** Helper text shown below input (when no error) */
  helperText?: string
  /** Show character count (for inputs with maxLength) */
  showCharCount?: boolean
}

export const FormInput = React.forwardRef<HTMLInputElement, FormInputProps>(
  (
    {
      label,
      error,
      isRequired = false,
      containerClassName = '',
      labelClassName = '',
      inputClassName = '',
      errorClassName = '',
      helperText,
      showCharCount = false,
      id,
      maxLength,
      type = 'text',
      ...inputProps
    },
    ref
  ) => {
    const [charCount, setCharCount] = React.useState(0)

    const baseInputClass =
      'w-full px-4 py-2 rounded-lg border bg-lsc-white dark:bg-earth-700 text-earth-700 dark:text-lsc-cream placeholder-earth-500 dark:placeholder-earth-500 focus:outline-none focus:ring-2 focus:ring-lsc-rose transition-colors'

    const errorInputClass = error
      ? 'border-status-danger-500 dark:border-status-danger-400'
      : 'border-lsc-border dark:border-earth-700'

    const finalInputClassName = inputClassName
      ? `${baseInputClass} ${errorInputClass} ${inputClassName}`
      : `${baseInputClass} ${errorInputClass}`

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
      if (showCharCount) {
        setCharCount(e.target.value.length)
      }
      inputProps.onChange?.(e)
    }

    const errorId = error && id ? `${id}-error` : undefined
    const helperId = helperText && id ? `${id}-helper` : undefined
    const describedBy = [errorId, helperId].filter(Boolean).join(' ') || undefined

    return (
      <div className={containerClassName ? containerClassName : ''}>
        {label && (
          <label
            htmlFor={id}
            className={
              labelClassName ||
              'block text-sm font-semibold text-lsc-dark dark:text-lsc-cream mb-2'
            }
          >
            {label}
            {isRequired && (
              <span className="text-status-danger-600" aria-label={t('aria.addRoleModal.required')}>
                {' '}
                *
              </span>
            )}
          </label>
        )}

        <input
          ref={ref}
          id={id}
          type={type}
          maxLength={maxLength}
          {...inputProps}
          onChange={handleChange}
          aria-invalid={!!error}
          aria-describedby={describedBy}
          className={finalInputClassName}
        />

        {showCharCount && maxLength && (
          <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
            {charCount}/{maxLength}
          </p>
        )}

        {error && (
          <p
            id={errorId}
            role="alert"
            className={
              errorClassName ||
              'text-status-danger-600 dark:text-status-danger-400 text-sm mt-1'
            }
          >
            {error}
          </p>
        )}

        {helperText && (
          <p
            id={helperId}
            className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1"
          >
            {helperText}
          </p>
        )}
      </div>
    )
  }
)

FormInput.displayName = 'FormInput'

export default FormInput

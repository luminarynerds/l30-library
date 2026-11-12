/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * ValidatedInput - Input component with inline validation feedback
 * Supports on-blur validation, success states, error messages, and helper text
 * Follows L30 brand voice guidelines for error messaging
 */

import React, { useState, useCallback } from 'react'
import { Check, AlertCircle, Eye, EyeOff } from 'lucide-react'
import { clsx as cn } from '@/utils/helpers'
import { t } from '@/i18n'

interface ValidatedInputProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'onChange' | 'onBlur'> {
  id: string
  label: string
  value: string
  onChange: (value: string) => void
  onBlur?: (value: string) => void

  // Validation
  validationFn?: (value: string) => string | null
  error?: string
  showSuccessState?: boolean
  validateOnBlur?: boolean

  // Helper text
  helperText?: string

  // Character counter
  showCharacterCount?: boolean

  // Styling
  className?: string
  containerClassName?: string

  // Accessibility
  'aria-describedby'?: string
}

export function ValidatedInput({
  id,
  label,
  type = 'text',
  value,
  onChange,
  onBlur,
  validationFn,
  error: externalError,
  showSuccessState = true,
  validateOnBlur = true,
  helperText,
  showCharacterCount = false,
  className,
  containerClassName,
  required = false,
  maxLength,
  disabled = false,
  placeholder,
  autoComplete,
  autoFocus = false,
  'aria-describedby': ariaDescribedBy,
  ...props
}: ValidatedInputProps): React.ReactElement {
  const [internalError, setInternalError] = useState<string | null>(null)
  const [touched, setTouched] = useState(false)
  const [showPassword, setShowPassword] = useState(false)

  const isPassword = type === 'password'
  const inputType = isPassword && showPassword ? 'text' : type

  const displayError = externalError || internalError
  const isValid = touched && !displayError && value.length > 0
  const showSuccess = showSuccessState && isValid

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onChange(e.target.value)

    // Clear error when user starts typing
    if (internalError) {
      setInternalError(null)
    }
  }

  const handleBlur = useCallback(() => {
    setTouched(true)

    if (validateOnBlur && validationFn) {
      const validationError = validationFn(value)
      setInternalError(validationError)
    }

    onBlur?.(value)
  }, [validateOnBlur, validationFn, value, onBlur])

  const describedBy = [
    displayError && `${id}-error`,
    helperText && `${id}-helper`,
    showCharacterCount && maxLength && `${id}-count`,
    ariaDescribedBy
  ]
    .filter(Boolean)
    .join(' ')

  return (
    <div className={containerClassName}>
      <label
        htmlFor={id}
        className="block text-base font-medium text-lsc-dark dark:text-lsc-cream mb-2"
      >
        {label}
        {required && (
          <span className="text-status-danger-500 ml-1" aria-label={t('aria.addRoleModal.required')}>*</span>
        )}
      </label>

      <div className="relative">
        <input
          id={id}
          type={inputType}
          value={value}
          onChange={handleChange}
          onBlur={handleBlur}
          placeholder={placeholder}
          required={required}
          autoFocus={autoFocus}
          autoComplete={autoComplete}
          maxLength={maxLength}
          disabled={disabled}
          aria-invalid={!!displayError}
          aria-describedby={describedBy || undefined}
          className={cn(
            'w-full px-4 py-3 text-base border-2 rounded-lg',
            'bg-lsc-white dark:bg-lsc-dark text-lsc-dark dark:text-lsc-cream',
            'focus:ring-2 focus:ring-lsc-rose focus:border-transparent',
            'transition-all duration-200',
            displayError && 'border-status-danger-500 dark:border-status-danger-500 pr-10',
            showSuccess && 'border-status-success-500 dark:border-status-success-500 pr-10',
            !displayError && !showSuccess && 'border-lsc-border dark:border-earth-700',
            disabled && 'opacity-50 cursor-not-allowed',
            isPassword && 'pr-12',
            className
          )}
          {...props}
        />

        {/* Success indicator */}
        {showSuccess && (
          <div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none">
            <Check className="w-5 h-5 text-status-success-500" aria-hidden="true" />
            <span className="sr-only">Valid input</span>
          </div>
        )}

        {/* Error indicator */}
        {displayError && !isPassword && (
          <div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none">
            <AlertCircle className="w-5 h-5 text-status-danger-500" aria-hidden="true" />
          </div>
        )}

        {/* Password visibility toggle */}
        {isPassword && (
          <button
            type="button"
            onClick={() => setShowPassword(!showPassword)}
            className="absolute right-3 top-1/2 -translate-y-1/2 z-10 p-2 min-w-[44px] min-h-[44px] flex items-center justify-center text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream rounded touch-manipulation focus:outline-none focus:ring-2 focus:ring-lsc-rose"
            aria-label={showPassword ? 'Hide password' : 'Show password'}
          >
            {showPassword ? (
              <EyeOff className="w-5 h-5" aria-hidden="true" />
            ) : (
              <Eye className="w-5 h-5" aria-hidden="true" />
            )}
          </button>
        )}
      </div>

      {/* Character count */}
      {showCharacterCount && maxLength && (
        <p
          id={`${id}-count`}
          className={cn(
            'mt-1 text-xs text-right',
            value.length > maxLength * 0.9
              ? 'text-status-warning-600 dark:text-status-warning-400 font-medium'
              : 'text-lsc-dark/70 dark:text-lsc-cream/70'
          )}
          aria-live="polite"
        >
          {value.length} / {maxLength} characters
        </p>
      )}

      {/* Error message */}
      {displayError && (
        <div
          id={`${id}-error`}
          role="alert"
          aria-live="polite"
          className="mt-2 flex items-start gap-2 text-sm text-status-danger-600 dark:text-status-danger-400"
        >
          <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" aria-hidden="true" />
          <span>{displayError}</span>
        </div>
      )}

      {/* Helper text */}
      {helperText && !displayError && (
        <p
          id={`${id}-helper`}
          className="mt-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70"
        >
          {helperText}
        </p>
      )}
    </div>
  )
}

export default ValidatedInput

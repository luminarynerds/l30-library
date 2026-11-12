/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
export function validateEmail(value: string): string | null {
  if (!value || !value.trim()) {
    return 'Email is required'
  }

  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  if (!emailRegex.test(value)) {
    return 'Please enter a valid email'
  }

  return null
}

export function validatePassword(value: string): string | null {
  if (!value) {
    return 'Password is required'
  }

  if (value.length < 8) {
    return 'Password must be at least 8 characters'
  }

  if (value.length > 128) {
    return 'Password cannot exceed 128 characters'
  }

  return null
}

export function validateName(value: string, fieldName = 'Name'): string | null {
  if (!value || !value.trim()) {
    return `${fieldName} is required`
  }

  if (value.trim().length < 2) {
    return `${fieldName} must be at least 2 characters`
  }

  if (value.length > 100) {
    return `${fieldName} cannot exceed 100 characters`
  }

  return null
}

export function validateRequired(value: unknown, fieldName = 'Field'): string | null {
  if (value === null || value === undefined || value === '' || (typeof value === 'string' && !value.trim())) {
    return `${fieldName} is required`
  }

  return null
}

export function validateLength(value: string, min: number, max: number, fieldName = 'Field'): string | null {
  if (!value) {
    return null // Use validateRequired separately if field is required
  }

  const length = value.trim().length

  if (length < min) {
    return `${fieldName} must be at least ${min} characters`
  }

  if (length > max) {
    return `${fieldName} cannot exceed ${max} characters`
  }

  return null
}

export type ValidationRules<T> = {
  [K in keyof T]?: (value: T[K]) => string | null
}

export function validateField(
  field: string,
  value: unknown,
  rules: Record<string, (val: unknown) => string | null>
): string | null {
  const rule = rules[field]
  if (!rule) return null
  return rule(value)
}

/**
 * Validate entire form with rules object
 *
 * @example
 * const errors = validateForm(formData, {
 *   email: validateEmail,
 *   password: validatePassword,
 *   name: (val) => validateName(val, 'Full Name')
 * })
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function validateForm<T extends Record<string, any>>(
  data: T,
  rules: ValidationRules<T>
): Record<string, string> {
  const errors: Record<string, string> = {}

  for (const field in rules) {
    const rule = rules[field as keyof T]
    if (rule) {
      const error = rule(data[field])
      if (error) {
        errors[field] = error
      }
    }
  }

  return errors
}

/**
 * Validators object - collection of common validators
 * Use individually or with validateForm
 *
 * @example
 * const errors = validateForm(formData, {
 *   email: VALIDATORS.email,
 *   password: VALIDATORS.password,
 * })
 */
export const VALIDATORS = {
  email: validateEmail,
  password: validatePassword,
  name: validateName,
  required: validateRequired,
  length: validateLength,
}

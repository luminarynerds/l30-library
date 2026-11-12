/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Authentication form validation utilities
 */

import { AUTH_CONFIG, COMMON_PASSWORDS, getCardConfig } from '../constants/authConfig'

export function validateEmail(email: string): { isValid: boolean; error?: string } {
  if (!email) {
    return { isValid: false, error: AUTH_CONFIG.VALIDATION_MESSAGES.EMAIL_REQUIRED }
  }

  // RFC 5321 compliant email regex
  const emailRegex = /^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+$/
  if (!emailRegex.test(email)) {
    return { isValid: false, error: AUTH_CONFIG.VALIDATION_MESSAGES.EMAIL_INVALID }
  }

  // Dot placement in the local part, which the regex above is too loose to
  // catch. The backend (email_validator via pydantic EmailStr) rejects
  // these, so catching them here keeps the failure inline instead of a
  // server-side 422 after submit.
  const localPart = email.slice(0, email.lastIndexOf('@'))
  if (localPart.startsWith('.') || localPart.endsWith('.') || localPart.includes('..')) {
    return { isValid: false, error: AUTH_CONFIG.VALIDATION_MESSAGES.EMAIL_INVALID }
  }

  return { isValid: true }
}

export function validatePassword(
  password: string,
  options: { enforceComplexity?: boolean } = {}
): { isValid: boolean; error?: string } {
  if (!password) {
    return { isValid: false, error: AUTH_CONFIG.VALIDATION_MESSAGES.PASSWORD_REQUIRED }
  }

  if (password.length < AUTH_CONFIG.PASSWORD.MIN_LENGTH) {
    return { isValid: false, error: AUTH_CONFIG.VALIDATION_MESSAGES.PASSWORD_TOO_SHORT }
  }

  if (AUTH_CONFIG.PASSWORD.REQUIRE_DIGIT && !/\d/.test(password)) {
    return { isValid: false, error: AUTH_CONFIG.VALIDATION_MESSAGES.PASSWORD_NEEDS_DIGIT }
  }

  if (options.enforceComplexity) {
    if (AUTH_CONFIG.PASSWORD.REQUIRE_LOWERCASE && !/[a-z]/.test(password)) {
      return { isValid: false, error: AUTH_CONFIG.VALIDATION_MESSAGES.PASSWORD_NEEDS_LOWERCASE }
    }

    if (AUTH_CONFIG.PASSWORD.REQUIRE_UPPERCASE && !/[A-Z]/.test(password)) {
      return { isValid: false, error: AUTH_CONFIG.VALIDATION_MESSAGES.PASSWORD_NEEDS_UPPERCASE }
    }

    if (AUTH_CONFIG.PASSWORD.REQUIRE_SPECIAL_CHAR && !/[!@#$%^&*(),.?":{}|<>]/.test(password)) {
      return { isValid: false, error: AUTH_CONFIG.VALIDATION_MESSAGES.PASSWORD_NEEDS_SPECIAL }
    }
  }

  if (COMMON_PASSWORDS.has(password.toLowerCase())) {
    return { isValid: false, error: AUTH_CONFIG.VALIDATION_MESSAGES.PASSWORD_TOO_COMMON }
  }

  return { isValid: true }
}

export function validatePasswordMatch(
  password: string,
  confirmPassword: string
): { isValid: boolean; error?: string } {
  if (password !== confirmPassword) {
    return { isValid: false, error: AUTH_CONFIG.VALIDATION_MESSAGES.PASSWORD_MISMATCH }
  }

  return { isValid: true }
}

export function validateLibraryCard(card: string, cardPrefix?: string): { isValid: boolean; error?: string } {
  if (!card) {
    return { isValid: false, error: AUTH_CONFIG.VALIDATION_MESSAGES.CARD_REQUIRED }
  }

  const config = cardPrefix ? getCardConfig(cardPrefix) : getCardConfig(AUTH_CONFIG.LIBRARY_CARD.PREFIX)
  if (!config.PATTERN.test(card.toUpperCase())) {
    return { isValid: false, error: config.MESSAGES.CARD_INVALID }
  }

  return { isValid: true }
}


export function validatePin(pin: string): { isValid: boolean; error?: string } {
  if (!pin) {
    return { isValid: false, error: AUTH_CONFIG.VALIDATION_MESSAGES.PIN_REQUIRED }
  }

  const pinRegex = /^\d{4,6}$/
  if (!pinRegex.test(pin)) {
    return { isValid: false, error: AUTH_CONFIG.VALIDATION_MESSAGES.PIN_INVALID }
  }

  return { isValid: true }
}

export function validatePhone(phone: string): { isValid: boolean; error?: string } {
  if (!phone) {
    // Phone is optional, so empty is valid
    return { isValid: true }
  }

  // Count actual digits (remove all non-digit characters)
  const digitsOnly = phone.replace(/\D/g, '');

  // Must have between 10-15 digits
  if (digitsOnly.length < 10 || digitsOnly.length > 15) {
    return { isValid: false, error: "That phone number doesn't look quite right. It should have 10 to 15 digits." }
  }

  // Check overall format (allows spaces, dashes, plus, parentheses)
  const phoneRegex = /^[\d\s+(),-]{10,50}$/
  if (!phoneRegex.test(phone)) {
    return { isValid: false, error: AUTH_CONFIG.VALIDATION_MESSAGES.PHONE_INVALID }
  }

  return { isValid: true }
}

export function validateName(name: string, fieldName: 'first' | 'last'): { isValid: boolean; error?: string } {
  if (!name || name.trim() === '') {
    const message =
      fieldName === 'first'
        ? AUTH_CONFIG.VALIDATION_MESSAGES.FIRST_NAME_REQUIRED
        : AUTH_CONFIG.VALIDATION_MESSAGES.LAST_NAME_REQUIRED
    return { isValid: false, error: message }
  }

  return { isValid: true }
}

export function validateEmailLogin(email: string, password: string): { isValid: boolean; errors: Record<string, string> } {
  const errors: Record<string, string> = {}

  const emailValidation = validateEmail(email)
  if (!emailValidation.isValid && emailValidation.error) {
    errors.email = emailValidation.error
  }

  const passwordValidation = validatePassword(password)
  if (!passwordValidation.isValid && passwordValidation.error) {
    errors.password = passwordValidation.error
  }

  return {
    isValid: Object.keys(errors).length === 0,
    errors,
  }
}

export function validateCardLogin(card: string, pin: string, cardPrefix?: string): { isValid: boolean; errors: Record<string, string> } {
  const errors: Record<string, string> = {}

  const cardValidation = validateLibraryCard(card, cardPrefix)
  if (!cardValidation.isValid && cardValidation.error) {
    errors.card = cardValidation.error
  }

  const pinValidation = validatePin(pin)
  if (!pinValidation.isValid && pinValidation.error) {
    errors.pin = pinValidation.error
  }

  return {
    isValid: Object.keys(errors).length === 0,
    errors,
  }
}

export function validateRegistration(data: {
  first_name: string
  last_name: string
  email: string
  password: string
  phone?: string
  address?: string
}): { isValid: boolean; errors: Record<string, string> } {
  const errors: Record<string, string> = {}

  const firstNameValidation = validateName(data.first_name, 'first')
  if (!firstNameValidation.isValid && firstNameValidation.error) {
    errors.first_name = firstNameValidation.error
  }

  const lastNameValidation = validateName(data.last_name, 'last')
  if (!lastNameValidation.isValid && lastNameValidation.error) {
    errors.last_name = lastNameValidation.error
  }

  const emailValidation = validateEmail(data.email)
  if (!emailValidation.isValid && emailValidation.error) {
    errors.email = emailValidation.error
  }

  const passwordValidation = validatePassword(data.password, { enforceComplexity: true })
  if (!passwordValidation.isValid && passwordValidation.error) {
    errors.password = passwordValidation.error
  }

  if (data.phone) {
    const phoneValidation = validatePhone(data.phone)
    if (!phoneValidation.isValid && phoneValidation.error) {
      errors.phone = phoneValidation.error
    }
  }

  return {
    isValid: Object.keys(errors).length === 0,
    errors,
  }
}

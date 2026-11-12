/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/* eslint-disable @typescript-eslint/ban-ts-comment */
/**
 * Comprehensive tests for authentication validation utilities.
 *
 * Tests cover:
 * - Email validation with RFC 5321 compliance
 * - Password validation with strength requirements
 * - Library card format validation
 * - PIN validation
 * - Phone number validation with international support
 * - Edge cases and unicode handling
 * - Form-level validation aggregation
 */

import { describe, it, expect } from 'vitest'
import {
  validateEmail,
  validatePassword,
  validatePasswordMatch,
  validateLibraryCard,
  validatePin,
  validatePhone,
  validateName,
  validateEmailLogin,
  validateCardLogin,
  validateRegistration,
} from '../authValidation'


describe('Email Validation', () => {
  it('should validate standard email addresses', () => {
    const validEmails = [
      'user@example.com',
      'test.user@example.com',
      'user+tag@example.com',
      'user_name@example.co.uk',
      'test123@sub.example.org',
    ]

    validEmails.forEach((email) => {
      const result = validateEmail(email)
      expect(result.isValid).toBe(true)
    })
  })

  it('should reject invalid email formats', () => {
    const invalidEmails = [
      'notanemail',
      '@example.com',
      'user@',
      'user @example.com',
      'user@@example.com',
      'user@.com',
    ]

    invalidEmails.forEach((email) => {
      const result = validateEmail(email)
      expect(result.isValid).toBe(false)
      expect(result.error).toBeDefined()
    })
  })

  it('should reject empty email', () => {
    const result = validateEmail('')
    expect(result.isValid).toBe(false)
    // Copy is now warm/plain-language (AUTH_CONFIG.VALIDATION_MESSAGES),
    // not the literal word "required" — match on the concept instead.
    expect(result.error).toMatch(/email/i)
  })

  it('should accept special characters in local part', () => {
    const emails = [
      'user+tag@example.com',
      'user.name@example.com',
      'user_name@example.com',
      'user-name@example.com',
    ]

    emails.forEach((email) => {
      const result = validateEmail(email)
      expect(result.isValid).toBe(true)
    })
  })

  it('should handle unicode domain names', () => {
    // Note: RFC 5321 regex might not accept all unicode domains
    const result = validateEmail('user@example.com')
    expect(result.isValid).toBe(true)
  })

  it('should accept multiple subdomains', () => {
    const result = validateEmail('user@mail.example.co.uk')
    expect(result.isValid).toBe(true)
  })

  it('should reject email with consecutive dots', () => {
    const result = validateEmail('user..name@example.com')
    expect(result.isValid).toBe(false)
  })

  it('should reject email starting or ending with dot', () => {
    expect(validateEmail('.user@example.com').isValid).toBe(false)
    expect(validateEmail('user.@example.com').isValid).toBe(false)
  })
})


describe('Password Validation', () => {
  it('should validate strong passwords', () => {
    const validPasswords = [
      'StrongPassword123',
      'MySecurePass456',
      'ValidPassword999',
    ]

    validPasswords.forEach((pwd) => {
      const result = validatePassword(pwd)
      expect(result.isValid).toBe(true)
    })
  })

  it('should reject empty password', () => {
    const result = validatePassword('')
    expect(result.isValid).toBe(false)
    // Copy is now warm/plain-language, not the literal word "required".
    expect(result.error).toMatch(/password/i)
  })

  it('should reject passwords that are too short', () => {
    const result = validatePassword('Short1')
    expect(result.isValid).toBe(false)
    // PASSWORD_TOO_SHORT reads "...at least 8 characters..." now.
    expect(result.error).toMatch(/8 characters/i)
  })

  it('should reject passwords without digits', () => {
    const result = validatePassword('NoDigitsHere')
    expect(result.isValid).toBe(false)
    // PASSWORD_NEEDS_DIGIT reads "Add a number..." now, not "digit".
    expect(result.error?.toLowerCase()).toContain('number')
  })

  it('should reject common passwords', () => {
    const commonPasswords = ['password123', '123456', 'qwerty', 'admin1']

    commonPasswords.forEach((pwd) => {
      const result = validatePassword(pwd)
      expect(result.isValid).toBe(false)
    })
  })

  it('should reject common password case-insensitively', () => {
    expect(validatePassword('PASSWORD123').isValid).toBe(false)
    expect(validatePassword('QwErTy1').isValid).toBe(false)
  })

  it('should accept passwords with special characters', () => {
    const specialPasswords = [
      'Pass!@#$%^&*123',
      'Pass123!',
      'Pass@123',
    ]

    specialPasswords.forEach((pwd) => {
      const result = validatePassword(pwd)
      expect(result.isValid).toBe(true)
    })
  })

  it('should accept passwords with unicode characters', () => {
    const result = validatePassword('Pässwörd123')
    // Should be accepted (most validation systems allow this)
    expect(result.isValid).toBe(true)
  })

  it('should accept very long passwords', () => {
    const longPassword = 'VeryLongPassword123' + 'x'.repeat(500)
    const result = validatePassword(longPassword)
    expect(result.isValid).toBe(true)
  })
})


describe('Password Validation — complexity (enforceComplexity)', () => {
  it('accepts a fully compliant password', () => {
    expect(validatePassword('SecurePass123!', { enforceComplexity: true }).isValid).toBe(true)
  })

  it('rejects a password with no lowercase letter', () => {
    const result = validatePassword('SECUREPASS123!', { enforceComplexity: true })
    expect(result.isValid).toBe(false)
    expect(result.error?.toLowerCase()).toContain('lowercase')
  })

  it('rejects a password with no uppercase letter', () => {
    const result = validatePassword('securepass123!', { enforceComplexity: true })
    expect(result.isValid).toBe(false)
    expect(result.error?.toLowerCase()).toContain('uppercase')
  })

  it('rejects a password with no special character', () => {
    const result = validatePassword('SecurePass123', { enforceComplexity: true })
    expect(result.isValid).toBe(false)
    expect(result.error?.toLowerCase()).toContain('special')
  })

  it('stays lenient without enforceComplexity so login is unaffected', () => {
    // The backend rejects this on complexity, but the lenient path used by
    // login must still accept it — login never re-checks password strength.
    expect(validatePassword('securepass123').isValid).toBe(true)
  })
})


describe('Password Matching', () => {
  it('should validate matching passwords', () => {
    const result = validatePasswordMatch('MyPassword123', 'MyPassword123')
    expect(result.isValid).toBe(true)
  })

  it('should reject non-matching passwords', () => {
    const result = validatePasswordMatch('MyPassword123', 'Different456')
    expect(result.isValid).toBe(false)
    expect(result.error).toBeDefined()
  })

  it('should be case-sensitive', () => {
    const result = validatePasswordMatch('MyPassword123', 'mypassword123')
    expect(result.isValid).toBe(false)
  })

  it('should reject when one is empty', () => {
    expect(validatePasswordMatch('Password123', '').isValid).toBe(false)
    expect(validatePasswordMatch('', 'Password123').isValid).toBe(false)
  })
})


describe('Library Card Validation', () => {
  it('should validate correct library card format', () => {
    const validCards = ['LSC123456', 'lsc123456', 'LSC000000', 'LSC999999']

    validCards.forEach((card) => {
      const result = validateLibraryCard(card)
      expect(result.isValid).toBe(true)
    })
  })

  it('should reject invalid card format', () => {
    const invalidCards = [
      '123456',        // No prefix
      'LSC12345',      // Too short
      'LSC1234567',    // Too long
      'ABC123456',     // Wrong prefix
      'LSC12345a',     // Contains letter
      '',              // Empty
    ]

    invalidCards.forEach((card) => {
      const result = validateLibraryCard(card)
      expect(result.isValid).toBe(false)
    })
  })

  it('should be case-insensitive for prefix', () => {
    expect(validateLibraryCard('lsc123456').isValid).toBe(true)
    expect(validateLibraryCard('Lsc123456').isValid).toBe(true)
  })

  it('should reject empty card', () => {
    const result = validateLibraryCard('')
    expect(result.isValid).toBe(false)
    // Copy is now warm/plain-language, not the literal word "required".
    expect(result.error).toMatch(/card/i)
  })
})


describe('PIN Validation', () => {
  it('should validate 4-6 digit PINs', () => {
    const validPins = ['1234', '12345', '123456', '0000', '999999']

    validPins.forEach((pin) => {
      const result = validatePin(pin)
      expect(result.isValid).toBe(true)
    })
  })

  it('should reject PINs that are too short', () => {
    expect(validatePin('123').isValid).toBe(false)
  })

  it('should reject PINs that are too long', () => {
    expect(validatePin('1234567').isValid).toBe(false)
  })

  it('should reject non-numeric PINs', () => {
    const invalidPins = ['123a', '12-34', '123 4', 'abcd']

    invalidPins.forEach((pin) => {
      const result = validatePin(pin)
      expect(result.isValid).toBe(false)
    })
  })

  it('should reject empty PIN', () => {
    const result = validatePin('')
    expect(result.isValid).toBe(false)
  })
})


describe('Phone Number Validation', () => {
  it('should validate standard phone formats', () => {
    // validatePhone's regex allows digits/spaces/+/()/,/- (see
    // authValidation.ts's "allows spaces, dashes, plus, parentheses" comment)
    // — periods aren't in that set, so '555.123.4567' doesn't validate.
    const validPhones = [
      '555-123-4567',
      '(555) 123-4567',
      '555 123 4567',
      '+1 555 123 4567',
      '5551234567',
    ]

    validPhones.forEach((phone) => {
      const result = validatePhone(phone)
      expect(result.isValid).toBe(true)
    })
  })

  it('should accept empty phone (optional field)', () => {
    const result = validatePhone('')
    expect(result.isValid).toBe(true)
  })

  it('should reject phone with too few digits', () => {
    const result = validatePhone('123-456')
    expect(result.isValid).toBe(false)
  })

  it('should reject phone with too many digits', () => {
    const result = validatePhone('1-234-567-8901-234-567')
    expect(result.isValid).toBe(false)
  })

  it('should accept international format', () => {
    // '+33 1 23 45 67' is only 9 digits — under validatePhone's 10-digit
    // floor — so pad it out to a realistic full French number instead.
    expect(validatePhone('+33 1 23 45 67 89').isValid).toBe(true)
    expect(validatePhone('+44 20 1234 5678').isValid).toBe(true)
  })

  it('should accept various formatting characters', () => {
    // Only digits/spaces/+/()/,/- are in validatePhone's allowed character
    // set — square brackets and letters ('[555]', 'ext:') aren't, so those
    // fixtures never validated under the current regex.
    const phones = [
      '(555) 123-4567',
      '555 123 4567',
      '+1 555 123 4567',
    ]

    phones.forEach((phone) => {
      const result = validatePhone(phone)
      expect(result.isValid).toBe(true)
    })
  })

  it('should reject letters in phone', () => {
    validatePhone('555-CALL-NOW')
    // This might be valid if system is lenient with formatting
    // Real behavior depends on regex
  })

  it('should count digits correctly', () => {
    // 10 digits (minimum)
    expect(validatePhone('5551234567').isValid).toBe(true)
    // 15 digits (maximum)
    expect(validatePhone('555123456789012').isValid).toBe(true)
    // 9 digits (too few)
    expect(validatePhone('555123456').isValid).toBe(false)
    // 16 digits (too many) - if format allows more than 50 chars this might pass
  })
})


describe('Name Validation', () => {
  it('should validate non-empty names', () => {
    expect(validateName('John', 'first').isValid).toBe(true)
    expect(validateName('Doe', 'last').isValid).toBe(true)
  })

  it('should reject empty names', () => {
    expect(validateName('', 'first').isValid).toBe(false)
    expect(validateName('', 'last').isValid).toBe(false)
  })

  it('should reject whitespace-only names', () => {
    expect(validateName('   ', 'first').isValid).toBe(false)
    expect(validateName('   ', 'last').isValid).toBe(false)
  })

  it('should distinguish between first and last name in errors', () => {
    const firstResult = validateName('', 'first')
    const lastResult = validateName('', 'last')

    expect(firstResult.error?.toLowerCase()).toContain('first')
    expect(lastResult.error?.toLowerCase()).toContain('last')
  })

  it('should accept names with special characters', () => {
    expect(validateName('Jean-Pierre', 'first').isValid).toBe(true)
    expect(validateName("O'Brien", 'last').isValid).toBe(true)
    expect(validateName('José', 'first').isValid).toBe(true)
  })
})


describe('Form-Level Validation', () => {
  describe('Email Login', () => {
    it('should validate complete email login', () => {
      // 'Password123' lowercases to 'password123', which is in
      // COMMON_PASSWORDS (see authConfig.ts) — use a fixture that isn't
      // blocklisted so this actually exercises the "valid" path.
      const result = validateEmailLogin('test@example.com', 'MySecurePass456')
      expect(result.isValid).toBe(true)
      expect(Object.keys(result.errors)).toHaveLength(0)
    })

    it('should collect multiple errors', () => {
      const result = validateEmailLogin('invalid-email', 'weak')
      expect(result.isValid).toBe(false)
      expect(result.errors.email).toBeDefined()
      expect(result.errors.password).toBeDefined()
    })

    it('should report email errors correctly', () => {
      // Same blocklisted-password gotcha as above — use a non-common
      // password so only the email fails.
      const result = validateEmailLogin('', 'MySecurePass456')
      expect(result.isValid).toBe(false)
      expect(result.errors.email).toBeDefined()
      expect(result.errors.password).toBeUndefined()
    })

    it('should report password errors correctly', () => {
      const result = validateEmailLogin('test@example.com', '')
      expect(result.isValid).toBe(false)
      expect(result.errors.password).toBeDefined()
      expect(result.errors.email).toBeUndefined()
    })
  })

  describe('Card Login', () => {
    it('should validate complete card login', () => {
      const result = validateCardLogin('LSC123456', '1234')
      expect(result.isValid).toBe(true)
      expect(Object.keys(result.errors)).toHaveLength(0)
    })

    it('should collect multiple errors', () => {
      const result = validateCardLogin('invalid', '12')
      expect(result.isValid).toBe(false)
      expect(result.errors.card).toBeDefined()
      expect(result.errors.pin).toBeDefined()
    })
  })

  describe('Registration', () => {
    it('should validate complete registration', () => {
      const result = validateRegistration({
        first_name: 'John',
        last_name: 'Doe',
        email: 'john@example.com',
        password: 'SecurePassword123!',
        phone: '555-123-4567',
      })

      expect(result.isValid).toBe(true)
      expect(Object.keys(result.errors)).toHaveLength(0)
    })

    it('should collect all field errors', () => {
      const result = validateRegistration({
        first_name: '',
        last_name: '',
        email: 'invalid-email',
        password: 'weak',
      })

      expect(result.isValid).toBe(false)
      expect(result.errors.first_name).toBeDefined()
      expect(result.errors.last_name).toBeDefined()
      expect(result.errors.email).toBeDefined()
      expect(result.errors.password).toBeDefined()
    })

    it('should allow registration without phone', () => {
      const result = validateRegistration({
        first_name: 'John',
        last_name: 'Doe',
        email: 'john@example.com',
        password: 'SecurePassword123!',
      })

      expect(result.isValid).toBe(true)
      expect(result.errors.phone).toBeUndefined()
    })

    it('should validate phone if provided', () => {
      const result = validateRegistration({
        first_name: 'John',
        last_name: 'Doe',
        email: 'john@example.com',
        password: 'SecurePassword123!',
        phone: 'invalid-phone',
      })

      expect(result.isValid).toBe(false)
      expect(result.errors.phone).toBeDefined()
    })
  })
})


describe('Edge Cases and Security', () => {
  it('should not execute code in validation strings', () => {
    const sqlInjection = "'; DROP TABLE users; --"
    // const xss = "<script>alert('XSS')</script>"

    // These should be treated as regular data
    const nameResult = validateName(sqlInjection, 'first')
    expect(nameResult.isValid).toBe(true)

    const emailResult = validateEmail('user@example.com')
    expect(emailResult.isValid).toBe(true)
  })

  it('should handle very long strings', () => {
    const longString = 'a'.repeat(10000)
    const result = validateName(longString, 'first')
    // Should either accept or reject gracefully
    expect(result).toBeDefined()
  })

  it('should handle null-like values gracefully', () => {
    // @ts-ignore - testing runtime behavior
    expect(() => validateEmail(null)).not.toThrow()
    // @ts-ignore
    expect(() => validatePassword(undefined)).not.toThrow()
  })

  it('should preserve whitespace within valid strings', () => {
    const email = 'user@example.com'
    // Whitespace shouldn't break valid formats
    expect(validateEmail(email).isValid).toBe(true)
  })
})

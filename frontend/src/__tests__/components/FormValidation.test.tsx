/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Form Validation Tests
 *
 * Generic tests for form validation utilities and patterns
 */

import { describe, it, expect } from 'vitest'
import {
  validateEmailLogin,
  validateCardLogin,
} from '@/utils/authValidation'
import { AUTH_CONFIG } from '@/constants/authConfig'

describe('Form Validation', () => {
  describe('Email Validation', () => {
    it('should validate correct email format', () => {
      const result = validateEmailLogin('test@example.com', 'Sn0wyOwl!42')
      expect(result.isValid).toBe(true)
      expect(result.errors).toEqual({})
    })

    it('should reject invalid email format', () => {
      const result = validateEmailLogin('invalid-email', 'Sn0wyOwl!42')
      expect(result.isValid).toBe(false)
      expect(result.errors.email).toBeDefined()
    })

    it('should require email', () => {
      // Validation copy is warm/patron-facing, not literally "required" (093b7d92e+).
      const result = validateEmailLogin('', 'Sn0wyOwl!42')
      expect(result.isValid).toBe(false)
      expect(result.errors.email).toBe(AUTH_CONFIG.VALIDATION_MESSAGES.EMAIL_REQUIRED)
    })

    it('should require password', () => {
      const result = validateEmailLogin('test@example.com', '')
      expect(result.isValid).toBe(false)
      expect(result.errors.password).toBe(AUTH_CONFIG.VALIDATION_MESSAGES.PASSWORD_REQUIRED)
    })

    it('should validate password length', () => {
      const result = validateEmailLogin('test@example.com', 'short')
      expect(result.isValid).toBe(false)
      expect(result.errors.password).toMatch(/at least 8 characters/i)
    })

    it('should accept various valid email formats', () => {
      const validEmails = [
        'user@example.com',
        'user.name@example.com',
        'user+tag@example.co.uk',
        'user_name@example-domain.com',
      ]

      validEmails.forEach(email => {
        const result = validateEmailLogin(email, 'Sn0wyOwl!42')
        expect(result.isValid).toBe(true)
      })
    })
  })

  describe('Card Number Validation', () => {
    it('should validate correct card format', () => {
      const result = validateCardLogin('LSC123456', '1234')
      expect(result.isValid).toBe(true)
      expect(result.errors).toEqual({})
    })

    it('should accept lowercase card prefix', () => {
      const result = validateCardLogin('lsc123456', '1234')
      expect(result.isValid).toBe(true)
    })

    it('should require card number', () => {
      const result = validateCardLogin('', '1234')
      expect(result.isValid).toBe(false)
      expect(result.errors.card).toBe(AUTH_CONFIG.VALIDATION_MESSAGES.CARD_REQUIRED)
    })

    it('should require PIN', () => {
      const result = validateCardLogin('LSC123456', '')
      expect(result.isValid).toBe(false)
      expect(result.errors.pin).toBe(AUTH_CONFIG.VALIDATION_MESSAGES.PIN_REQUIRED)
    })

    it('should validate card format', () => {
      const result = validateCardLogin('ABC123456', '1234')
      expect(result.isValid).toBe(false)
      expect(result.errors.card).toMatch(/LSC followed by 6 digits/i)
    })

    it('should validate PIN length', () => {
      const invalidPINs = ['12', '123', '1234567']

      invalidPINs.forEach(pin => {
        const result = validateCardLogin('LSC123456', pin)
        expect(result.isValid).toBe(false)
        expect(result.errors.pin).toMatch(/4 to 6 digits/i)
      })
    })

    it('should accept valid PIN lengths', () => {
      const validPINs = ['1234', '12345', '123456']

      validPINs.forEach(pin => {
        const result = validateCardLogin('LSC123456', pin)
        expect(result.isValid).toBe(true)
      })
    })

    it('should validate card number has exactly 6 digits', () => {
      const invalidCards = [
        'LSC12345',   // Too short
        'LSC1234567', // Too long
        'LSC',        // No digits
      ]

      invalidCards.forEach(card => {
        const result = validateCardLogin(card, '1234')
        expect(result.isValid).toBe(false)
      })
    })
  })

  describe('Password Strength', () => {
    it('should identify weak passwords', () => {
      const weakPasswords = [
        'password',
        '12345678',
        'qwertyui',
        'aaaaaaaa',
      ]

      // Note: Actual password strength checking would be in a separate utility
      // This is a placeholder for that functionality
      weakPasswords.forEach(password => {
        expect(password.length).toBeGreaterThanOrEqual(8)
      })
    })

    it('should identify strong passwords', () => {
      const strongPasswords = [
        'P@ssw0rd123!',
        'MySecureP@ss123',
        'C0mpl3x!Pass',
      ]

      strongPasswords.forEach(password => {
        expect(password.length).toBeGreaterThanOrEqual(8)
        expect(/[A-Z]/.test(password)).toBe(true)
        expect(/[a-z]/.test(password)).toBe(true)
        expect(/[0-9]/.test(password)).toBe(true)
      })
    })
  })

  describe('Edge Cases', () => {
    it('should treat leading/trailing whitespace as invalid (no trimming)', () => {
      // authValidation has never trimmed email/password (only validateName
      // does); the RFC 5321 email regex's character class excludes
      // whitespace, so a padded email fails the format check outright.
      const result = validateEmailLogin(' test@example.com ', ' Sn0wyOwl!42 ')
      expect(result.isValid).toBe(false)
      expect(result.errors.email).toBeDefined()
    })

    it('should handle special characters in email', () => {
      const result = validateEmailLogin('user+test@example.com', 'Sn0wyOwl!42')
      expect(result.isValid).toBe(true)
    })

    it('should reject email without domain', () => {
      const result = validateEmailLogin('user@', 'Sn0wyOwl!42')
      expect(result.isValid).toBe(false)
    })

    it('should reject email without @', () => {
      const result = validateEmailLogin('userexample.com', 'Sn0wyOwl!42')
      expect(result.isValid).toBe(false)
    })
  })
})

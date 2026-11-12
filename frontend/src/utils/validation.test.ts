/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect } from 'vitest'
import { validateEmail } from './validation'

describe('validation.ts — validateEmail', () => {
  it('rejects an empty string as required', () => {
    expect(validateEmail('')).toBe('Email is required')
  })

  it('rejects whitespace-only input as required', () => {
    expect(validateEmail('   ')).toBe('Email is required')
  })

  it('rejects a string with no @ as invalid', () => {
    expect(validateEmail('notanemail')).toBe('Please enter a valid email')
  })

  it('accepts a plain valid email', () => {
    expect(validateEmail('user@example.com')).toBeNull()
  })
})

/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * [SAM-GATE] Documents Dup finding #8: `utils/validation.ts` and
 * `utils/authValidation.ts` each export a `validateEmail`, and they
 * disagree on dot-placement rules. `authValidation.ts` (used by
 * login/registration) rejects leading/trailing/consecutive dots in the
 * local part; `validation.ts`'s looser regex accepts them. An address good
 * enough to pass a form validated with one could fail the other.
 *
 * This test characterizes the current split — it does not pick a canonical
 * regex. That's a product call for the maintainer (which one wins, and does the
 * loser get deleted or reconciled).
 */
import { describe, it, expect } from 'vitest'
import { validateEmail as validateEmailLoose } from '../validation'
import { validateEmail as validateEmailStrict } from '../authValidation'

function looseIsValid(email: string): boolean {
  return validateEmailLoose(email) === null
}

function strictIsValid(email: string): boolean {
  return validateEmailStrict(email).isValid
}

describe('validateEmail divergence between validation.ts and authValidation.ts', () => {
  it.each([
    ['valid@example.com', true, true],
    ['a@b', false, false],
  ])('agree on %s (loose=%s, strict=%s)', (email, expectedLoose, expectedStrict) => {
    expect(looseIsValid(email)).toBe(expectedLoose)
    expect(strictIsValid(email)).toBe(expectedStrict)
  })

  it.each([
    'a..b@example.com',
    '.user@example.com',
    'user.@example.com',
    'user@example..com',
  ])(
    'disagrees on %s — validation.ts accepts it, authValidation.ts rejects it (dot-placement rule)',
    (email) => {
      expect(looseIsValid(email)).toBe(true)
      expect(strictIsValid(email)).toBe(false)
    }
  )
})

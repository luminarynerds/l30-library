/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, expect, it } from 'vitest'

import { toApiDateTime, toDateTimeLocalValue } from './eventDateTime'

describe('eventDateTime', () => {
  it('round-trips datetime-local values through API conversion', () => {
    const localValue = '2026-03-15T10:30'

    const apiValue = toApiDateTime(localValue)
    const formValue = toDateTimeLocalValue(apiValue)

    expect(formValue).toBe(localValue)
  })

  it('keeps invalid values unchanged to avoid destructive edits', () => {
    const invalidValue = 'not-a-datetime'

    expect(toApiDateTime(invalidValue)).toBe(invalidValue)
    expect(toDateTimeLocalValue(invalidValue)).toBe(invalidValue.slice(0, 16))
  })
})

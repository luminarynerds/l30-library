/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, expect, it } from 'vitest'
import { resolveLibraryContact } from './libraryContact'

const branding = { address_line1: 'Old address', address_line2: '', city: 'Old city', state: 'OH', zip_code: '12345', phone: '555-1000' }

describe('library contact source', () => {
  it('uses the main branch consistently instead of conflicting branding', () => {
    const contact = resolveLibraryContact(branding, [
      { branch_type: 'branch', address_line1: 'Other branch', phone: '555-2000' },
      { branch_type: 'main', address_line1: 'Main address', city: 'New city', state: 'ON', zip_code: null, phone: '555-3000' },
    ])
    expect(contact).toEqual({ address_line1: 'Main address', address_line2: '', city: 'New city', state: 'ON', zip_code: '', phone: '555-3000' })
  })

  it('falls back to branding when branch data is unavailable', () => {
    expect(resolveLibraryContact(branding)).toEqual(branding)
    expect(resolveLibraryContact(branding, [])).toEqual(branding)
  })

  it('keeps a branch address together instead of adding branding city or postal code', () => {
    expect(resolveLibraryContact(branding, [{ branch_type: 'main', address_line1: 'Main address' }])).toEqual({
      address_line1: 'Main address', address_line2: '', city: '', state: '', zip_code: '', phone: '555-1000',
    })
  })
})

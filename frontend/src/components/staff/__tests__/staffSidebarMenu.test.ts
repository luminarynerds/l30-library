/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect } from 'vitest'
import { AREAS, FOOTER_ITEMS, ROLE_SIDEBAR_ACCESS, DASHBOARD_PATH } from '../staffSidebarMenu'

describe('staffSidebarMenu — lean rail', () => {
  it('exposes exactly the four default areas plus board, in order', () => {
    expect(AREAS.map((a) => a.path)).toEqual([
      '/staff/front-desk-hub',
      '/staff/collection-hub',
      '/staff/library-hub',
      '/staff/report-hub',
      '/staff/board-hub',
    ])
  })

  it('labels the library-hub area "Programs"', () => {
    expect(AREAS.find((a) => a.path === '/staff/library-hub')?.label).toBe('Programs')
  })

  it('gates each area on the right ability', () => {
    const byPath = Object.fromEntries(AREAS.map((a) => [a.path, a.access]))
    expect(byPath['/staff/front-desk-hub']).toBe('front_desk')
    expect(byPath['/staff/collection-hub']).toBe('collection')
    expect(byPath['/staff/library-hub']).toBe('library_life')
    expect(byPath['/staff/report-hub']).toBe('reports_outreach')
    expect(byPath['/staff/board-hub']).toBe('board')
  })

  it('footer has Admin (configuration) and Help (help)', () => {
    expect(FOOTER_ITEMS.map((f) => [f.label, f.access])).toEqual([
      ['Admin', 'configuration'],
      ['Help', 'help'],
    ])
  })

  it('dashboard path is /staff', () => {
    expect(DASHBOARD_PATH).toBe('/staff')
  })

  it('plain staff can see the four default areas but not board/admin', () => {
    const staff = ROLE_SIDEBAR_ACCESS.staff
    expect(staff).toEqual(expect.arrayContaining(['front_desk', 'collection', 'library_life', 'reports_outreach', 'help']))
    expect(staff).not.toContain('board')
    expect(staff).not.toContain('configuration')
  })
})

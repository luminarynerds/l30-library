/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/// <reference types="@testing-library/jest-dom/vitest" />
import React from 'react'
import { render } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { AdminShell } from '../AdminShell'

vi.mock('@/components/staff/StaffLayout', () => ({
  StaffLayout: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="staff-layout">{children}</div>
  ),
}))
vi.mock('../StaffLayout', () => ({
  StaffLayout: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="staff-layout">{children}</div>
  ),
}))
vi.mock('../../staff/StaffLayout', () => ({
  StaffLayout: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="staff-layout">{children}</div>
  ),
}))

describe('AdminShell', () => {
  it('(a) default maxWidth is max-w-none, not max-w-7xl', () => {
    const { container } = render(
      <AdminShell title="Test">
        <div>content</div>
      </AdminShell>,
    )
    // The content container is the first div inside the StaffLayout render
    const contentDiv = container.querySelector('[class*="mx-auto"]')
    expect(contentDiv).not.toBeNull()
    expect(contentDiv!.className).toContain('max-w-none')
    expect(contentDiv!.className).not.toContain('max-w-7xl')
  })

  it('(b) maxWidth prop overrides default', () => {
    const { container } = render(
      <AdminShell title="Test" maxWidth="max-w-3xl">
        <div>content</div>
      </AdminShell>,
    )
    const contentDiv = container.querySelector('[class*="mx-auto"]')
    expect(contentDiv).not.toBeNull()
    expect(contentDiv!.className).toContain('max-w-3xl')
    expect(contentDiv!.className).not.toContain('max-w-none')
  })
})

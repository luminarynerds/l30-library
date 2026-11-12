/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { format } from 'date-fns'

import {
  todayLocalYMD,
  getStatusConfig,
} from '../parentHomeVisitsHelpers'

describe('ParentHomeVisitsPage helpers', () => {
  it('todayLocalYMD returns the viewer-local date, not UTC', () => {
    // Local clock truth: this is what staff actually see on their wall clock.
    const expected = format(new Date(), 'yyyy-MM-dd')
    expect(todayLocalYMD()).toBe(expected)

    // Sanity: the old broken impl was
    //   new Date().toISOString().split('T')[0]
    // which is the UTC date. In timezones west of UTC after ~5pm local,
    // that value rolls ahead of the local wall-clock date. Confirm our
    // helper does NOT match a UTC-aligned string when the two differ.
    const utcYMD = new Date().toISOString().split('T')[0]
    if (utcYMD !== expected) {
      // Only meaningful when the run happens to straddle midnight UTC.
      expect(todayLocalYMD()).not.toBe(utcYMD)
    }
  })

  it('getStatusConfig falls back to the scheduled config for unknown statuses', () => {
    const known = getStatusConfig('scheduled')
    const unknown = getStatusConfig('some_brand_new_backend_status')
    expect(unknown).toBe(known)
    expect(unknown.color).toMatch(/status-warning/)
    expect(unknown.monoCue).toBeTruthy()
  })

  it('getStatusConfig returns distinct monoCue glyphs for confirmed vs completed', () => {
    // Both are green check-style states, so the a11y fix swaps one to a
    // visually distinct icon AND a distinct non-color cue. Verify that the
    // monochrome cue is different so color-blind, forced-colors-mode, or
    // print-preview users can still tell them apart.
    expect(getStatusConfig('confirmed').monoCue).not.toBe(
      getStatusConfig('completed').monoCue,
    )
  })
})

describe('ParentHomeVisitsPage status badges', () => {
  // Render badges via a minimal harness that mirrors the production JSX 1:1
  // (same role, same aria-label binding, same monoCue span, same color
  // classes). We test at the helper boundary rather than driving the full
  // page through react-query + AdminShell + happy-dom, which is brittle on
  // this project's vitest pool config. If the harness drifts from the
  // production JSX, the page-level snapshot stays in code review.
  function Harness({
    status,
    label,
  }: {
    status: string
    label: string
  }) {
    const config = getStatusConfig(status)
    return (
      <span
        role="status"
        aria-label={label}
        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${config.color}`}
      >
        {config.icon}
        <span
          aria-hidden="true"
          className="font-mono text-[0.85em] leading-none"
        >
          {config.monoCue}
        </span>
        <span>{label}</span>
      </span>
    )
  }

  it('renders confirmed badge with role=status and a localized aria-label', () => {
    render(<Harness status="confirmed" label="Confirmed" />)

    const badge = screen.getByRole('status', { name: 'Confirmed' })
    expect(badge).toBeTruthy()
    // Visible text content is the localized label, not the underscored enum.
    expect(badge.textContent).toContain('Confirmed')
    expect(badge.textContent).not.toContain('_')
    // Decorative icon must be hidden from AT.
    const svg = badge.querySelector('svg')
    expect(svg?.getAttribute('aria-hidden')).toBe('true')
  })

  it('renders completed badge with a localized aria-label that does not collide with confirmed', () => {
    render(
      <div>
        <Harness status="confirmed" label="Confirmed" />
        <Harness status="completed" label="Completed" />
      </div>,
    )

    expect(screen.getByRole('status', { name: 'Confirmed' })).toBeTruthy()
    expect(screen.getByRole('status', { name: 'Completed' })).toBeTruthy()
  })

  it('falls back gracefully when the backend ships an unknown status', () => {
    // Pass a status the frontend has never seen. Production code routes it
    // through `getStatusConfig`, which falls back to the `scheduled` entry
    // rather than crashing with `undefined.color`.
    render(<Harness status="in_transit" label="In transit" />)

    const badge = screen.getByRole('status', { name: 'In transit' })
    expect(badge.className).toMatch(/status-warning/)
    expect(badge.textContent).toContain('In transit')
  })
})

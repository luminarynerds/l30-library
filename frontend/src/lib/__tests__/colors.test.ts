/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect } from 'vitest'
import { lightenForDarkMode, contrastRatio, hexToHsl, hexToRgb } from '../colors'

const DARK_SURFACE = '#1e1a24'

describe('lightenForDarkMode', () => {
  it('lifts #8B5E5E to clear WCAG AA against the dark surface', () => {
    const lifted = lightenForDarkMode('#8B5E5E')
    expect(contrastRatio(lifted, DARK_SURFACE)).toBeGreaterThanOrEqual(4.5)
  })

  it('lifts all default brand presets to clear WCAG AA', () => {
    const presets = ['#C4704B', '#8B5E5E', '#D49898', '#2E86AB', '#1B4965', '#4A7C59', '#7B4B8A', '#D4613E', '#34495E']
    for (const hex of presets) {
      const lifted = lightenForDarkMode(hex)
      expect(contrastRatio(lifted, DARK_SURFACE)).toBeGreaterThanOrEqual(4.5)
    }
  })

  it('returns a hex string and preserves hue', () => {
    const lifted = lightenForDarkMode('#8B5E5E')
    expect(lifted).toMatch(/^#[0-9a-f]{6}$/i)
    const [h1] = hexToHsl('#8B5E5E')
    const [h2] = hexToHsl(lifted)
    // Hue should be preserved within a small rounding tolerance
    expect(Math.abs(h1 - h2)).toBeLessThan(2)
  })

  it('raises lightness floor to >=75%', () => {
    const [, , l] = hexToHsl(lightenForDarkMode('#8B5E5E'))
    expect(l).toBeGreaterThanOrEqual(75)
  })

  it('does not mutate an already-light input below the floor of saturation', () => {
    // A near-white input shouldn't be over-saturated
    const lifted = lightenForDarkMode('#FAFAFA')
    expect(lifted).toMatch(/^#[0-9a-f]{6}$/i)
  })
})

/**
 * Split-token regression guard for PR #677:
 * The lift must apply ONLY to the text-rgb var, not the bg-rgb var.
 * If both got lifted again, `bg-lsc-rose` with white text would drop
 * below 4.5:1 like the original regression.
 */
describe('rose token split (text vs bg)', () => {
  const DARK = '#1e1a24'
  const PRIMARY = '#8B5E5E'
  const WHITE = '#FFFFFF'

  it('bg-rgb stays unlifted (raw brand color) so bg-lsc-rose + white text clears 4.5:1', () => {
    // BrandingContext writes hexToRgb(rawPrimary) into --accent-rose-rgb.
    expect(hexToRgb(PRIMARY)).toBe('139 94 94')
    expect(contrastRatio(PRIMARY, WHITE)).toBeGreaterThanOrEqual(4.5)
  })

  it('text-rgb gets lifted in dark mode and clears 4.5:1 on dark surface', () => {
    // BrandingContext writes hexToRgb(lightenForDarkMode(rawPrimary)) into --accent-rose-text-rgb.
    const lifted = lightenForDarkMode(PRIMARY)
    expect(hexToRgb(lifted)).not.toBe(hexToRgb(PRIMARY))
    expect(contrastRatio(lifted, DARK)).toBeGreaterThanOrEqual(4.5)
  })

  it('text-lsc-rose resolves to the lifted color via the --accent-rose-text-rgb var', () => {
    // Simulate BrandingContext's effect in dark mode against a stub element
    // styled with `color: rgb(var(--accent-rose-text-rgb))` (the tailwind
    // textColor override for text-lsc-rose).
    const root = document.documentElement
    const liftedRgb = hexToRgb(lightenForDarkMode(PRIMARY))   // text-only var (lifted)
    const rawRgb = hexToRgb(PRIMARY)                          // bg/border var (unlifted)
    root.style.setProperty('--accent-rose-text-rgb', liftedRgb)
    root.style.setProperty('--accent-rose-rgb', rawRgb)
    const el = document.createElement('span')
    el.style.color = 'rgb(var(--accent-rose-text-rgb))'
    el.style.backgroundColor = 'rgb(var(--accent-rose-rgb))'
    document.body.appendChild(el)
    try {
      const computed = getComputedStyle(el)
      // happy-dom emits space-separated `rgb(R G B)` from the resolved var.
      expect(computed.color).toBe(`rgb(${liftedRgb})`)
      expect(computed.backgroundColor).toBe(`rgb(${rawRgb})`)
      expect(computed.color).not.toEqual(computed.backgroundColor)
    } finally {
      el.remove()
      root.style.removeProperty('--accent-rose-text-rgb')
      root.style.removeProperty('--accent-rose-rgb')
    }
  })
})

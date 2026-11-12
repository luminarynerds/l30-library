/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fireEvent, render, screen } from '@testing-library/react'
import '@testing-library/jest-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import CatalogDisplayMenu from '../CatalogDisplayMenu'

vi.mock('@/i18n/I18nContext', () => ({
  useTranslation: () => ({
    t: (key: string, fallback?: Record<string, unknown> | string) =>
      typeof fallback === 'string' ? fallback : key,
  }),
}))

// The catalog reading-comfort toggles must drive the SHARED accessibility
// settings (the single source of truth that cssApplicator reads), not a local
// copy. The original standalone button broke because it wrote its own value;
// these tests pin the toggles to updateSetting and to reading state FROM settings.
const updateSetting = vi.fn()
let mockSettings: { dyslexiaFont: boolean; quietMode: boolean }
vi.mock('@/features/accessibility/hooks/useAccessibility', () => ({
  useAccessibility: () => ({ settings: mockSettings, updateSetting }),
}))

function openMenu() {
  fireEvent.click(screen.getByRole('button', { name: /Display/i }))
}

describe('CatalogDisplayMenu', () => {
  beforeEach(() => {
    updateSetting.mockClear()
    mockSettings = { dyslexiaFont: false, quietMode: false }
  })

  it('dyslexia switch reflects settings.dyslexiaFont (off)', () => {
    render(<CatalogDisplayMenu hideCovers={false} onToggleHideCovers={() => {}} onResetCovers={() => {}} />)
    openMenu()
    expect(screen.getByRole('switch', { name: /Dyslexia-friendly text/i })).toHaveAttribute('aria-checked', 'false')
  })

  it('dyslexia switch reflects settings.dyslexiaFont (on)', () => {
    mockSettings = { dyslexiaFont: true, quietMode: false }
    render(<CatalogDisplayMenu hideCovers={false} onToggleHideCovers={() => {}} onResetCovers={() => {}} />)
    openMenu()
    expect(screen.getByRole('switch', { name: /Dyslexia-friendly text/i })).toHaveAttribute('aria-checked', 'true')
  })

  it('toggling dyslexia calls updateSetting with the shared dyslexiaFont key set true', () => {
    render(<CatalogDisplayMenu hideCovers={false} onToggleHideCovers={() => {}} onResetCovers={() => {}} />)
    openMenu()
    fireEvent.click(screen.getByRole('switch', { name: /Dyslexia-friendly text/i }))
    expect(updateSetting).toHaveBeenCalledWith('dyslexiaFont', true)
  })

  it('toggling quiet mode calls updateSetting with quietMode set true', () => {
    render(<CatalogDisplayMenu hideCovers={false} onToggleHideCovers={() => {}} onResetCovers={() => {}} />)
    openMenu()
    fireEvent.click(screen.getByRole('switch', { name: /Quiet mode/i }))
    expect(updateSetting).toHaveBeenCalledWith('quietMode', true)
  })

  it('hide covers switch reflects the prop and calls back on click', () => {
    const onToggleHideCovers = vi.fn()
    render(<CatalogDisplayMenu hideCovers onToggleHideCovers={onToggleHideCovers} onResetCovers={() => {}} />)
    openMenu()
    const sw = screen.getByRole('switch', { name: /Hide covers/i })
    expect(sw).toHaveAttribute('aria-checked', 'true')
    fireEvent.click(sw)
    expect(onToggleHideCovers).toHaveBeenCalledTimes(1)
  })

  it('reset is disabled when everything is already at defaults', () => {
    render(<CatalogDisplayMenu hideCovers={false} onToggleHideCovers={() => {}} onResetCovers={() => {}} />)
    openMenu()
    expect(screen.getByRole('button', { name: /Reset display to defaults/i })).toBeDisabled()
  })

  it('reset turns off comfort settings and restores covers', () => {
    mockSettings = { dyslexiaFont: true, quietMode: true }
    const onResetCovers = vi.fn()
    render(<CatalogDisplayMenu hideCovers onToggleHideCovers={() => {}} onResetCovers={onResetCovers} />)
    openMenu()
    const reset = screen.getByRole('button', { name: /Reset display to defaults/i })
    expect(reset).toBeEnabled()
    fireEvent.click(reset)
    expect(updateSetting).toHaveBeenCalledWith('dyslexiaFont', false)
    expect(updateSetting).toHaveBeenCalledWith('quietMode', false)
    expect(onResetCovers).toHaveBeenCalledTimes(1)
  })
})

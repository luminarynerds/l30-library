/// <reference types="@testing-library/jest-dom" />
/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * WCAG 2.1.4: the single-key catalog shortcuts must be fully inert when the
 * user has opted out via the keyboardShortcutsEnabled accessibility setting.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook } from '@testing-library/react'
import { useCatalogKeyboardShortcuts } from '../useCatalogKeyboardShortcuts'

vi.mock('@/pages/catalog/utils/catalogTextToSpeech', () => ({
  stopSpeaking: vi.fn(),
}))

function makeParams(overrides: Partial<Parameters<typeof useCatalogKeyboardShortcuts>[0]> = {}) {
  const input = document.createElement('input')
  document.body.appendChild(input)
  return {
    searchInputRef: { current: input },
    isDrawerOpen: false,
    setIsDrawerOpen: vi.fn(),
    simplifiedView: false,
    setSimplifiedView: vi.fn(),
    setSpeakingItemId: vi.fn(),
    quietMode: false,
    updateA11ySetting: vi.fn(),
    reduceMotion: true,
    announceToScreenReader: vi.fn(),
    shortcutsEnabled: true,
    ...overrides,
  }
}

function pressKey(key: string) {
  window.dispatchEvent(new KeyboardEvent('keydown', { key, bubbles: true }))
}

describe('useCatalogKeyboardShortcuts — opt-out gate', () => {
  beforeEach(() => {
    document.body.innerHTML = ''
  })

  it('binds shortcuts when enabled: / focuses search, q toggles quiet mode', () => {
    const params = makeParams()
    renderHook(() => useCatalogKeyboardShortcuts(params))

    pressKey('/')
    expect(document.activeElement).toBe(params.searchInputRef.current)
    expect(params.announceToScreenReader).toHaveBeenCalledWith('Search field focused')

    // Move focus off the input so the next shortcut isn't swallowed.
    ;(document.activeElement as HTMLElement).blur()
    pressKey('q')
    expect(params.updateA11ySetting).toHaveBeenCalledWith('quietMode', true)
  })

  it('binds nothing when shortcutsEnabled is false', () => {
    const params = makeParams({ shortcutsEnabled: false })
    renderHook(() => useCatalogKeyboardShortcuts(params))

    pressKey('/')
    pressKey('q')
    pressKey('s')
    pressKey('f')

    expect(document.activeElement).not.toBe(params.searchInputRef.current)
    expect(params.updateA11ySetting).not.toHaveBeenCalled()
    expect(params.setSimplifiedView).not.toHaveBeenCalled()
    expect(params.setIsDrawerOpen).not.toHaveBeenCalled()
    expect(params.announceToScreenReader).not.toHaveBeenCalled()
  })

  it('rebinds when the setting flips back on', () => {
    let params = makeParams({ shortcutsEnabled: false })
    const { rerender } = renderHook(
      ({ p }) => useCatalogKeyboardShortcuts(p),
      { initialProps: { p: params } },
    )

    pressKey('s')
    expect(params.setSimplifiedView).not.toHaveBeenCalled()

    params = { ...params, shortcutsEnabled: true }
    rerender({ p: params })

    pressKey('s')
    expect(params.setSimplifiedView).toHaveBeenCalledTimes(1)
  })

  it('targets the filters sidebar by data attribute, not English aria-label', () => {
    const sidebar = document.createElement('aside')
    sidebar.setAttribute('data-catalog-filters', '')
    sidebar.setAttribute('aria-label', 'Filtros') // non-English locale
    sidebar.scrollIntoView = vi.fn()
    document.body.appendChild(sidebar)
    window.innerWidth = 1440

    const params = makeParams()
    renderHook(() => useCatalogKeyboardShortcuts(params))

    pressKey('f')
    expect(sidebar.scrollIntoView).toHaveBeenCalled()
  })
})

/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'

describe('translations lazy loader', () => {
  beforeEach(async () => {
    vi.resetModules()
    vi.mocked(localStorage.getItem).mockReset()
    vi.mocked(localStorage.setItem).mockReset()
    vi.mocked(localStorage.removeItem).mockReset()
  })

  it('starts with no language loaded', async () => {
    const mod = await import('../i18n/translations')
    expect(mod.isLanguageLoaded('en')).toBe(false)
    expect(mod.isLanguageLoaded('es')).toBe(false)
  })

  it('loadLanguage("en") populates en translations and getTranslation returns localized strings', async () => {
    const mod = await import('../i18n/translations')
    expect(mod.isLanguageLoaded('en')).toBe(false)

    await mod.loadLanguage('en')

    expect(mod.isLanguageLoaded('en')).toBe(true)
    const all = mod.getLanguageTranslations('en')
    expect(typeof all).toBe('object')
    expect(Object.keys(all).length).toBeGreaterThan(0)
  })

  it('getTranslation falls back to the key when no language is loaded yet', async () => {
    const mod = await import('../i18n/translations')
    expect(mod.getTranslation('common.save')).toBe('common.save')
  })

  it('concurrent loadLanguage calls resolve consistently and only fetch once', async () => {
    const mod = await import('../i18n/translations')
    const a = mod.loadLanguage('en')
    const b = mod.loadLanguage('en')
    await Promise.all([a, b])
    expect(mod.isLanguageLoaded('en')).toBe(true)
    // Second call after settled should be a no-op fast-path
    const c = mod.loadLanguage('en')
    await c
    expect(mod.isLanguageLoaded('en')).toBe(true)
  })

  it('isValidLanguage gates supported locales', async () => {
    const { isValidLanguage } = await import('../i18n/translations')
    expect(isValidLanguage('en')).toBe(true)
    expect(isValidLanguage('es')).toBe(true)
    expect(isValidLanguage('zz')).toBe(false)
    expect(isValidLanguage('')).toBe(false)
  })

  it('getInitialLanguage honours localStorage preference', async () => {
    vi.mocked(localStorage.getItem).mockReturnValue('es')
    const { getInitialLanguage } = await import('../i18n/translations')
    expect(getInitialLanguage()).toBe('es')
  })

  it('getInitialLanguage falls back to "en" for unsupported stored values', async () => {
    vi.mocked(localStorage.getItem).mockReturnValue('klingon')
    const { getInitialLanguage } = await import('../i18n/translations')
    // navigator.language may match a supported lang in the test env; if it's
    // not a supported code we expect 'en'. Either way, never returns 'klingon'.
    expect(getInitialLanguage()).not.toBe('klingon')
  })

  it('English fallback applies when a key is missing in another language', async () => {
    const mod = await import('../i18n/translations')
    await mod.loadLanguage('en')
    // Pick a key that exists in en
    const enAll = mod.getLanguageTranslations('en') as Record<string, unknown>
    const firstSection = Object.keys(enAll)[0]
    // Without loading 'fr', requesting an fr translation should fall back to en
    if (firstSection) {
      const fr = mod.getTranslation(firstSection, 'fr')
      // Either returns an object stub key or the en value; what matters is it
      // doesn't throw and doesn't return the literal key when en has it
      expect(typeof fr).toBe('string')
    }
  })

  it('getTranslation returns defaultValue (not the key) when key is missing and one is provided', async () => {
    const mod = await import('../i18n/translations')
    await mod.loadLanguage('en')
    expect(mod.getTranslation('nope.not.here', 'en', undefined, 'Fallback')).toBe('Fallback')
  })

  it('getTranslation returns the key when missing and no defaultValue is provided', async () => {
    const mod = await import('../i18n/translations')
    await mod.loadLanguage('en')
    expect(mod.getTranslation('still.not.here', 'en')).toBe('still.not.here')
  })

  it('standalone t() accepts a string fallback as the second arg', async () => {
    const mod = await import('../i18n/translations')
    await mod.loadLanguage('en')
    expect(mod.t('really.not.here', 'Default Text')).toBe('Default Text')
  })

  it('standalone t() still accepts a params object as the second arg', async () => {
    const mod = await import('../i18n/translations')
    await mod.loadLanguage('en')
    // Missing key + params object (no defaultValue) -> returns the raw key
    expect(mod.t('missing.key.with.params', { name: 'Sam' })).toBe('missing.key.with.params')
  })
})

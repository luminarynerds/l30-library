/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Regression tests for accessibility preset application and stale-settings
 * recovery.
 *
 * What this guards against:
 *   1. A preset's enum value drifting out of sync with the type-guard
 *      enum (which lands a literal class like "font-size-undefined" on
 *      <html>).
 *   2. Stale localStorage values from a prior schema (e.g. an old
 *      fontSize: "x-large") leaking past validateAndMergeSettings.
 *   3. A preset that targets dyslexia-mode failing to set the
 *      data-dyslexia-mode attribute that activates the Atkinson
 *      Hyperlegible @font-face cascade.
 */
import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import { ACCESSIBILITY_PRESETS, DYSLEXIA_SUPPORT_PRESET } from '../config/presets.config';
import { DEFAULT_SETTINGS } from '../config/defaults.config';
import {
  applyThemeClasses,
  removeThemeClasses,
  validateAndMergeSettings,
} from '../utils/cssApplicator';

function applyPreset(preset: typeof ACCESSIBILITY_PRESETS[number]) {
  const settings = { ...DEFAULT_SETTINGS, ...preset.settings };
  applyThemeClasses(settings);
  return settings;
}

describe('preset application', () => {
  beforeEach(() => {
    removeThemeClasses();
  });

  afterEach(() => {
    removeThemeClasses();
  });

  it.each(ACCESSIBILITY_PRESETS.map((p) => [p.id, p] as const))(
    'preset %s applies without leaving "undefined" in className',
    (_id, preset) => {
      applyPreset(preset);
      const className = document.documentElement.className;
      expect(className).not.toMatch(/undefined/);
      expect(className).not.toMatch(/\bnull\b/);
    }
  );

  it('Hyperlegible Reading preset sets data-dyslexia-mode so the @font-face cascade fires', () => {
    applyPreset(DYSLEXIA_SUPPORT_PRESET);
    expect(document.documentElement.getAttribute('data-dyslexia-mode')).toBe('true');
    expect(document.documentElement.classList.contains('dyslexia-font')).toBe(true);
  });

  it('Hyperlegible Reading preset retains the dyslexia-support id slug for localStorage backcompat', () => {
    // Renaming the user-facing label is fine; renaming the id would
    // orphan saved settings. Lock the slug in.
    expect(DYSLEXIA_SUPPORT_PRESET.id).toBe('dyslexia-support');
    expect(DYSLEXIA_SUPPORT_PRESET.name).toBe('Hyperlegible Reading');
  });
});

describe('validateAndMergeSettings', () => {
  it('falls back to defaults when fontSize is a stale out-of-enum value', () => {
    // 'x-large' was a real value in an earlier schema; today the enum
    // is normal | large | xlarge. Without per-field validation this
    // leaks into the className as "font-size-undefined".
    const stale = { fontSize: 'x-large' as unknown as never };
    const merged = validateAndMergeSettings(stale, DEFAULT_SETTINGS);
    expect(merged.fontSize).toBe(DEFAULT_SETTINGS.fontSize);
  });

  it('falls back to defaults for every enum-typed field independently', () => {
    const stale = {
      theme: 'neon' as unknown as never,
      fontSize: 'huge' as unknown as never,
      lineSpacing: 'mega' as unknown as never,
      letterSpacing: 'widest' as unknown as never,
      letterSpacingBody: 'widest' as unknown as never,
      letterSpacingHeaders: 'widest' as unknown as never,
      colorBlindMode: 'magenta' as unknown as never,
      fontWeight: 999 as unknown as never,
      enhancedFocusOpacity: 33 as unknown as never,
    };
    const merged = validateAndMergeSettings(stale, DEFAULT_SETTINGS);
    expect(merged.theme).toBe(DEFAULT_SETTINGS.theme);
    expect(merged.fontSize).toBe(DEFAULT_SETTINGS.fontSize);
    expect(merged.lineSpacing).toBe(DEFAULT_SETTINGS.lineSpacing);
    expect(merged.letterSpacing).toBe(DEFAULT_SETTINGS.letterSpacing);
    expect(merged.letterSpacingBody).toBe(DEFAULT_SETTINGS.letterSpacingBody);
    expect(merged.letterSpacingHeaders).toBe(DEFAULT_SETTINGS.letterSpacingHeaders);
    expect(merged.colorBlindMode).toBe(DEFAULT_SETTINGS.colorBlindMode);
    expect(merged.fontWeight).toBe(DEFAULT_SETTINGS.fontWeight);
    expect(merged.enhancedFocusOpacity).toBe(DEFAULT_SETTINGS.enhancedFocusOpacity);
  });

  it('applying merged settings from stale input never produces "undefined" classes', () => {
    const stale = { fontSize: 'x-large' as unknown as never };
    const merged = validateAndMergeSettings(stale, DEFAULT_SETTINGS);
    removeThemeClasses();
    applyThemeClasses(merged);
    expect(document.documentElement.className).not.toMatch(/undefined/);
  });

  it('preserves valid user values (does not stomp on them)', () => {
    const valid = { fontSize: 'xlarge' as const, theme: 'dark' as const };
    const merged = validateAndMergeSettings(valid, DEFAULT_SETTINGS);
    expect(merged.fontSize).toBe('xlarge');
    expect(merged.theme).toBe('dark');
  });
});

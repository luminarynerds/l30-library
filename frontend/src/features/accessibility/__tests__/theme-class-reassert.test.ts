/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Regression tests for settings-class resilience.
 *
 * What this guards against: an externally-stripped settings class staying
 * lost when settings are unchanged. The original culprit was a settings-hash
 * cache in applyThemeClasses (removed 2026-08-14): <html> losing its
 * .light/.dark/.high-contrast class rendered the :root dark tokens under
 * light-mode markup — dark cards with dark text (seen live on the Orange
 * demo, 2026-07-06) — and every other settings class had the same exposure.
 * Re-applying with unchanged settings must restore everything.
 */
import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import { DEFAULT_SETTINGS } from '../config/defaults.config';
import {
  applyThemeClasses,
  removeThemeClasses,
} from '../utils/cssApplicator';

describe('settings class re-assertion with unchanged settings', () => {
  beforeEach(() => {
    removeThemeClasses();
  });

  afterEach(() => {
    removeThemeClasses();
    document.documentElement.classList.remove('light');
  });

  it.each([
    ['light', 'light'],
    ['dark', 'dark'],
    ['high-contrast', 'high-contrast'],
  ] as const)(
    'restores the %s theme class after external removal with unchanged settings',
    (theme, expectedClass) => {
      const settings = { ...DEFAULT_SETTINGS, theme };
      applyThemeClasses(settings);
      expect(document.documentElement.classList.contains(expectedClass)).toBe(true);

      // Simulate a third-party script (or a buggy applicator elsewhere)
      // stripping every theme class while settings stay unchanged.
      document.documentElement.classList.remove('light', 'dark', 'high-contrast');

      applyThemeClasses(settings); // cache hit — must still re-assert
      expect(document.documentElement.classList.contains(expectedClass)).toBe(true);
    }
  );

  it('exactly one theme class family is present after re-assertion', () => {
    const settings = { ...DEFAULT_SETTINGS, theme: 'dark' as const };
    applyThemeClasses(settings);
    document.documentElement.classList.remove('dark');
    applyThemeClasses(settings);
    const cls = document.documentElement.classList;
    expect(cls.contains('dark')).toBe(true);
    expect(cls.contains('light')).toBe(false);
    expect(cls.contains('high-contrast')).toBe(false);
  });

  // The theme class was only ever the loudest casualty. Every other settings
  // class has the same exposure: if a third-party script (or a wholesale
  // className write) strips it while settings are unchanged, re-applying must
  // restore it too — not just .light/.dark/.high-contrast.
  it.each([
    ['font-size-large', { fontSize: 'large' }],
    ['reduce-motion', { reduceMotion: true }],
    ['dyslexia-font', { dyslexiaFont: true }],
  ] as const)(
    'restores %s after external removal with unchanged settings',
    (expectedClass, overrides) => {
      const settings = { ...DEFAULT_SETTINGS, ...overrides };
      applyThemeClasses(settings);
      expect(document.documentElement.classList.contains(expectedClass)).toBe(true);

      document.documentElement.classList.remove(expectedClass);

      applyThemeClasses(settings); // unchanged settings — must still restore
      expect(document.documentElement.classList.contains(expectedClass)).toBe(true);
    }
  );
});

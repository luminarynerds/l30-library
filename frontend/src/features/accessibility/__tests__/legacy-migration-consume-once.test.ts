/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Regression tests for consume-once legacy migration.
 *
 * What this guards against: a lingering lsc-neurodivergent-settings key
 * shadowing the saved unified accessibility-settings on every boot. The
 * patron's changes applied live, then silently reverted on the next
 * reload, and the saved settings were overwritten with the migrated
 * legacy values (reproduced against l30.org, 2026-08-14).
 */
import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import { DEFAULT_SETTINGS } from '../config/defaults.config';
import { loadInitialSettings } from '../context/UnifiedAccessibilityContext';

const LEGACY_KEY = 'lsc-neurodivergent-settings';
const UNIFIED_KEY = 'accessibility-settings';

const legacyBlob = JSON.stringify({
  sensory: { mutedColors: true },
  presetName: 'legacy-preset',
});

const unifiedWithLargeFont = JSON.stringify({
  ...DEFAULT_SETTINGS,
  fontSize: 'large',
});

// The global setup stubs localStorage with storeless vi.fn()s; these tests
// are about what survives in storage, so install a real Map-backed store.
function installStoringLocalStorage(): void {
  const store = new Map<string, string>();
  Object.defineProperty(window, 'localStorage', {
    configurable: true,
    value: {
      getItem: (k: string) => (store.has(k) ? (store.get(k) as string) : null),
      setItem: (k: string, v: string) => void store.set(k, String(v)),
      removeItem: (k: string) => void store.delete(k),
      clear: () => void store.clear(),
    },
  });
}

describe('loadInitialSettings: consume-once legacy migration', () => {
  beforeEach(() => installStoringLocalStorage());
  afterEach(() => localStorage.clear());

  it('saved unified settings win over a lingering legacy key', () => {
    localStorage.setItem(LEGACY_KEY, legacyBlob);
    localStorage.setItem(UNIFIED_KEY, unifiedWithLargeFont);

    const { settings } = loadInitialSettings(true);

    expect(settings.fontSize).toBe('large');
    expect(settings.mutedColors).toBe(DEFAULT_SETTINGS.mutedColors);
  });

  it('deletes the legacy key so it cannot shadow later boots', () => {
    localStorage.setItem(LEGACY_KEY, legacyBlob);
    localStorage.setItem(UNIFIED_KEY, unifiedWithLargeFont);

    loadInitialSettings(true);

    expect(localStorage.getItem(LEGACY_KEY)).toBeNull();
  });

  it('first-ever migration still works when no unified settings exist', () => {
    localStorage.setItem(LEGACY_KEY, legacyBlob);

    const { settings, presetName } = loadInitialSettings(true);

    expect(settings.mutedColors).toBe(true);
    expect(presetName).toBe('legacy-preset');
    expect(localStorage.getItem(LEGACY_KEY)).toBeNull();
  });

  it('unreadable legacy blob falls back to unified settings and is deleted', () => {
    localStorage.setItem(LEGACY_KEY, '{not json');
    localStorage.setItem(UNIFIED_KEY, unifiedWithLargeFont);

    const { settings } = loadInitialSettings(true);

    expect(settings.fontSize).toBe('large');
    expect(localStorage.getItem(LEGACY_KEY)).toBeNull();
  });

  it('control: unified settings load normally with no legacy key', () => {
    localStorage.setItem(UNIFIED_KEY, unifiedWithLargeFont);

    expect(loadInitialSettings(true).settings.fontSize).toBe('large');
  });
});

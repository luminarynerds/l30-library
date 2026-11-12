/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Theme Application Hook
 * Handles applying accessibility settings to the DOM
 */

import { useEffect, useCallback } from 'react';
import type { AccessibilitySettings } from '../types/accessibility.types';
import { applyThemeClasses } from '../utils/cssApplicator';

function shouldBeDark(settings: AccessibilitySettings): boolean | null {
  const { autoThemeSchedule, autoThemeDarkStart, autoThemeLightStart } = settings;

  if (autoThemeSchedule === 'system') {
    return null; // defer to prefers-color-scheme
  }

  const darkStart = autoThemeSchedule === 'solar' ? 19 : autoThemeDarkStart;
  const lightStart = autoThemeSchedule === 'solar' ? 7 : autoThemeLightStart;
  const hour = new Date().getHours();

  // Handle wrap-around (e.g. dark 19-7 means dark when hour >= 19 OR hour < 7)
  if (darkStart > lightStart) {
    return hour >= darkStart || hour < lightStart;
  }
  // Edge case: dark 7-19 would mean dark during the day (unusual but supported)
  if (darkStart < lightStart) {
    return hour >= darkStart && hour < lightStart;
  }
  // darkStart === lightStart: always dark
  return true;
}

function applyScheduledTheme(settings: AccessibilitySettings): void {
  // First let the standard applicator run (handles all non-theme classes too)
  applyThemeClasses(settings);

  // If theme is 'system', check if schedule overrides OS preference
  if (settings.theme === 'system') {
    const dark = shouldBeDark(settings);
    if (dark !== null) {
      const root = document.documentElement;
      if (dark) {
        root.classList.add('dark');
        root.classList.remove('light');
      } else {
        root.classList.add('light');
        root.classList.remove('dark');
      }
    }
  }
}

export function useThemeApplication(
  settings: AccessibilitySettings
): void {
  const applyTheme = useCallback(() => {
    applyScheduledTheme(settings);
  }, [settings]);

  // Apply CSS classes and custom properties
  // No cleanup needed — this provider wraps the entire app and never unmounts.
  // Removing classes on effect re-run caused a white flash (FOUC) during navigation.
  useEffect(() => {
    applyScheduledTheme(settings);
  }, [settings]);

  // Listen for system theme changes when theme is set to 'system'
  useEffect(() => {
    if (settings.theme === 'system') {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');

      const handleSystemThemeChange = () => {
        applyScheduledTheme(settings);
      };

      mediaQuery.addEventListener('change', handleSystemThemeChange);

      return () => {
        mediaQuery.removeEventListener('change', handleSystemThemeChange);
      };
    }
  }, [settings.theme, settings]);

  // Re-check time-based schedule every minute when using solar or custom
  useEffect(() => {
    if (
      settings.theme !== 'system' ||
      settings.autoThemeSchedule === 'system'
    ) {
      return;
    }

    const interval = setInterval(applyTheme, 60_000);
    return () => clearInterval(interval);
  }, [settings.theme, settings.autoThemeSchedule, applyTheme]);
}

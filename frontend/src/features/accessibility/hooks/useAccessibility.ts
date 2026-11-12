/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Main Accessibility Hook
 * Provides access to accessibility settings and update functions
 */

import { useCallback, useContext } from 'react';
import { UnifiedAccessibilityContext } from '../context/UnifiedAccessibilityContext';
import type {
  UpdateSetting,
  AccessibilityContextType,
  AccessibilitySettings,
} from '../types/accessibility.types';

export function useAccessibility(): AccessibilityContextType &
  AccessibilitySettings & {
    announceToScreenReader: (message: string) => void;
  } {
  const context = useContext(UnifiedAccessibilityContext);

  if (!context) {
    throw new Error(
      'useAccessibility must be used within AccessibilityProvider. ' +
      'Make sure your component is wrapped in <AccessibilityProvider>.'
    );
  }

  const { settings, updateSetting: originalUpdateSetting } = context;

  const updateSetting = useCallback<UpdateSetting>((key, value) => {
    originalUpdateSetting(key, value);
  }, [originalUpdateSetting]);

  const announceToScreenReader = useCallback((message: string) => {
    if (typeof window === 'undefined') return;

    const id = 'sr-announcer';
    let el = document.getElementById(id);

    if (!el) {
      el = document.createElement('div');
      el.id = id;
      el.setAttribute('aria-live', 'polite');
      el.setAttribute('aria-atomic', 'true');
      el.className = 'sr-only';
      document.body.appendChild(el);
    }

    el.textContent = '';
    window.setTimeout(() => {
      if (el) el.textContent = message;
    }, 10);
  }, []);

  return {
    ...context,
    settings,
    updateSetting,
    ...settings,
    announceToScreenReader,
  };
}

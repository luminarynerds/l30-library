/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Unified Accessibility Hook
 *
 * Provides access to unified accessibility settings and controls
 * Replaces both useAccessibility() and useNeurodivergentSettings()
 *
 * Includes:
 * - Full modern accessibility settings
 * - Category-based update helpers
 * - Preset system integration
 * - Analytics tracking
 * - Screen reader announcements
 *
 * @example
 * ```tsx
 * function MyComponent() {
 *   const { settings, updateSetting } = useUnifiedAccessibility();
 *
 *   return (
 *     <button onClick={() => updateSetting('fontSize', 'large')}>
 *       Increase Font Size
 *     </button>
 *   );
 * }
 * ```
 */

import { useCallback, useContext } from 'react';
import { UnifiedAccessibilityContext } from '../context/UnifiedAccessibilityContext';
import type {
  UpdateSetting,
  AccessibilitySettings,
} from '../types/accessibility.types';
import type { UnifiedAccessibilityContextType } from '../context/UnifiedAccessibilityContext';
import { logger } from '../../../utils/logger';

export interface UseUnifiedAccessibilityReturn
  extends UnifiedAccessibilityContextType,
  AccessibilitySettings {
  /**
   * Announce a message to screen readers
   */
  announceToScreenReader: (message: string) => void;
}

export function useUnifiedAccessibility(): UseUnifiedAccessibilityReturn {
  const context = useContext(UnifiedAccessibilityContext);

  if (!context) {
    throw new Error(
      'useUnifiedAccessibility must be used within UnifiedAccessibilityProvider. ' +
      'Make sure your component is wrapped in <UnifiedAccessibilityProvider>.'
    );
  }

  const { settings, updateSetting: originalUpdateSetting, ...rest } = context;

  const updateSetting = useCallback<UpdateSetting>((key, value) => {
    originalUpdateSetting(key, value);
  }, [originalUpdateSetting]);

  /**
   * Announce a message to screen readers
   * Creates a live region if it doesn't exist
   */
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
    ...rest,
    settings,
    updateSetting,
    announceToScreenReader,
    // Spread all settings as flat properties for convenience
    ...settings,
  };
}

export function useAccessibility(): UseUnifiedAccessibilityReturn {
  logger.warn(
    'useAccessibility is deprecated. Use useUnifiedAccessibility() instead. ' +
    'Both hooks work the same, but useUnifiedAccessibility is the recommended name.'
  );
  return useUnifiedAccessibility();
}

export function useNeurodivergentSettings() {
  logger.warn(
    'useNeurodivergentSettings is deprecated. Use useUnifiedAccessibility() instead. ' +
    'The hook now returns all settings in a unified structure.'
  );

  const context = useContext(UnifiedAccessibilityContext);

  if (!context) {
    throw new Error(
      'useNeurodivergentSettings must be used within UnifiedAccessibilityProvider.'
    );
  }

  // Return context directly for legacy compatibility
  return context;
}

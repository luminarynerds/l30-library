/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/* eslint-disable react-refresh/only-export-components */
/**
 * Accessibility Context
 * Pure state management for accessibility settings
 *
 * This context is focused solely on state management.
 * Side effects (persistence, CSS application) are handled by hooks.
 */

import {
  createContext,
  useState,
  useCallback,
  useMemo,
  ReactNode,
  useEffect,
} from "react";
import type {
  AccessibilitySettings,
  AccessibilityContextType,
  UpdateSetting,
} from '../types/accessibility.types';
import { DEFAULT_SETTINGS } from '../config/defaults.config';
import {
  useSettingsPersistence,
  loadSettingsFromStorage,
} from '../hooks/useSettingsPersistence';
import { useThemeApplication } from '../hooks/useThemeApplication';
import { logger } from '../../../utils/logger';
import { t } from '@/i18n'

/**
 * Context for accessibility settings
 */
export const AccessibilityContext = createContext<
  AccessibilityContextType | undefined
>(undefined);

function AccessibilityErrorBoundary({
  children,
  onError
}: {
  children: ReactNode;
  onError?: (error: Error) => void;
}) {
  const [hasError, setHasError] = useState(false);
  const [_error, setError] = useState<Error | null>(null);

  useEffect(() => {
    const handleError = (event: ErrorEvent) => {
      // Only handle accessibility-related errors
      if (event.filename?.includes('accessibility') ||
          event.message?.includes('accessibility')) {
        logger.error('Accessibility system error:', event.error);
        setError(event.error || new Error(event.message));
        setHasError(true);
        onError?.(event.error || new Error(event.message));
      }
    };

    window.addEventListener('error', handleError);
    return () => window.removeEventListener('error', handleError);
  }, [onError]);

  if (hasError) {
    return (
      <div
        role="alert"
        className="fixed bottom-4 right-4 bg-status-warning-100 dark:bg-status-warning-900/30 border border-status-warning-400 text-status-warning-700 dark:text-status-warning-300 px-4 py-3 rounded-lg shadow-lg max-w-sm z-50"
        aria-live="assertive"
      >
        <div className="flex items-center">
          <div className="py-1">
            <strong className="font-bold">Accessibility Notice</strong>
            <div className="block sm:inline ml-2">
              Some accessibility features may not be available. Using default settings.
            </div>
          </div>
        </div>
        <button
          onClick={() => {
            setHasError(false);
            setError(null);
            window.location.reload(); // Force reload to reset state
          }}
          className="mt-2 bg-status-warning-200 hover:bg-status-warning-300 text-status-warning-800 dark:text-status-warning-300 px-3 py-1 rounded text-sm font-medium transition-colors"
          aria-label={t('aria.common.reloadPageToRestoreAccessibility')}
        >
          Reload Page
        </button>
      </div>
    );
  }

  return <>{children}</>;
}

interface AccessibilityProviderProps {
  children: ReactNode;
}

export function AccessibilityProvider({
  children,
}: AccessibilityProviderProps) {
  const [_error, setError] = useState<Error | null>(null);
  const [_isInitialized, setIsInitialized] = useState(false);

  // Load initial settings from localStorage with error handling
  const [settings, setSettings] = useState<AccessibilitySettings>(() => {
    try {
      const loadedSettings = loadSettingsFromStorage();
      setIsInitialized(true);
      return loadedSettings;
    } catch (_err) {
      logger.error('Failed to load accessibility settings:', _err);
      setError(_err as Error);
      setIsInitialized(true);
      return DEFAULT_SETTINGS; // Fallback to defaults
    }
  });

  /**
   * Update a single setting with error handling
   * Type-safe - ensures value matches setting key type
   */
  const updateSetting = useCallback<UpdateSetting>(
    (key, value) => {
      try {
        setSettings((prev) => ({
          ...prev,
          [key]: value,
        }));
        setError(null); // Clear any previous errors on successful update
      } catch (_err) {
        logger.error(`Failed to update accessibility setting ${key}:`, _err);
        setError(_err as Error);
      }
    },
    []
  );

  /**
   * Reset all settings to defaults with error handling
   */
  const resetSettings = useCallback(() => {
    try {
      setSettings(DEFAULT_SETTINGS);
      setError(null);
      logger.info('Accessibility settings reset to defaults');
    } catch (_err) {
      logger.error('Failed to reset accessibility settings:', _err);
      setError(_err as Error);
    }
  }, []);

  // Side effects handled by hooks (must be called unconditionally per Rules of Hooks)
  useSettingsPersistence(settings); // Auto-save to localStorage
  useThemeApplication(settings); // Apply CSS classes and theme

  // Memoize context value to prevent unnecessary re-renders
  const contextValue = useMemo(
    () => ({
      settings,
      updateSetting,
      resetSettings,
    }),
    [settings, updateSetting, resetSettings]
  );

  return (
    <AccessibilityErrorBoundary onError={setError}>
      <AccessibilityContext.Provider value={contextValue}>
        {children}
        {_error && (
          <div
            role="alert"
            className="fixed top-4 right-4 bg-status-danger-100 dark:bg-status-danger-900/30 border border-status-danger-400 text-status-danger-700 dark:text-status-danger-300 px-4 py-3 rounded-lg shadow-lg max-w-sm z-50"
            aria-live="assertive"
          >
            <div className="flex items-center">
              <div className="py-1">
                <strong className="font-bold">Accessibility Error</strong>
                <div className="block sm:inline ml-2">
                  Some features may not work correctly.
                </div>
              </div>
            </div>
          </div>
        )}
      </AccessibilityContext.Provider>
    </AccessibilityErrorBoundary>
  );
}

/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/* eslint-disable react-refresh/only-export-components */
/**
 * Unified Accessibility Context
 *
 * Consolidates both AccessibilityContext and NeurodivergentSettingsContext
 * into a single source of truth for accessibility settings.
 *
 * Features:
 * - Flat structure from modern AccessibilityContext
 * - Category-based helpers from legacy NeurodivergentSettingsContext
 * - Automatic migration from legacy format
 * - Full backward compatibility
 * - Preset system combining both approaches
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
import type {
  NeurodivergentSettings,
  SettingsPreset as LegacyPreset,
} from '../../../types/neurodivergent-settings';
import { DEFAULT_SETTINGS } from '../config/defaults.config';
import { getPresetById } from '../config/presets.config';
import { applyPresetToSettings } from '../../../lib/neurodivergent-presets';
import {
  useSettingsPersistence,
  loadSettingsFromStorage,
  hasStoredSettings,
} from '../hooks/useSettingsPersistence';
import { useThemeApplication } from '../hooks/useThemeApplication';
import { logger } from '../../../utils/logger';
import {
  migrateNeurodivergentToAccessibility,
  detectLegacySettingsInStorage,
  clearLegacySettings,
} from '../utils/settingsMigration';
import { t } from '@/i18n'

export interface UnifiedAccessibilityContextType extends AccessibilityContextType {
  // Category-based helpers for legacy compatibility
  updateCategory: <K extends keyof AccessibilitySettings>(
    category: K,
    updates: Partial<AccessibilitySettings[K]>
  ) => void;

  // Preset helpers
  applyAccessibilityPreset: (presetId: string) => void;
  applyLegacyPreset: (presetId: LegacyPreset) => void;
  getCurrentPreset: () => string | undefined;

  // Session management
  isSettingsOpen: boolean;
  setIsSettingsOpen: (open: boolean) => void;
  quickSettingsVisible: boolean;
  setQuickSettingsVisible: (visible: boolean) => void;

  // Export/import for settings backup
  exportSettings: () => string;
  importSettings: (json: string) => boolean;

  // Reset individual categories
  resetCategory: (category: keyof AccessibilitySettings) => void;
}

/**
 * Unified Accessibility Context
 * Single context replacing both AccessibilityContext and NeurodivergentSettingsContext
 */
export const UnifiedAccessibilityContext = createContext<
  UnifiedAccessibilityContextType | undefined
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
            window.location.reload();
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

interface UnifiedAccessibilityProviderProps {
  children: ReactNode;
  /**
   * Enable migration from legacy NeurodivergentSettingsContext
   * Default: true
   */
  enableLegacyMigration?: boolean;
}

/**
 * Boot-time settings load. Exported for tests.
 *
 * Legacy migration is consume-once: the lsc-neurodivergent-settings key is
 * read at most one boot (and only when no unified settings were ever
 * saved), then deleted. Before 2026-08-14 a lingering legacy key was
 * re-migrated on EVERY boot, shadowing the saved unified settings and
 * overwriting them via persistence — the patron's changes applied live,
 * then reverted on the next reload.
 */
export function loadInitialSettings(enableLegacyMigration: boolean): {
  settings: AccessibilitySettings;
  presetName?: string;
} {
  if (enableLegacyMigration && detectLegacySettingsInStorage()) {
    try {
      if (!hasStoredSettings()) {
        const legacySettings = localStorage.getItem('lsc-neurodivergent-settings');
        if (legacySettings) {
          const parsed = JSON.parse(legacySettings) as NeurodivergentSettings;
          const migrated = migrateNeurodivergentToAccessibility(parsed);
          logger.info('Migrated legacy neurodivergent settings to unified format');
          clearLegacySettings();
          return { settings: migrated, presetName: parsed.presetName };
        }
      }
    } catch (err: unknown) {
      logger.warn('Failed to parse legacy settings, falling back:', err);
    }
    // Unified settings exist (or the legacy blob was unreadable): delete
    // the legacy key so it can never shadow them again.
    clearLegacySettings();
  }

  return { settings: loadSettingsFromStorage() };
}

export function UnifiedAccessibilityProvider({
  children,
  enableLegacyMigration = true,
}: UnifiedAccessibilityProviderProps) {
  const [_error, setError] = useState<Error | null>(null);
  const [_isInitialized, setIsInitialized] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [quickSettingsVisible, setQuickSettingsVisible] = useState(false);
  const [currentPreset, setCurrentPreset] = useState<string | undefined>();

  // Load initial settings with migration support
  const [settings, setSettings] = useState<AccessibilitySettings>(() => {
    try {
      const { settings: initial, presetName } = loadInitialSettings(enableLegacyMigration);

      // Preserve legacy preset name if available
      if (presetName) {
        setCurrentPreset(presetName);
      }

      setIsInitialized(true);
      return initial;
    } catch (_err) {
      logger.error('Failed to load accessibility settings:', _err);
      setError(_err as Error);
      setIsInitialized(true);
      return DEFAULT_SETTINGS;
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
        setError(null);
      } catch (_err) {
        logger.error(`Failed to update accessibility setting ${key}:`, _err);
        setError(_err as Error);
      }
    },
    []
  );

  /**
   * Update settings by category (for legacy compatibility)
   * Useful for grouping related settings
   */
  const updateCategory = useCallback(<K extends keyof AccessibilitySettings>(
    category: K,
    updates: Partial<AccessibilitySettings[K]>
  ) => {
    try {
      setSettings((prev) => ({
        ...prev,
        [category]: {
          ...(prev[category] as object),
          ...updates,
        },
      }));
      setError(null);
    } catch (_err) {
      logger.error(`Failed to update category ${category}:`, _err);
      setError(_err as Error);
    }
  }, []);

  /**
   * Reset all settings to defaults with error handling.
   *
   * Preserves the patron's saved profiles (their own deliberate work).
   * Language is not part of accessibility settings — I18nContext owns it —
   * so a reset never touches the reader's language. Everything else — the
   * visual/sensory accommodations a "reset" is meant to undo — goes back
   * to defaults.
   */
  const resetSettings = useCallback(() => {
    try {
      setSettings((prev) => ({
        ...DEFAULT_SETTINGS,
        savedProfiles: prev.savedProfiles,
      }));
      setCurrentPreset(undefined);
      setError(null);
      logger.info('Accessibility settings reset to defaults');
    } catch (_err) {
      logger.error('Failed to reset accessibility settings:', _err);
      setError(_err as Error);
    }
  }, []);

  /**
   * Reset individual category to defaults
   */
  const resetCategory = useCallback((category: keyof AccessibilitySettings) => {
    try {
      setSettings((prev) => ({
        ...prev,
        [category]: DEFAULT_SETTINGS[category],
      }));
      setError(null);
      logger.info(`Reset category ${category} to defaults`);
    } catch (_err) {
      logger.error(`Failed to reset category ${category}:`, _err);
      setError(_err as Error);
    }
  }, []);

  /**
   * Apply modern accessibility preset
   */
  const applyAccessibilityPreset = useCallback((presetId: string) => {
    try {
      const preset = getPresetById(presetId);

      if (!preset) {
        logger.warn(`Preset ${presetId} not found`);
        return;
      }

      setSettings((prev) => ({
        ...prev,
        ...preset.settings,
      }));
      setCurrentPreset(presetId);
      setError(null);
      logger.info(`Applied preset ${presetId}`);
    } catch (_err) {
      logger.error(`Failed to apply preset ${presetId}:`, _err);
      setError(_err as Error);
    }
  }, []);

  /**
   * Apply legacy neurodivergent preset
   */
  const applyLegacyPreset = useCallback((presetId: LegacyPreset) => {
    try {
      // Create a temporary legacy settings object
      const tempLegacy: NeurodivergentSettings = {
        executiveFunction: {
          sessionResume: true,
          decisionHelp: false,
          simplifiedChoices: false,
          taskBreakdown: false,
          progressTracking: true,
        },
        sensory: {
          fontFamily: "standard",
          fontSize: 16,
          lineHeight: 1.5,
          letterSpacing: 0,
          theme: "auto",
          mutedColors: false,
          reducedMotion: false,
          readingRuler: false,
          bionicReading: false,
          visualNoise: "medium",
          showImages: true,
          autoplayVideos: false,
        },
        focus: {
          focusMode: false,
          blinders: false,
          distractionFree: false,
          singleTask: false,
          timeBoxing: false,
          hyperfocusProtection: true,
        },
        processing: {
          plainLanguage: false,
          audioDescriptions: false,
          contentWarnings: true,
          slowAnimations: false,
          confirmActions: false,
          previewChanges: false,
        },
        anxiety: {
          undoEnabled: true,
          previewMode: false,
          calmAvailability: false,
          noFOMO: false,
          anonymous: false,
          hideDeadlines: false,
          gentleReminders: true,
        },
        control: {
          routines: false,
          exactMatch: false,
          layoutLock: false,
          customDefaults: {},
          keyboardShortcuts: true,
          autoSave: true,
        },
        interest: {
          gamification: true,
          surpriseMe: false,
          rabbitHoles: true,
          discoveryMode: "full",
          hideSpoilers: false,
        },
        practical: {
          offline: false,
          voiceCommands: false,
          nonVerbal: false,
          largeButtons: false,
          hapticFeedback: false,
        },
        reducedMotion: false,
        mutedColors: false,
        largeText: false,
        highContrast: false,
        soundsEnabled: false,
        breakRemindersEnabled: true,
        breakIntervalMinutes: 30,
        showImages: true,
        contentDensity: "comfortable",
        version: 1,
      };

      const appliedLegacy = applyPresetToSettings(tempLegacy, presetId);
      const migratedSettings = migrateNeurodivergentToAccessibility(appliedLegacy);

      setSettings((prev) => ({
        ...prev,
        ...migratedSettings,
      }));
      setCurrentPreset(presetId);
      setError(null);
      logger.info(`Applied legacy preset ${presetId}`);
    } catch (_err) {
      logger.error(`Failed to apply legacy preset ${presetId}:`, _err);
      setError(_err as Error);
    }
  }, []);

  /**
   * Get current active preset ID (if any)
   */
  const getCurrentPreset = useCallback(() => {
    return currentPreset;
  }, [currentPreset]);

  /**
   * Export settings as JSON
   */
  const exportSettings = useCallback(() => {
    return JSON.stringify(settings, null, 2);
  }, [settings]);

  /**
   * Import settings from JSON
   */
  const importSettings = useCallback((json: string): boolean => {
    try {
      const imported = JSON.parse(json);
      setSettings(imported);
      setCurrentPreset(undefined);
      return true;
    } catch {
      logger.error('Failed to import settings');
      return false;
    }
  }, []);

  // Side effects (must be called unconditionally per Rules of Hooks)
  useSettingsPersistence(settings);
  useThemeApplication(settings);

  // Memoize context value to prevent unnecessary re-renders
  const contextValue = useMemo<UnifiedAccessibilityContextType>(
    () => ({
      settings,
      updateSetting,
      updateCategory,
      resetSettings,
      resetCategory,
      applyAccessibilityPreset,
      applyLegacyPreset,
      getCurrentPreset,
      isSettingsOpen,
      setIsSettingsOpen,
      quickSettingsVisible,
      setQuickSettingsVisible,
      exportSettings,
      importSettings,
    }),
    [
      settings,
      updateSetting,
      updateCategory,
      resetSettings,
      resetCategory,
      applyAccessibilityPreset,
      applyLegacyPreset,
      getCurrentPreset,
      isSettingsOpen,
      quickSettingsVisible,
      exportSettings,
      importSettings,
    ]
  );

  return (
    <AccessibilityErrorBoundary onError={setError}>
      <UnifiedAccessibilityContext.Provider value={contextValue}>
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
      </UnifiedAccessibilityContext.Provider>
    </AccessibilityErrorBoundary>
  );
}

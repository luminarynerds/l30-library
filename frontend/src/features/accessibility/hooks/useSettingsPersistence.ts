/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Settings Persistence Hook
 * Handles localStorage synchronization for accessibility settings
 *
 * This module includes migration logic to consolidate settings from
 * multiple legacy storage keys into a single unified format.
 */

import { useEffect } from 'react';
import type { AccessibilitySettings } from '../types/accessibility.types';
import { DEFAULT_SETTINGS } from '../config/defaults.config';
import { validateAndMergeSettings } from '../utils/cssApplicator';
import { logger } from '@/utils/logger';

const STORAGE_KEY = 'accessibility-settings';

// Legacy storage keys that will be migrated.
// TODO: Safe to remove this migration after 2026-07-01 (90 days post-deploy).
// By then all active users will have visited and had their settings migrated.
const LEGACY_KEYS = {
  neurodivergent: 'neurodivergent-settings',
  calmCatalog: 'calm-catalog-settings',
  anonymousBrowsing: 'anonymous-browsing-settings',
  quietNotifications: 'quiet-notification-settings',
  quickSettings: 'quick-settings-enabled',
} as const;

// Migration version - increment when migration logic changes
const MIGRATION_VERSION = 1;
const MIGRATION_VERSION_KEY = 'accessibility-migration-version';

/**
 * Migrate settings from legacy storage keys to unified format
 * This function reads from all old keys and merges them into a single object
 */
// eslint-disable-next-line complexity
function migrateFromLegacySettings(): Partial<AccessibilitySettings> {
  const migrated: Partial<AccessibilitySettings> = {};

  try {
    // Migrate from neurodivergent-settings
    const neuroSettings = localStorage.getItem(LEGACY_KEYS.neurodivergent);
    if (neuroSettings) {
      const parsed = JSON.parse(neuroSettings);

      // Map neurodivergent settings to unified format
      if (parsed.sensory) {
        if (parsed.sensory.mutedColors !== undefined) migrated.mutedColors = parsed.sensory.mutedColors;
        if (parsed.sensory.reducedMotion !== undefined) migrated.reduceMotion = parsed.sensory.reducedMotion;
        if (parsed.sensory.readingRuler !== undefined) migrated.readingGuide = parsed.sensory.readingRuler;
        if (parsed.sensory.bionicReading !== undefined) migrated.bionicReading = parsed.sensory.bionicReading;
        if (parsed.sensory.showImages !== undefined) migrated.showImages = parsed.sensory.showImages;
      }
      if (parsed.focus) {
        if (parsed.focus.focusMode !== undefined) migrated.focusMode = parsed.focus.focusMode;
        if (parsed.focus.blinders !== undefined) migrated.blinders = parsed.focus.blinders;
        if (parsed.focus.hyperfocusProtection !== undefined) migrated.breakReminders = parsed.focus.hyperfocusProtection;
      }
      if (parsed.processing) {
        if (parsed.processing.plainLanguage !== undefined) migrated.plainLanguage = parsed.processing.plainLanguage;
      }
      if (parsed.anxiety) {
        if (parsed.anxiety.noFOMO !== undefined) migrated.noFOMO = parsed.anxiety.noFOMO;
        if (parsed.anxiety.undoEnabled !== undefined) migrated.undoEnabled = parsed.anxiety.undoEnabled;
        if (parsed.anxiety.anonymous !== undefined) migrated.anonymousMode = parsed.anxiety.anonymous;
      }
      // Legacy top-level settings
      if (parsed.reducedMotion !== undefined) migrated.reduceMotion = parsed.reducedMotion;
      if (parsed.mutedColors !== undefined) migrated.mutedColors = parsed.mutedColors;
      if (parsed.highContrast !== undefined) migrated.highContrast = parsed.highContrast;
      if (parsed.breakRemindersEnabled !== undefined) migrated.breakReminders = parsed.breakRemindersEnabled;
      if (parsed.breakIntervalMinutes !== undefined) migrated.breakIntervalMinutes = parsed.breakIntervalMinutes;
      if (parsed.showImages !== undefined) migrated.showImages = parsed.showImages;
      if (parsed.contentDensity !== undefined) migrated.contentDensity = parsed.contentDensity;
    }

    // Migrate from anonymous-browsing-settings
    const anonSettings = localStorage.getItem(LEGACY_KEYS.anonymousBrowsing);
    if (anonSettings) {
      const parsed = JSON.parse(anonSettings);
      if (parsed.enabled !== undefined) migrated.anonymousMode = parsed.enabled;
      if (parsed.disableSearchHistory !== undefined) migrated.disableSearchHistory = parsed.disableSearchHistory;
      if (parsed.disableViewHistory !== undefined) migrated.disableViewHistory = parsed.disableViewHistory;
      if (parsed.disableRecommendations !== undefined) migrated.disableRecommendations = parsed.disableRecommendations;
      if (parsed.disableTracking !== undefined) migrated.disableTracking = parsed.disableTracking;
      if (parsed.autoClearOnExit !== undefined) migrated.autoClearOnExit = parsed.autoClearOnExit;
    }

    // Migrate from quiet-notification-settings
    const notifSettings = localStorage.getItem(LEGACY_KEYS.quietNotifications);
     
    if (notifSettings) {
      const parsed = JSON.parse(notifSettings);
      if (parsed.whisperMode !== undefined) migrated.whisperMode = parsed.whisperMode;
      if (parsed.batchNotifications !== undefined) migrated.batchNotifications = parsed.batchNotifications;
      if (parsed.batchTime !== undefined) migrated.batchTime = parsed.batchTime;
      if (parsed.batchHour !== undefined) migrated.batchHour = parsed.batchHour;
      if (parsed.noUrgentLanguage !== undefined) migrated.noUrgentLanguage = parsed.noUrgentLanguage;
      if (parsed.showBadge !== undefined) migrated.showNotificationBadge = parsed.showBadge;
      if (parsed.autoDismissSeconds !== undefined) migrated.autoDismissSeconds = parsed.autoDismissSeconds;
    }

    // Migrate from quick-settings-enabled
    const quickSettings = localStorage.getItem(LEGACY_KEYS.quickSettings);
    if (quickSettings) {
      try {
        const parsed = JSON.parse(quickSettings);
        if (Array.isArray(parsed)) {
          migrated.quickSettingsPinned = parsed;
        }
      } catch {
        // quickSettings might be stored as a simple array, not JSON
      }
    }

    // Migrate from calm-catalog-settings (legacy format)
    const calmSettings = localStorage.getItem(LEGACY_KEYS.calmCatalog);
    if (calmSettings) {
      const parsed = JSON.parse(calmSettings);
      // Only use these if not already set from neurodivergent settings
      if (parsed.reducedMotion !== undefined && migrated.reduceMotion === undefined) {
        migrated.reduceMotion = parsed.reducedMotion;
      }
      if (parsed.mutedColors !== undefined && migrated.mutedColors === undefined) {
        migrated.mutedColors = parsed.mutedColors;
      }
      if (parsed.highContrast !== undefined && migrated.highContrast === undefined) {
        migrated.highContrast = parsed.highContrast;
      }
      if (parsed.showImages !== undefined && migrated.showImages === undefined) {
        migrated.showImages = parsed.showImages;
      }
      if (parsed.breakRemindersEnabled !== undefined && migrated.breakReminders === undefined) {
        migrated.breakReminders = parsed.breakRemindersEnabled;
      }
      if (parsed.breakIntervalMinutes !== undefined && migrated.breakIntervalMinutes === undefined) {
        migrated.breakIntervalMinutes = parsed.breakIntervalMinutes;
      }
    }

    logger.info('Migrated settings from legacy storage keys', {
      migratedKeys: Object.keys(migrated)
    });
  } catch (error: unknown) {
    logger.error('Error during settings migration:', error);
  }

  return migrated;
}

function performMigrationIfNeeded(): Partial<AccessibilitySettings> | null {
  try {
    const currentVersion = localStorage.getItem(MIGRATION_VERSION_KEY);

    // Check if any legacy keys exist
    const hasLegacyData = Object.values(LEGACY_KEYS).some(
      key => localStorage.getItem(key) !== null
    );

    // If no legacy data and we're at current version, no migration needed
    if (!hasLegacyData && currentVersion === String(MIGRATION_VERSION)) {
      return null;
    }

    // Perform migration
    const migrated = migrateFromLegacySettings();

    // Mark migration as complete
    localStorage.setItem(MIGRATION_VERSION_KEY, String(MIGRATION_VERSION));

    return Object.keys(migrated).length > 0 ? migrated : null;
  } catch (error: unknown) {
    logger.error('Migration check failed:', error);
    return null;
  }
}

export function useSettingsPersistence(
  settings: AccessibilitySettings
): void {
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
    } catch (error: unknown) {
      logger.error('Failed to save accessibility settings:', error);
      // Silently fail - don't break the app if localStorage is unavailable
    }
  }, [settings]);
}

export function loadSettingsFromStorage(): AccessibilitySettings {
  try {
    // Defensive check for localStorage availability
    if (typeof localStorage === 'undefined') {
      return DEFAULT_SETTINGS;
    }

    // Check for and perform migration from legacy keys
    const migratedSettings = performMigrationIfNeeded();

    const saved = localStorage.getItem(STORAGE_KEY);

    // If no saved settings, use migrated or defaults
    if (!saved) {
      if (migratedSettings) {
        // Save migrated settings as the new unified settings
        const merged = validateAndMergeSettings(migratedSettings, DEFAULT_SETTINGS);
        localStorage.setItem(STORAGE_KEY, JSON.stringify(merged));
        logger.info('Saved migrated settings to unified storage');
        return merged;
      }
      return DEFAULT_SETTINGS;
    }

    // Defensive parsing with validation
    let parsed: unknown;
    try {
      parsed = JSON.parse(saved);
    } catch (parseError) {
      logger.error('Invalid JSON in accessibility settings, clearing:', parseError);
      localStorage.removeItem(STORAGE_KEY);
      // Fall back to migrated settings if available
      if (migratedSettings) {
        const merged = validateAndMergeSettings(migratedSettings, DEFAULT_SETTINGS);
        localStorage.setItem(STORAGE_KEY, JSON.stringify(merged));
        return merged;
      }
      return DEFAULT_SETTINGS;
    }

    // Validate parsed is an object
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
      logger.error('Invalid accessibility settings structure, clearing');
      localStorage.removeItem(STORAGE_KEY);
      if (migratedSettings) {
        const merged = validateAndMergeSettings(migratedSettings, DEFAULT_SETTINGS);
        localStorage.setItem(STORAGE_KEY, JSON.stringify(merged));
        return merged;
      }
      return DEFAULT_SETTINGS;
    }

    // Merge: defaults -> migrated -> saved (saved takes priority)
    let finalSettings = { ...DEFAULT_SETTINGS };

    if (migratedSettings) {
      finalSettings = { ...finalSettings, ...migratedSettings };
    }

    // Validate and merge saved settings on top
    finalSettings = validateAndMergeSettings(
      parsed as Partial<AccessibilitySettings>,
      finalSettings
    );

    // Save the fully merged settings back
    localStorage.setItem(STORAGE_KEY, JSON.stringify(finalSettings));

    return finalSettings;
  } catch (error: unknown) {
    logger.error('Failed to load accessibility settings:', error);
    // Try to clear potentially corrupted data
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch {
      // Ignore removal errors
    }
    return DEFAULT_SETTINGS;
  }
}

export function hasStoredSettings(): boolean {
  try {
    return localStorage.getItem(STORAGE_KEY) !== null;
  } catch {
    return false;
  }
}

export function clearSettingsFromStorage(): void {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch (error: unknown) {
    logger.error('Failed to clear accessibility settings:', error);
  }
}

export function cleanupLegacyStorage(preserveNotificationQueue = true): void {
  try {
    Object.entries(LEGACY_KEYS).forEach(([name, key]) => {
      // Optionally preserve the notification queue as it contains actual notifications
      if (name === 'quietNotifications' && preserveNotificationQueue) {
        // Only remove settings, not the queue
        return;
      }
      localStorage.removeItem(key);
    });
    logger.info('Cleaned up legacy accessibility storage keys');
  } catch (error: unknown) {
    logger.error('Failed to clean up legacy storage:', error);
  }
}

export function hasLegacySettings(): boolean {
  try {
    return Object.values(LEGACY_KEYS).some(
      key => localStorage.getItem(key) !== null
    );
  } catch {
    return false;
  }
}

/**
 * Export legacy keys for external use (e.g., debugging)
 */
export { LEGACY_KEYS };

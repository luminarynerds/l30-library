/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Settings Migration Utility
 *
 * Handles conversion from NeurodivergentSettings (legacy) to AccessibilitySettings (modern)
 * Provides data validation, error handling, and comprehensive mapping logic
 */

import type { AccessibilitySettings } from '../types/accessibility.types';
import type { NeurodivergentSettings } from '../../../types/neurodivergent-settings';
import { DEFAULT_SETTINGS } from '../config/defaults.config';
import { logger } from '../../../utils/logger';

export function detectLegacySettingsInStorage(): boolean {
  try {
    const legacyKey = 'lsc-neurodivergent-settings';
    return localStorage.getItem(legacyKey) !== null;
  } catch (err: unknown) {
    logger.error('Failed to check for legacy settings:', err);
    return false;
  }
}

/**
 * Comprehensive mapping from legacy NeurodivergentSettings to modern AccessibilitySettings
 *
 * This function intelligently maps settings between the two systems:
 * - Direct mappings (1:1)
 * - Computed mappings (multiple legacy → single modern)
 * - Dropped mappings (legacy settings not applicable to modern system)
 * - Fallbacks to defaults for unmapped settings
 // eslint-disable-next-line complexity
 */
        // eslint-disable-next-line complexity
export function migrateNeurodivergentToAccessibility(
  legacySettings: NeurodivergentSettings
): AccessibilitySettings {
  try {
    // Start with default modern settings as baseline
    const modern: AccessibilitySettings = { ...DEFAULT_SETTINGS };

    if (!legacySettings) {
      logger.warn('Legacy settings are null/undefined, using defaults');
      return modern;
    }

    // ========================================
    // Sensory Settings Migration
    // ========================================
    if (legacySettings.sensory) {
      const sensory = legacySettings.sensory;

      // Font mapping: "dyslexic" → dyslexiaFont: true
      if (sensory.fontFamily === 'dyslexic') {
        modern.dyslexiaFont = true;
      }

      // Font size mapping (legacy uses 12-24px, modern uses normal/large/xlarge)
      if (sensory.fontSize) {
        if (sensory.fontSize >= 18) {
          modern.fontSize = 'large';
        } else if (sensory.fontSize >= 16) {
          modern.fontSize = 'normal';
        } else {
          modern.fontSize = 'normal'; // Fallback for smaller sizes
        }
      }

      // Line height mapping (legacy uses 1.0-2.5, modern uses normal/relaxed/loose)
      if (sensory.lineHeight) {
        if (sensory.lineHeight >= 2.0) {
          modern.lineSpacing = 'loose';
        } else if (sensory.lineHeight >= 1.7) {
          modern.lineSpacing = 'relaxed';
        } else {
          modern.lineSpacing = 'normal';
        }
      }

      // Letter spacing mapping (legacy uses 0-10px, modern uses normal/wide/wider)
      if (sensory.letterSpacing !== undefined && sensory.letterSpacing !== null) {
        if (sensory.letterSpacing >= 6) {
          modern.letterSpacing = 'wider';
          modern.letterSpacingBody = 'wider';
          modern.letterSpacingHeaders = 'wider';
        } else if (sensory.letterSpacing >= 3) {
          modern.letterSpacing = 'wide';
          modern.letterSpacingBody = 'wide';
          modern.letterSpacingHeaders = 'wide';
        } else {
          modern.letterSpacing = 'normal';
          modern.letterSpacingBody = 'normal';
          modern.letterSpacingHeaders = 'normal';
        }
      }

      // Direct mappings
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      modern.theme = (sensory.theme as any) || modern.theme;
      modern.mutedColors = sensory.mutedColors ?? modern.mutedColors;
      modern.reduceMotion = sensory.reducedMotion ?? modern.reduceMotion;
      modern.bionicReading = sensory.bionicReading ?? modern.bionicReading;
      modern.showImages = sensory.showImages ?? modern.showImages;
      modern.lineFocusGuide = sensory.readingRuler ?? modern.lineFocusGuide;

      // Disable autoplay videos if not shown
      if (!sensory.autoplayVideos) {
        // This would need to be implemented as a feature
        logger.info('Note: autoplay videos toggle not implemented in modern system');
      }

      // Visual noise mapping (legacy: none/low/medium → modern: reduceMotion/quiet settings)
      if (sensory.visualNoise === 'none') {
        modern.quietMode = true;
        modern.reduceMotion = true;
      } else if (sensory.visualNoise === 'low') {
        modern.quietModeLite = true;
      }
    }

    // ========================================
    // Focus Settings Migration
    // ========================================
    if (legacySettings.focus) {
      const focus = legacySettings.focus;

      modern.focusMode = focus.focusMode ?? modern.focusMode;
      modern.blinders = focus.blinders ?? modern.blinders;
      modern.breakReminders = focus.hyperfocusProtection ?? modern.breakReminders;

      // Distraction-free is combination of focus mode + reduced motion
      if (focus.distractionFree) {
        modern.focusMode = true;
        modern.whisperMode = true; // Quiet notifications
        modern.reduceMotion = true;
      }

      // Time boxing → could map to break reminders
      if (focus.timeBoxing) {
        modern.breakReminders = true;
        modern.breakIntervalMinutes = 25; // Pomodoro-style
      }

      // Single task → cognitive load reduction
      if (focus.singleTask) {
        modern.reducedCognitiveLoad = true;
      }
    }

    // ========================================
    // Processing Settings Migration
    // ========================================
    if (legacySettings.processing) {
      const processing = legacySettings.processing;

      modern.plainLanguage = processing.plainLanguage ?? modern.plainLanguage;
      modern.explicitConfirmations = processing.confirmActions ?? modern.explicitConfirmations;

      // Slow animations
      if (processing.slowAnimations) {
        modern.reduceMotion = true;
      }

      // Preview changes → keep as preference (note to implement)
      if (processing.previewChanges) {
        logger.info('Note: preview changes feature should be implemented');
      }

      // Audio descriptions → should be handled by accessibility tree
      if (processing.audioDescriptions) {
        logger.info('Note: audio descriptions should use native accessibility APIs');
      }

      // Content warnings (system feature, not user setting)
      if (!processing.contentWarnings) {
        logger.info('Note: content warnings toggle not migrated (system feature)');
      }
    }

    // ========================================
    // Anxiety Settings Migration
    // ========================================
    if (legacySettings.anxiety) {
      const anxiety = legacySettings.anxiety;

      modern.undoEnabled = anxiety.undoEnabled ?? modern.undoEnabled;
      modern.noFOMO = anxiety.noFOMO ?? modern.noFOMO;
      modern.anonymousMode = anxiety.anonymous ?? modern.anonymousMode;

      // Gentle reminders → use with notifications
      if (anxiety.gentleReminders) {
        modern.whisperMode = true;
        modern.noUrgentLanguage = true;
      }

      // Preview mode → similar to explicit confirmations
      if (anxiety.previewMode) {
        modern.explicitConfirmations = true;
      }

      // Calm availability → messaging feature
      if (anxiety.calmAvailability) {
        logger.info('Note: calm availability is messaging preference, not a setting');
      }

      // Hide deadlines → remove time pressure
      if (anxiety.hideDeadlines) {
        modern.removeTimePressure = true;
      }
    }

    // ========================================
    // Executive Function Settings Migration
    // ========================================
    if (legacySettings.executiveFunction) {
      const exec = legacySettings.executiveFunction;

      // Session resume → persist session
      modern.persistSession = exec.sessionResume ?? modern.persistSession;

      // Decision help → simplified view / reduced cognitive load
      if (exec.decisionHelp) {
        modern.reducedCognitiveLoad = true;
        modern.simplifiedView = true;
      }

      // Simplified choices → reduced options in UI
      if (exec.simplifiedChoices) {
        modern.reducedCognitiveLoad = true;
      }
    }

    // ========================================
    // Control Settings Migration
    // ========================================
    if (legacySettings.control) {
      const control = legacySettings.control;

      // Keyboard shortcuts - enable by default, but this is noted
      if (!control.keyboardShortcuts) {
        logger.info('Note: keyboard shortcuts disabled in legacy settings');
      }

      // Auto save
      if (control.autoSave) {
        modern.persistSession = true;
      }

      // Layout lock → predictable navigation
      if (control.layoutLock) {
        modern.predictableNavigation = true;
      }

      // Exact match (search) → feature implementation
      if (control.exactMatch) {
        logger.info('Note: exact match search preference should be stored separately');
      }

      // Routines → user preferences, not accessibility settings
      if (control.routines) {
        logger.info('Note: routines feature is not an accessibility setting');
      }
    }

    // ========================================
    // Interest Settings Migration
    // ========================================
    if (legacySettings.interest) {
      const interest = legacySettings.interest;

      // Gamification → toggle feature
      if (!interest.gamification) {
        modern.removeTimePressure = true; // Related concept
      }

      // Surprise me / rabbit holes → discovery mode
      if (!interest.surpriseMe && !interest.rabbitHoles) {
        modern.preferPagination = true; // Clear structure
      }

      // Discovery mode: off → simplified view
      if (interest.discoveryMode === 'off') {
        modern.simplifiedView = true;
      }

      logger.info('Note: interest settings are feature toggles, not core accessibility');
    }

    // ========================================
    // Practical Settings Migration
    // ========================================
    if (legacySettings.practical) {
      const practical = legacySettings.practical;

      // Large buttons → content density
      if (practical.largeButtons) {
        modern.contentDensity = 'spacious';
      }

      // Voice commands → voice control
      if (practical.voiceCommands) {
        modern.voiceControlEnabled = true;
      }

      // Non-verbal → remove text, use icons
      if (practical.nonVerbal) {
        logger.info('Note: non-verbal mode should reduce text display');
      }

      // Haptic feedback
      if (practical.hapticFeedback) {
        logger.info('Note: haptic feedback requires device API');
      }

      // Offline
      if (practical.offline) {
        logger.info('Note: offline mode is feature flag, not setting');
      }
    }

    // ========================================
    // Legacy Flat Settings Migration
    // ========================================

    // Direct legacy settings that exist at root level
    if (legacySettings.reducedMotion !== undefined) {
      modern.reduceMotion = legacySettings.reducedMotion;
    }

    if (legacySettings.mutedColors !== undefined) {
      modern.mutedColors = legacySettings.mutedColors;
    }

    if (legacySettings.highContrast !== undefined) {
      modern.highContrast = legacySettings.highContrast;
    }

    if (legacySettings.largeText !== undefined && legacySettings.largeText) {
      modern.fontSize = 'large';
    }

    if (legacySettings.showImages !== undefined) {
      modern.showImages = legacySettings.showImages;
    }

    if (legacySettings.breakRemindersEnabled !== undefined) {
      modern.breakReminders = legacySettings.breakRemindersEnabled;
    }

    if (legacySettings.breakIntervalMinutes !== undefined) {
      modern.breakIntervalMinutes = legacySettings.breakIntervalMinutes;
    }

    // Content density mapping
    if (legacySettings.contentDensity) {
      modern.contentDensity = legacySettings.contentDensity;
    }

    logger.info('Successfully migrated legacy accessibility settings', {
      timestamp: new Date().toISOString(),
      presetName: legacySettings.presetName,
    });

    return modern;
  } catch (error: unknown) {
    logger.error('Error during settings migration:', error);
    // Return defaults on error
    return DEFAULT_SETTINGS;
  }
}

/**
 * Reverse migration: Convert modern AccessibilitySettings back to legacy format
 * Used for backward compatibility export/import
 */
        // eslint-disable-next-line complexity
export function migrateAccessibilityToNeurodivergent(
         
  modern: AccessibilitySettings
): NeurodivergentSettings {
  // This is a partial migration - not all modern settings map back to legacy
  return {
    executiveFunction: {
      sessionResume: modern.persistSession ?? true,
      decisionHelp: modern.reducedCognitiveLoad ?? false,
      simplifiedChoices: modern.simplifiedView ?? false,
      taskBreakdown: false,
      progressTracking: true,
    },
    sensory: {
      fontFamily: modern.dyslexiaFont ? 'dyslexic' : 'standard',
      fontSize: modern.fontSize === 'xlarge' ? 20 : modern.fontSize === 'large' ? 18 : 16,
      lineHeight: modern.lineSpacing === 'loose' ? 2.0 : modern.lineSpacing === 'relaxed' ? 1.7 : 1.5,
      letterSpacing: modern.letterSpacing === 'wider' ? 6 : modern.letterSpacing === 'wide' ? 3 : 0,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      theme: (modern.theme as any) ?? 'auto',
      mutedColors: modern.mutedColors ?? false,
      reducedMotion: modern.reduceMotion ?? false,
      readingRuler: modern.lineFocusGuide ?? false,
      bionicReading: modern.bionicReading ?? false,
      visualNoise: modern.quietMode ? 'none' : modern.quietModeLite ? 'low' : 'medium',
      showImages: modern.showImages ?? true,
      autoplayVideos: false, // Default to off
    },
    focus: {
      focusMode: modern.focusMode ?? false,
      blinders: modern.blinders ?? false,
      distractionFree: modern.focusMode ?? false,
      singleTask: modern.reducedCognitiveLoad ?? false,
      timeBoxing: modern.breakReminders ?? false,
      hyperfocusProtection: modern.breakReminders ?? true,
    },
    processing: {
      plainLanguage: modern.plainLanguage ?? false,
      audioDescriptions: false,
      contentWarnings: true,
      slowAnimations: modern.reduceMotion ?? false,
      confirmActions: modern.explicitConfirmations ?? false,
      previewChanges: false,
    },
    anxiety: {
      undoEnabled: modern.undoEnabled ?? true,
      previewMode: modern.explicitConfirmations ?? false,
      calmAvailability: false,
      noFOMO: modern.noFOMO ?? false,
      anonymous: modern.anonymousMode ?? false,
      hideDeadlines: modern.removeTimePressure ?? false,
      gentleReminders: modern.noUrgentLanguage ?? true,
    },
    control: {
      routines: false,
      exactMatch: false,
      layoutLock: modern.predictableNavigation ?? false,
      customDefaults: {},
      keyboardShortcuts: true,
      autoSave: modern.persistSession ?? true,
    },
    interest: {
      gamification: true,
      surpriseMe: false,
      rabbitHoles: true,
      discoveryMode: modern.simplifiedView ? 'off' : 'full',
      hideSpoilers: false,
    },
    practical: {
      offline: false,
      voiceCommands: modern.voiceControlEnabled ?? false,
      nonVerbal: false,
      largeButtons: modern.contentDensity === 'spacious',
      hapticFeedback: false,
    },
    reducedMotion: modern.reduceMotion ?? false,
    mutedColors: modern.mutedColors ?? false,
    largeText: modern.fontSize === 'xlarge' || modern.fontSize === 'large',
    highContrast: modern.highContrast ?? false,
    soundsEnabled: true,
    breakRemindersEnabled: modern.breakReminders ?? false,
    breakIntervalMinutes: modern.breakIntervalMinutes ?? 30,
    showImages: modern.showImages ?? true,
    contentDensity: modern.contentDensity ?? 'comfortable',
    version: 1,
  };
}

export function validateMigratedSettings(settings: AccessibilitySettings): boolean {
  try {
    // Check for required properties
    const requiredProps = [
      'fontSize',
      'lineSpacing',
      'theme',
      'reduceMotion',
    ];

    for (const prop of requiredProps) {
      if (!(prop in settings)) {
        logger.warn(`Missing required property in migrated settings: ${prop}`);
        return false;
      }
    }

    return true;
  } catch (error: unknown) {
    logger.error('Settings validation failed:', error);
    return false;
  }
}

export function clearLegacySettings(): void {
  try {
    localStorage.removeItem('lsc-neurodivergent-settings');
    logger.info('Cleared legacy neurodivergent settings from storage');
  } catch (error: unknown) {
    logger.error('Failed to clear legacy settings:', error);
  }
}

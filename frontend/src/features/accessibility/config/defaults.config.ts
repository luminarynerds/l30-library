/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import type { AccessibilitySettings, AccessibilityProfile } from '../types/accessibility.types';

function getCultureAwareDefaults(locale: string = 'en'): Partial<AccessibilitySettings> {
  // Culture-specific defaults are now offered via prompt, not applied silently
  const cultureDefaults: Record<string, Partial<AccessibilitySettings>> = {
    'ar': {}, // RTL handled by CSS
    'default': {}
  };
  return (cultureDefaults[locale] || cultureDefaults.default) as Partial<AccessibilitySettings>;
}

export const CULTURE_SUGGESTIONS: Record<string, { message: string; settings: Partial<AccessibilitySettings> }> = {
  'zh': { message: 'Would you like larger text and higher contrast for better CJK character readability?', settings: { highContrast: true, fontSize: 'large' } },
  'ja': { message: 'Would you like larger text and higher contrast for better readability?', settings: { highContrast: true, fontSize: 'large' } },
  'ko': { message: 'Would you like larger text and higher contrast for better readability?', settings: { highContrast: true, fontSize: 'large' } },
};

export const BUILT_IN_PROFILES: AccessibilityProfile[] = [
  {
    id: 'reading',
    name: 'Reading Mode',
    icon: 'BookOpen',
    settings: {
      focusMode: true,
      dyslexiaFont: false,
      lineSpacing: 'relaxed',
      fontSize: 'large',
      reduceMotion: true,
    },
    createdAt: '2026-01-01T00:00:00.000Z',
  },
  {
    id: 'presenting',
    name: 'Presenting',
    icon: 'Monitor',
    settings: {
      fontSize: 'xlarge',
      highContrast: true,
      lineSpacing: 'loose',
      reduceMotion: true,
    },
    createdAt: '2026-01-01T00:00:00.000Z',
  },
  {
    id: 'low-light',
    name: 'Low Light',
    icon: 'Moon',
    settings: {
      theme: 'dark',
      highContrast: false,
      mutedColors: true,
      reduceMotion: true,
    },
    createdAt: '2026-01-01T00:00:00.000Z',
  },
];

function createDefaultSettings(): AccessibilitySettings {
  // Get current language (fallback to 'en' if not available)
  const currentLanguage = typeof navigator !== 'undefined'
    ? navigator.language.split('-')[0] || 'en'
    : 'en';

  // Get culture-aware defaults
  const cultureDefaults = getCultureAwareDefaults(currentLanguage);

  // Base defaults
  const baseDefaults: AccessibilitySettings = {
    // Dyslexia Support
    dyslexiaFont: false,
    letterSpacing: 'normal',

    // Text Customization
    fontSize: 'normal',
    lineSpacing: 'normal',
    fontWeight: 400,
    letterSpacingBody: 'normal',
    letterSpacingHeaders: 'normal',

    // Visual Theme
    theme: 'light',
    autoThemeSchedule: 'system',
    autoThemeDarkStart: 19,
    autoThemeLightStart: 7,
    reduceMotion: false,
    highContrast: false,
    colorBlindMode: 'none',

    // Reading Assistance
    readingGuide: false,
    focusMode: false,

    // Neuro-Inclusive Features
    quietMode: false,
    quietModeLite: false,
    keyboardShortcutsEnabled: true,
    reducedCognitiveLoad: false,
    predictableNavigation: false,
    enhancedFocus: false,
    enhancedFocusOpacity: 80,
    enhancedFocusIndicatorOnly: false,

    // Neurodivergent-First Features
    contentDensity: 'comfortable',
    preferPagination: false,
    simplifiedView: false,
    plainLanguage: false,
    removeTimePressure: false,
    hideDecorativeImages: false,
    explicitConfirmations: false,
    lineFocusGuide: false,
    persistSession: true, // Default to enabled for better UX

    // Device Settings
    enableCameraFeatures: true, // Default enabled for library functionality
    enableARFeatures: true, // Default enabled for modern library features
    enableBarcodeScanning: true, // Default enabled for inventory/checkouts

    // Privacy Settings (consolidated from AnonymousBrowsing)
    anonymousMode: false,
    disableSearchHistory: false,
    disableViewHistory: false,
    disableRecommendations: false,
    disableTracking: false,
    autoClearOnExit: false,

    // Notification Settings (consolidated from QuietNotifications)
    whisperMode: true, // Default to calmer notifications
    batchNotifications: false,
    batchTime: 'morning',
    batchHour: 9,
    noUrgentLanguage: true, // Default to calmer language
    showNotificationBadge: true,
    autoDismissSeconds: 0, // Manual dismiss by default

    // Quick Settings Toolbar
    quickSettingsPinned: ['focusMode', 'theme', 'readingGuide', 'anonymousMode'],
    showQuickSettings: true,
    quickSettingsPosition: 'bottom-left',

    // Cognitive Support (consolidated from NeurodivergentSettings)
    bionicReading: false,
    mutedColors: false,
    blinders: false,
    breakReminders: false,
    breakIntervalMinutes: 30,
    noFOMO: false,
    undoEnabled: true, // Default to enabled for anxiety reduction
    undoWindowSeconds: 30,
    showImages: true,

    // Focus Customization (WCAG 2.2)
    focusRingColor: 'orange', // Default brand color
    customFocusRingColor: '#C67C48',

    // Reading Assistance Tools
    readingTool: 'none',
    readingMaskOpacity: 75,
    readingMaskHeight: 80,

    // Voice Control
    voiceControlEnabled: false, // Opt-in feature
    voiceControlLanguage: '', // Uses main language if empty
    voiceControlContinuous: true, // Continuous listening when enabled

    // Session Awareness
    showSessionTime: false, // Opt-in to avoid pressure
    sessionTimeWarningMinutes: 60, // Gentle reminder after 1 hour

    // Profiles
    builtInProfiles: BUILT_IN_PROFILES,
    savedProfiles: [],
  };

  // Merge culture-aware defaults with base defaults
  return { ...baseDefaults, ...cultureDefaults };
}

export const DEFAULT_SETTINGS: AccessibilitySettings = createDefaultSettings();

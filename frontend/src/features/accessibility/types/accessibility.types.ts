/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
// Language Types

/**
 * Supported languages for the application.
 * Based on ISO 639-1 language codes.
 */
export const LANGUAGES = ['en', 'es', 'fr', 'de', 'zh', 'ar', 'ru'] as const;

export type Language = typeof LANGUAGES[number];

// Font and Typography Types

/**
 * Available font sizes for text scaling
 */
export const FONT_SIZES = ['normal', 'large', 'xlarge'] as const;

export type FontSize = typeof FONT_SIZES[number];

/**
 * Line spacing options for improved readability
 */
export const LINE_SPACINGS = ['normal', 'relaxed', 'loose'] as const;

export type LineSpacing = typeof LINE_SPACINGS[number];

/**
 * Letter spacing options for dyslexia support
 */
export const LETTER_SPACINGS = ['normal', 'wide', 'wider'] as const;

export type LetterSpacing = typeof LETTER_SPACINGS[number];

/**
 * Font weight options for enhanced readability
 */
export const FONT_WEIGHTS = [400, 500, 600] as const;

export type FontWeight = typeof FONT_WEIGHTS[number];

// Theme and Visual Types

/**
 * Available theme modes
 */
export const THEMES = ['light', 'dark', 'high-contrast', 'system'] as const;

export type Theme = typeof THEMES[number];

/**
 * Auto theme schedule options for time-based theme switching
 */
export const AUTO_THEME_SCHEDULES = ['system', 'solar', 'custom'] as const;

export type AutoThemeSchedule = typeof AUTO_THEME_SCHEDULES[number];

/**
 * Color blind mode options for visual accessibility
 */
export const COLOR_BLIND_MODES = [
  'none',
  'deuteranopia',  // Red-green color blindness (most common)
  'protanopia',    // Red-green color blindness
  'tritanopia',    // Blue-yellow color blindness
  'achromatopsia'  // Complete color blindness (monochrome)
] as const;

export type ColorBlindMode = typeof COLOR_BLIND_MODES[number];

/**
 * Enhanced focus dimming opacity levels
 */
export const ENHANCED_FOCUS_OPACITIES = [50, 60, 70, 80] as const;

export type EnhancedFocusOpacity = typeof ENHANCED_FOCUS_OPACITIES[number];

/**
 * Focus ring color options for customization (WCAG 2.2 compliant)
 */
export const FOCUS_RING_COLORS = [
  'orange',
  'blue',
  'green',
  'purple',
  'pink',
  'cyan',
  'yellow',
  'custom',
] as const;

export type FocusRingColor = typeof FOCUS_RING_COLORS[number];

/**
 * Reading assistance tool options
 */
export const READING_TOOLS = ['none', 'mask', 'guide', 'both'] as const;

export type ReadingTool = typeof READING_TOOLS[number];

// Profile Types

export interface AccessibilityProfile {
  id: string;
  name: string;
  icon?: string; // lucide icon name
  settings: Partial<AccessibilitySettings>;
  createdAt: string;
}

// Main Settings Interface

export interface AccessibilitySettings {
  // Legacy/backward compatibility properties
  largeText?: boolean;
  sessionResume?: boolean;
  experienceLevel?: string;
  neurodivergentSettings?: object;

  // Language is deliberately NOT part of accessibility settings.
  // I18nContext owns it; a second copy here caused saved settings to
  // stomp the user's language choice on every page load.

  // Dyslexia Support

  /** Enable OpenDyslexic font family */
  dyslexiaFont: boolean;

  /** Letter spacing for all text (legacy, kept for backward compatibility) */
  letterSpacing: LetterSpacing;

  // Text Customization

  /** Global font size multiplier */
  fontSize: FontSize;

  /** Line height for better readability */
  lineSpacing: LineSpacing;

  /** Base font weight */
  fontWeight: FontWeight;

  /** Letter spacing for body text only */
  letterSpacingBody: LetterSpacing;

  /** Letter spacing for headers only */
  letterSpacingHeaders: LetterSpacing;

  // Visual Theme

  /** Color theme (light/dark/high-contrast) */
  theme: Theme;

  /** Auto theme schedule mode (system/solar/custom) */
  autoThemeSchedule: AutoThemeSchedule;

  /** Hour (0-23) when dark theme starts for custom schedule */
  autoThemeDarkStart: number;

  /** Hour (0-23) when light theme starts for custom schedule */
  autoThemeLightStart: number;

  /** Disable animations and transitions */
  reduceMotion: boolean;

  /** High contrast mode for better visibility */
  highContrast: boolean;

  /** Color blind mode filter */
  colorBlindMode: ColorBlindMode;

  // Reading Assistance

  /** Show horizontal reading guide line */
  readingGuide: boolean;

  /** Focus mode - minimizes distractions */
  focusMode: boolean;

  // Neuro-Inclusive Features (WCAG 2.2 / 3.0)

  /** Quiet Mode - collapses carousels, hides animations, reduces saturation */
  quietMode: boolean;

  /** Quiet Mode Lite - quiet mode but keeps functional animations */
  quietModeLite: boolean;

  /** Single-key keyboard shortcuts on the catalog (WCAG 2.1.4 opt-out) */
  keyboardShortcutsEnabled: boolean;

  /** Reduced Cognitive Load - simplifies layouts, removes decorative elements */
  reducedCognitiveLoad: boolean;

  /** Predictable Navigation - shows breadcrumbs, persistent undo */
  predictableNavigation: boolean;

  /** Enhanced Focus - highlights active element, dims background (ADHD/Autism support) */
  enhancedFocus: boolean;

  /** Dimming intensity when enhanced focus is active (lower = more dimmed) */
  enhancedFocusOpacity: EnhancedFocusOpacity;

  /** Focus ring only, no background dimming */
  enhancedFocusIndicatorOnly: boolean;

  // Neurodivergent-First Features

  /** Content density preference (affects spacing and visual density) */
  contentDensity: 'compact' | 'comfortable' | 'spacious';

  /** Prefer pagination over infinite scroll (clear completion points) */
  preferPagination: boolean;

  /** Simplified view mode (remove decorative elements, focus on content) */
  simplifiedView: boolean;

  /** Plain language mode (replace jargon with simple terms) */
  plainLanguage: boolean;

  /** Remove time pressure elements (trending, "X viewing now", etc.) */
  removeTimePressure: boolean;

  /** Hide decorative images (reduce visual noise) */
  hideDecorativeImages: boolean;

  /** Explicit confirmations for actions (reduce anxiety about mistakes) */
  explicitConfirmations: boolean;

  /** Line focus guide for reading (highlight current line) */
  lineFocusGuide: boolean;

  /** Session persistence (save and restore state) */
  persistSession: boolean;

  // Device Settings

  /** Enable camera-based features (barcode scanning, photo capture) */
  enableCameraFeatures: boolean;

  /** Enable AR features for book previews and local history */
  enableARFeatures: boolean;

  /** Enable automatic barcode scanning */
  enableBarcodeScanning: boolean;

  // Privacy Settings (consolidated from AnonymousBrowsing)

  /** Enable anonymous/private browsing mode */
  anonymousMode: boolean;

  /** Disable search history tracking */
  disableSearchHistory: boolean;

  /** Disable view history tracking */
  disableViewHistory: boolean;

  /** Disable personalized recommendations */
  disableRecommendations: boolean;

  /** Disable activity tracking */
  disableTracking: boolean;

  /** Automatically clear history on exit */
  autoClearOnExit: boolean;

  // Notification Settings (consolidated from QuietNotifications)

  /** Whisper mode - subtle, non-intrusive notifications */
  whisperMode: boolean;

  /** Batch notifications instead of real-time delivery */
  batchNotifications: boolean;

  /** Time to deliver batched notifications */
  batchTime: 'morning' | 'afternoon' | 'evening' | 'never';

  /** Hour for batch delivery (0-23) */
  batchHour: number;

  /** Never use urgent language in notifications */
  noUrgentLanguage: boolean;

  /** Show notification count badge */
  showNotificationBadge: boolean;

  /** Auto-dismiss notifications after X seconds (0 = manual) */
  autoDismissSeconds: number;

  // Quick Settings Toolbar

  /** IDs of settings pinned to quick settings toolbar */
  quickSettingsPinned: string[];

  /** Show the quick settings toolbar */
  showQuickSettings: boolean;

  /** Quick settings toolbar position */
  quickSettingsPosition: 'bottom-right' | 'bottom-left' | 'top-right' | 'top-left';

  // Cognitive Support (consolidated from NeurodivergentSettings)

  /** Enable bionic reading (bold word beginnings) */
  bionicReading: boolean;

  /** Use muted/calm color palette */
  mutedColors: boolean;

  /** Enable blinders (narrow focus area) */
  blinders: boolean;

  /** Enable break reminders */
  breakReminders: boolean;

  /** Break reminder interval in minutes */
  breakIntervalMinutes: number;

  /** Hide FOMO-inducing elements (trending, "X people viewing") */
  noFOMO: boolean;

  /** Enable undo functionality with time window */
  undoEnabled: boolean;

  /** Undo time window in seconds */
  undoWindowSeconds: number;

  /** Show images in catalog/content */
  showImages: boolean;

  // Focus Customization (WCAG 2.2)

  /** Focus ring color for keyboard navigation indicators */
  focusRingColor: FocusRingColor;

  /** Custom focus ring color (hex value, used when focusRingColor is 'custom') */
  customFocusRingColor: string;

  // Reading Assistance Tools

  /** Active reading tool (mask, guide, both, or none) */
  readingTool: ReadingTool;

  /** Reading mask opacity (0-100) */
  readingMaskOpacity: number;

  /** Reading mask window height in pixels */
  readingMaskHeight: number;

  // Voice Control

  /** Enable voice control navigation */
  voiceControlEnabled: boolean;

  /** Voice control language (uses main language setting if not specified) */
  voiceControlLanguage: string;

  /** Continuous listening mode for voice control */
  voiceControlContinuous: boolean;

  // Session Awareness

  /** Show session time in UI */
  showSessionTime: boolean;

  /** Maximum session time warning threshold in minutes (0 = disabled) */
  sessionTimeWarningMinutes: number;

  // Profiles

  /** Built-in accessibility profiles */
  builtInProfiles: AccessibilityProfile[];

  /** User-saved accessibility profiles */
  savedProfiles: AccessibilityProfile[];

  // Sensory Settings

  /** Sensory sensitivity configuration */
  sensory?: {
    reduceVisualStimulation?: boolean;
    reduceAudioStimulation?: boolean;
    reduceTactileFeedback?: boolean;
    reduceMotion?: boolean;
  };
}

// Context Types

export interface AccessibilityContextType {
  settings: AccessibilitySettings;
  updateSetting: UpdateSetting;
  resetSettings: () => void;
  updateSettings?: UpdateSetting; // Alias for backward compatibility
}

// Type Utilities

export type SettingKey = keyof AccessibilitySettings;

export type SettingValue<K extends SettingKey> = AccessibilitySettings[K];

export interface UpdateSetting {
  <K extends SettingKey>(key: K, value: SettingValue<K>): void;
}

export type PartialSettings = Partial<AccessibilitySettings>;

export interface ValidationResult {
  valid: boolean;
  errors: Array<{
    key: string;
    value: unknown;
    message: string;
  }>;
}

// Type Guards

export function isLanguage(value: unknown): value is Language {
  return typeof value === 'string' && LANGUAGES.includes(value as Language);
}

export function isFontSize(value: unknown): value is FontSize {
  return typeof value === 'string' && FONT_SIZES.includes(value as FontSize);
}

export function isLineSpacing(value: unknown): value is LineSpacing {
  return typeof value === 'string' && LINE_SPACINGS.includes(value as LineSpacing);
}

export function isLetterSpacing(value: unknown): value is LetterSpacing {
  return typeof value === 'string' && LETTER_SPACINGS.includes(value as LetterSpacing);
}

export function isTheme(value: unknown): value is Theme {
  return typeof value === 'string' && THEMES.includes(value as Theme);
}

export function isColorBlindMode(value: unknown): value is ColorBlindMode {
  return typeof value === 'string' && COLOR_BLIND_MODES.includes(value as ColorBlindMode);
}

export function isFontWeight(value: unknown): value is FontWeight {
  return typeof value === 'number' && FONT_WEIGHTS.includes(value as FontWeight);
}

export function isEnhancedFocusOpacity(value: unknown): value is EnhancedFocusOpacity {
  return typeof value === 'number' && ENHANCED_FOCUS_OPACITIES.includes(value as EnhancedFocusOpacity);
}

export function isSettingKey(value: unknown): value is SettingKey {
  if (typeof value !== 'string') return false;

  const validKeys: SettingKey[] = [
    'dyslexiaFont',
    'letterSpacing',
    'fontSize',
    'lineSpacing',
    'fontWeight',
    'letterSpacingBody',
    'letterSpacingHeaders',
    'theme',
    'reduceMotion',
    'highContrast',
    'colorBlindMode',
    'readingGuide',
    'focusMode',
    'quietMode',
    'quietModeLite',
    'keyboardShortcutsEnabled',
    'reducedCognitiveLoad',
    'predictableNavigation',
    'enhancedFocus',
    'enhancedFocusOpacity',
    'enhancedFocusIndicatorOnly',
    // Neurodivergent-first features
    'contentDensity',
    'preferPagination',
    'simplifiedView',
    'plainLanguage',
    'removeTimePressure',
    'hideDecorativeImages',
    'explicitConfirmations',
    'lineFocusGuide',
    'persistSession',
    // Device settings
    'enableCameraFeatures',
    'enableARFeatures',
    'enableBarcodeScanning',
    // Privacy settings
    'anonymousMode',
    'disableSearchHistory',
    'disableViewHistory',
    'disableRecommendations',
    'disableTracking',
    'autoClearOnExit',
    // Notification settings
    'whisperMode',
    'batchNotifications',
    'batchTime',
    'batchHour',
    'noUrgentLanguage',
    'showNotificationBadge',
    'autoDismissSeconds',
    // Quick settings
    'quickSettingsPinned',
    'showQuickSettings',
    'quickSettingsPosition',
    // Cognitive support
    'bionicReading',
    'mutedColors',
    'blinders',
    'breakReminders',
    'breakIntervalMinutes',
    'noFOMO',
    'undoEnabled',
    'undoWindowSeconds',
    'showImages',
    // Focus customization
    'focusRingColor',
    'customFocusRingColor',
    // Reading assistance
    'readingTool',
    'readingMaskOpacity',
    'readingMaskHeight',
    // Voice control
    'voiceControlEnabled',
    'voiceControlLanguage',
    'voiceControlContinuous',
    // Session awareness
    'showSessionTime',
    'sessionTimeWarningMinutes',
    // Auto theme schedule
    'autoThemeSchedule',
    'autoThemeDarkStart',
    'autoThemeLightStart',

    // Profiles
    'builtInProfiles',
    'savedProfiles',
  ];

  return validKeys.includes(value as SettingKey);
}

export function isFocusRingColor(value: unknown): value is FocusRingColor {
  return typeof value === 'string' && FOCUS_RING_COLORS.includes(value as FocusRingColor);
}

export function isReadingTool(value: unknown): value is ReadingTool {
  return typeof value === 'string' && READING_TOOLS.includes(value as ReadingTool);
}

export function isAutoThemeSchedule(value: unknown): value is AutoThemeSchedule {
  return typeof value === 'string' && AUTO_THEME_SCHEDULES.includes(value as AutoThemeSchedule);
}

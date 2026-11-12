/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import type {
  FontSize,
  LineSpacing,
  LetterSpacing,
  ColorBlindMode,
} from '../types/accessibility.types';

export const THEME_CLASSES = {
  // Font size classes
  fontSize: {
    normal: 'font-size-normal',
    large: 'font-size-large',
    xlarge: 'font-size-xlarge',
  } as Record<FontSize, string>,

  // Line spacing classes
  lineSpacing: {
    normal: 'leading-normal',
    relaxed: 'leading-relaxed',
    loose: 'leading-loose',
  } as Record<LineSpacing, string>,

  // Letter spacing classes (legacy)
  letterSpacing: {
    normal: 'letter-spacing-normal',
    wide: 'letter-spacing-wide',
    wider: 'letter-spacing-wider',
  } as Record<LetterSpacing, string>,

  // Letter spacing classes (body text)
  letterSpacingBody: {
    normal: 'letter-spacing-body-normal',
    wide: 'letter-spacing-body-wide',
    wider: 'letter-spacing-body-wider',
  } as Record<LetterSpacing, string>,

  // Letter spacing classes (headers)
  letterSpacingHeaders: {
    normal: 'letter-spacing-headers-normal',
    wide: 'letter-spacing-headers-wide',
    wider: 'letter-spacing-headers-wider',
  } as Record<LetterSpacing, string>,

  // Color blind mode classes
  colorBlindMode: {
    none: '',
    deuteranopia: 'theme-deuteranopia',
    protanopia: 'theme-protanopia',
    tritanopia: 'theme-tritanopia',
    achromatopsia: 'theme-achromatopsia',
  } as Record<ColorBlindMode, string>,

  // Boolean setting classes (applied when true)
  dyslexiaFont: 'dyslexia-font',
  highContrast: 'high-contrast',
  reduceMotion: 'reduce-motion',
  readingGuide: 'reading-guide',
  focusMode: 'focus-mode',
  quietMode: 'quiet-mode',
  quietModeLite: 'quiet-mode-lite',
  reducedCognitiveLoad: 'reduced-cognitive-load',
  predictableNavigation: 'predictable-navigation',
  enhancedFocus: 'enhanced-focus',
  enhancedFocusIndicatorOnly: 'enhanced-focus-indicator-only',
  dark: 'dark',
  // Quick settings toggles
  plainLanguage: 'plain-language',
  noFOMO: 'no-fomo',
  anonymousMode: 'anonymous-mode',
  blinders: 'blinders',
  bionicReading: 'bionic-reading',
  mutedColors: 'muted-colors',
} as const;

/**
 * CSS custom property (CSS variable) values
 *
 * These values are set as CSS variables on document.documentElement
 * for dynamic styling based on accessibility settings.
 */
export const CSS_VARIABLES = {
  // Font size scale multipliers
  fontSize: {
    normal: '1',
    large: '1.125',
    xlarge: '1.25',
  } as Record<FontSize, string>,

  // Line height values
  lineSpacing: {
    normal: '1.5',
    relaxed: '1.75',
    loose: '2',
  } as Record<LineSpacing, string>,

  // Letter spacing values (em units)
  letterSpacing: {
    normal: '0',
    wide: '0.05em',
    wider: '0.1em',
  } as Record<LetterSpacing, string>,

  // Font weight values
  fontWeight: {
    400: '400',
    500: '500',
    600: '600',
  } as Record<400 | 500 | 600, string>,

  // Enhanced focus opacity values (0-1 range)
  enhancedFocusOpacity: {
    50: '0.5',
    60: '0.6',
    70: '0.7',
    80: '0.8',
  } as Record<50 | 60 | 70 | 80, string>,
} as const;

/**
 * CSS variable names used in the application
 *
 * Maps setting keys to CSS custom property names for easy reference
 */
export const CSS_VARIABLE_NAMES = {
  fontScale: '--font-scale',
  fontWeight: '--font-weight-base',
  lineHeight: '--line-height',
  letterSpacing: '--letter-spacing',
  enhancedFocusOpacity: '--enhanced-focus-opacity',
} as const;

/**
 * Class groups for easier cleanup
 *
 * When a setting changes, all classes in its group are removed
 * before applying the new class.
 */
export const CLASS_GROUPS = {
  fontSize: ['font-size-normal', 'font-size-large', 'font-size-xlarge'],
  lineSpacing: ['leading-normal', 'leading-relaxed', 'leading-loose'],
  letterSpacing: ['letter-spacing-normal', 'letter-spacing-wide', 'letter-spacing-wider'],
  letterSpacingBody: [
    'letter-spacing-body-normal',
    'letter-spacing-body-wide',
    'letter-spacing-body-wider',
  ],
  letterSpacingHeaders: [
    'letter-spacing-headers-normal',
    'letter-spacing-headers-wide',
    'letter-spacing-headers-wider',
  ],
  colorBlindMode: [
    'theme-deuteranopia',
    'theme-protanopia',
    'theme-tritanopia',
    'theme-achromatopsia',
  ],
  theme: ['dark', 'high-contrast'],
} as const;

export function getThemeClass(
  settingKey: keyof typeof THEME_CLASSES,
  value: string | number | boolean
): string {
  const classMap = THEME_CLASSES[settingKey];

  if (typeof classMap === 'string') {
    // Boolean setting - return class if value is true
    return value ? classMap : '';
  }

  if (typeof classMap === 'object' && classMap !== null) {
    // Value-based setting - lookup class by value
    return (classMap as Record<string, string>)[String(value)] || '';
  }

  return '';
}

export function getCSSVariableValue(
  settingKey: keyof typeof CSS_VARIABLES,
  value: string | number
): string {
  const variableMap = CSS_VARIABLES[settingKey];

  if (typeof variableMap === 'object' && variableMap !== null) {
    return (variableMap as Record<string, string>)[String(value)] || '';
  }

  return '';
}

export function getClassGroup(settingKey: keyof typeof CLASS_GROUPS): readonly string[] {
  return CLASS_GROUPS[settingKey] || [];
}

// Export legacy class group constants for backwards compatibility
export const FONT_SIZE_CLASSES = THEME_CLASSES.fontSize;
export const LINE_SPACING_CLASSES = THEME_CLASSES.lineSpacing;
export const LETTER_SPACING_CLASSES = THEME_CLASSES.letterSpacing;
export const BODY_LETTER_SPACING_CLASSES = THEME_CLASSES.letterSpacingBody;
export const HEADER_LETTER_SPACING_CLASSES = THEME_CLASSES.letterSpacingHeaders;
export const COLOR_BLIND_MODE_CLASSES = THEME_CLASSES.colorBlindMode;
export const ALL_FONT_SIZE_CLASSES = CLASS_GROUPS.fontSize;
export const ALL_LINE_SPACING_CLASSES = CLASS_GROUPS.lineSpacing;
export const ALL_LETTER_SPACING_CLASSES = CLASS_GROUPS.letterSpacing;
export const ALL_BODY_LETTER_SPACING_CLASSES = CLASS_GROUPS.letterSpacingBody;
export const ALL_HEADER_LETTER_SPACING_CLASSES = CLASS_GROUPS.letterSpacingHeaders;
export const ALL_COLOR_BLIND_MODE_CLASSES = CLASS_GROUPS.colorBlindMode;
export const FONT_SCALE_VALUES = CSS_VARIABLES.fontSize;

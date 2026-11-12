/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
/**
 * CSS Applicator Utilities
 * Functions to apply accessibility settings to the DOM
 */

import type { AccessibilitySettings } from '../types/accessibility.types';
import { loadTheme } from '@/utils/themeLoader';
import {
  isTheme,
  isFontSize,
  isLineSpacing,
  isLetterSpacing,
  isColorBlindMode,
  isFontWeight,
  isEnhancedFocusOpacity,
} from '../types/accessibility.types';
import {
  FONT_SIZE_CLASSES,
  FONT_SCALE_VALUES,
  LINE_SPACING_CLASSES,
  LETTER_SPACING_CLASSES,
  BODY_LETTER_SPACING_CLASSES,
  HEADER_LETTER_SPACING_CLASSES,
  COLOR_BLIND_MODE_CLASSES,
  ALL_FONT_SIZE_CLASSES,
  ALL_LINE_SPACING_CLASSES,
  ALL_LETTER_SPACING_CLASSES,
  ALL_BODY_LETTER_SPACING_CLASSES,
  ALL_HEADER_LETTER_SPACING_CLASSES,
  ALL_COLOR_BLIND_MODE_CLASSES,
} from '../config/theme.config';

function applyThemeClass(settings: AccessibilitySettings): void {
  const root = document.documentElement;

  if (settings.theme === 'dark') {
    root.classList.add('dark');
    root.classList.remove('light', 'high-contrast');
  } else if (settings.theme === 'high-contrast') {
    root.classList.remove('dark', 'light');
    root.classList.add('high-contrast');
  } else if (settings.theme === 'system') {
    // Detect system preference
    const systemPrefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    if (systemPrefersDark) {
      root.classList.add('dark');
      root.classList.remove('light');
    } else {
      root.classList.add('light');
      root.classList.remove('dark');
    }
    root.classList.remove('high-contrast');
  } else {
    // Light theme
    root.classList.add('light');
    root.classList.remove('dark', 'high-contrast');
  }
  // Also support highContrast boolean setting for backwards compatibility
  if (settings.highContrast && settings.theme !== 'high-contrast') {
    root.classList.add('high-contrast');
  }
}

// Applies every settings class unconditionally. There used to be a
// settings-hash cache that skipped this body when settings were unchanged;
// it made any externally-stripped class permanent (the theme class grew a
// re-assert carve-out for exactly that, 2026-07-06, and every other class
// kept the exposure). Every operation below is an idempotent classList /
// setProperty write and the lazy CSS loads are singleton-guarded, so the
// cache bought nothing worth that failure mode.
export function applyThemeClasses(settings: AccessibilitySettings): void {
  const root = document.documentElement;

  // Dyslexia Font
  root.classList.toggle('dyslexia-font', settings.dyslexiaFont);
  if (settings.dyslexiaFont) {
    root.setAttribute('data-dyslexia-mode', 'true');
  } else {
    root.removeAttribute('data-dyslexia-mode');
  }

  // Font Size
  root.classList.remove(...ALL_FONT_SIZE_CLASSES);
  root.classList.add(FONT_SIZE_CLASSES[settings.fontSize]);
  root.style.setProperty('--font-scale', FONT_SCALE_VALUES[settings.fontSize]);

  // Line Spacing
  root.classList.remove(...ALL_LINE_SPACING_CLASSES);
  root.classList.add(LINE_SPACING_CLASSES[settings.lineSpacing]);

  // Theme
  // Explicitly handle light/dark/high-contrast/system themes to ensure proper class management
  applyThemeClass(settings);

  // Reduce Motion
  root.classList.toggle('reduce-motion', settings.reduceMotion);

  // Reading Guide
  root.classList.toggle('reading-guide', settings.readingGuide);

  // Focus Mode
  root.classList.toggle('focus-mode', settings.focusMode);

  // Letter Spacing (legacy)
  root.classList.remove(...ALL_LETTER_SPACING_CLASSES);
  root.classList.add(LETTER_SPACING_CLASSES[settings.letterSpacing]);

  // Letter Spacing - Body (only emit when non-default; otherwise it shadows the global Letter Spacing control on p/li/td)
  root.classList.remove(...ALL_BODY_LETTER_SPACING_CLASSES);
  if (settings.letterSpacingBody !== 'normal') {
    root.classList.add(BODY_LETTER_SPACING_CLASSES[settings.letterSpacingBody]);
  }

  // Letter Spacing - Headers (only emit when non-default; otherwise it shadows the global control on h1-h6)
  root.classList.remove(...ALL_HEADER_LETTER_SPACING_CLASSES);
  if (settings.letterSpacingHeaders !== 'normal') {
    root.classList.add(HEADER_LETTER_SPACING_CLASSES[settings.letterSpacingHeaders]);
  }

  // Font Weight
  root.style.setProperty('--font-weight-base', settings.fontWeight.toString());

  // Quiet Mode (mutually exclusive)
  if (settings.quietMode) {
    root.classList.add('quiet-mode');
    root.classList.remove('quiet-mode-lite');
  } else {
    root.classList.remove('quiet-mode');
    if (settings.quietModeLite) {
      root.classList.add('quiet-mode-lite');
    } else {
      root.classList.remove('quiet-mode-lite');
    }
  }

  // Reduced Cognitive Load
  root.classList.toggle('reduced-cognitive-load', settings.reducedCognitiveLoad);

  // Load neuro-inclusive CSS when any neuro-inclusive feature is enabled
  // This ensures all the CSS classes have their corresponding styles
  const needsNeuroInclusiveCSS =
    settings.reducedCognitiveLoad ||
    settings.readingGuide ||
    settings.focusMode ||
    settings.quietMode ||
    settings.quietModeLite ||
    settings.predictableNavigation ||
    settings.enhancedFocus ||
    settings.dyslexiaFont ||
    settings.plainLanguage ||
    settings.noFOMO ||
    settings.anonymousMode ||
    settings.blinders ||
    settings.bionicReading ||
    settings.mutedColors ||
    settings.letterSpacing !== 'normal' ||
    settings.letterSpacingBody !== 'normal' ||
    settings.letterSpacingHeaders !== 'normal' ||
    settings.contentDensity !== 'comfortable' ||
    settings.hideDecorativeImages ||
    !settings.showImages ||
    settings.lineFocusGuide ||
    settings.simplifiedView ||
    settings.removeTimePressure;

  if (needsNeuroInclusiveCSS) {
    loadTheme('neuro-inclusive').catch((e) => Sentry.captureException(e instanceof Error ? e : new Error(String(e))));
  }

  // Predictable Navigation
  root.classList.toggle('predictable-navigation', settings.predictableNavigation);

  // Enhanced Focus
  if (settings.enhancedFocus) {
    if (settings.enhancedFocusIndicatorOnly) {
      root.classList.add('enhanced-focus-indicator-only');
      root.classList.remove('enhanced-focus');
    } else {
      root.classList.add('enhanced-focus');
      root.classList.remove('enhanced-focus-indicator-only');
      root.style.setProperty(
        '--enhanced-focus-opacity',
        `${settings.enhancedFocusOpacity / 100}`
      );
    }
  } else {
    root.classList.remove('enhanced-focus', 'enhanced-focus-indicator-only');
  }

  // Color Blind Mode
  root.classList.remove(...ALL_COLOR_BLIND_MODE_CLASSES);
  const colorBlindClass = COLOR_BLIND_MODE_CLASSES[settings.colorBlindMode];
  if (colorBlindClass) {
    root.classList.add(colorBlindClass);
  }
  // Lazy load colorblind theme if needed
  if (settings.colorBlindMode !== 'none') {
    loadTheme('colorblind').catch((e) => Sentry.captureException(e instanceof Error ? e : new Error(String(e))));
  }

  // Language: owned by I18nContext (document.documentElement.lang), not set here.

  // Plain Language (simplify jargon)
  root.classList.toggle('plain-language', settings.plainLanguage);

  // No FOMO (hide urgency elements like "X people viewing")
  root.classList.toggle('no-fomo', settings.noFOMO);

  // Anonymous Mode (private browsing visual indicator)
  root.classList.toggle('anonymous-mode', settings.anonymousMode);

  // Blinders (narrow focus area)
  root.classList.toggle('blinders', settings.blinders);

  // Bionic Reading (bold word beginnings)
  root.classList.toggle('bionic-reading', settings.bionicReading);

  // Muted Colors (calm color palette)

  // Apply additional accessibility settings
  applyAdditionalSettings(settings);
  root.classList.toggle('muted-colors', settings.mutedColors);

  // Apply additional settings
  root.classList.remove('content-density-compact', 'content-density-comfortable', 'content-density-spacious');
  if (settings.contentDensity) root.classList.add('content-density-' + settings.contentDensity);
  root.classList.toggle('hide-decorative-images', settings.hideDecorativeImages);
  root.classList.toggle('hide-all-images', !settings.showImages);
  root.classList.toggle('line-focus-guide', settings.lineFocusGuide);
  root.classList.toggle('simplified-view', settings.simplifiedView);
  root.classList.toggle('remove-time-pressure', settings.removeTimePressure);
}

export function removeThemeClasses(): void {
  const root = document.documentElement;

  // Remove all accessibility-related classes
  root.classList.remove(
    'dyslexia-font',
    'dark',
    'high-contrast',
    'reduce-motion',
    'reading-guide',
    'focus-mode',
    'quiet-mode',
    'quiet-mode-lite',
    'reduced-cognitive-load',
    'predictable-navigation',
    'enhanced-focus',
    'enhanced-focus-indicator-only',
    'plain-language',
    'no-fomo',
    'anonymous-mode',
    'blinders',
    'bionic-reading',
    'muted-colors',
    ...ALL_FONT_SIZE_CLASSES,
    ...ALL_LINE_SPACING_CLASSES,
    ...ALL_LETTER_SPACING_CLASSES,
    ...ALL_BODY_LETTER_SPACING_CLASSES,
    ...ALL_HEADER_LETTER_SPACING_CLASSES,
    ...ALL_COLOR_BLIND_MODE_CLASSES
  );

  // Remove data attributes
  root.removeAttribute('data-dyslexia-mode');

  // Remove custom properties
  root.style.removeProperty('--font-scale');
  root.style.removeProperty('--font-weight-base');
  root.style.removeProperty('--enhanced-focus-opacity');
}

export function validateAndMergeSettings(
  saved: Partial<AccessibilitySettings> | null | undefined,
  defaults: AccessibilitySettings
): AccessibilitySettings {
  // Handle null/undefined/non-object saved settings
  if (!saved || typeof saved !== 'object') {
    return { ...defaults };
  }

  // Safely merge, filtering out any properties that are undefined or null
  const filtered: Partial<AccessibilitySettings> = {};
  for (const key of Object.keys(saved) as (keyof AccessibilitySettings)[]) {
    const value = saved[key];
    if (value !== undefined && value !== null) {
      (filtered as Record<string, unknown>)[key] = value;
    }
  }

  const merged = {
    ...defaults,
    ...filtered,
  };

  // Validate every enum-typed field. Stale localStorage values
  // (e.g. an old `fontSize: 'x-large'` from before the enum was
  // tightened) would otherwise land on <html> as literal class
  // names like `font-size-undefined`. Fall back to default per-field.
  if (!isTheme(merged.theme)) {
    merged.theme = defaults.theme;
  }
  if (!isFontSize(merged.fontSize)) {
    merged.fontSize = defaults.fontSize;
  }
  if (!isLineSpacing(merged.lineSpacing)) {
    merged.lineSpacing = defaults.lineSpacing;
  }
  if (!isLetterSpacing(merged.letterSpacing)) {
    merged.letterSpacing = defaults.letterSpacing;
  }
  if (!isLetterSpacing(merged.letterSpacingBody)) {
    merged.letterSpacingBody = defaults.letterSpacingBody;
  }
  if (!isLetterSpacing(merged.letterSpacingHeaders)) {
    merged.letterSpacingHeaders = defaults.letterSpacingHeaders;
  }
  if (!isColorBlindMode(merged.colorBlindMode)) {
    merged.colorBlindMode = defaults.colorBlindMode;
  }
  if (!isFontWeight(merged.fontWeight)) {
    merged.fontWeight = defaults.fontWeight;
  }
  if (!isEnhancedFocusOpacity(merged.enhancedFocusOpacity)) {
    merged.enhancedFocusOpacity = defaults.enhancedFocusOpacity;
  }

  return merged;
}

// Additional accessibility settings (added for completeness)
export function applyAdditionalSettings(settings: AccessibilitySettings): void {
  const root = document.documentElement;
  
  // Content Density
  root.classList.remove('content-density-compact', 'content-density-comfortable', 'content-density-spacious');
  if (settings.contentDensity) {
    root.classList.add(`content-density-${settings.contentDensity}`);
  }

  // Hide Decorative Images
  root.classList.toggle('hide-decorative-images', settings.hideDecorativeImages);

  // Hide All Images (inverse of showImages)
  root.classList.toggle('hide-all-images', !settings.showImages);

  // Line Focus Guide
  root.classList.toggle('line-focus-guide', settings.lineFocusGuide);

  // Simplified View
  root.classList.toggle('simplified-view', settings.simplifiedView);

  // Remove Time Pressure
  root.classList.toggle('remove-time-pressure', settings.removeTimePressure);
}

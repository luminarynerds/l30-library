/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Accessibility Feature - Main Entry Point
 *
 * This module provides a centralized, accessible system for customizing
 * the user experience. It includes WCAG 2.2/3.0 compliant features and
 * neuro-inclusive design options.
 *
 * @example
 * ```tsx
 * import { AccessibilityProvider, useAccessibility } from '@/features/accessibility';
 *
 * function App() {
 *   return (
 *     <AccessibilityProvider>
 *       <MyApp />
 *     </AccessibilityProvider>
 *   );
 * }
 *
 * function MyComponent() {
 *   const { settings, updateSetting } = useAccessibility();
 *   // Use settings...
 * }
 * ```
 */

// ============================================================================
// Main Exports
// ============================================================================

/**
 * Legacy provider component (deprecated - use UnifiedAccessibilityProvider)
 */
export { AccessibilityProvider } from './context/AccessibilityContext';

/**
 * Unified provider component - consolidates both accessibility systems
 */
export {
  UnifiedAccessibilityProvider,
  UnifiedAccessibilityContext,
} from './context/UnifiedAccessibilityContext';
export type { UnifiedAccessibilityContextType } from './context/UnifiedAccessibilityContext';

/**
 * Legacy hook for accessing settings (deprecated - use useUnifiedAccessibility)
 */
export { useAccessibility } from './hooks/useAccessibility';

/**
 * Unified hook for accessing settings - works with both modern and legacy presets
 */
export {
  useUnifiedAccessibility,
  useNeurodivergentSettings,
} from './hooks/useUnifiedAccessibility';
export type { UseUnifiedAccessibilityReturn } from './hooks/useUnifiedAccessibility';

// ============================================================================
// Type Exports
// ============================================================================

export type {
  // Main interfaces
  AccessibilitySettings,
  AccessibilityContextType,
  UpdateSetting,
  PartialSettings,

  // Individual setting types
  Language,
  FontSize,
  LineSpacing,
  LetterSpacing,
  FontWeight,
  Theme,
  ColorBlindMode,
  EnhancedFocusOpacity,
  AutoThemeSchedule,

  // Type utilities
  SettingKey,
  SettingValue,
  ValidationResult,
} from './types/accessibility.types';

// ============================================================================
// Configuration Exports (for advanced usage)
// ============================================================================

/**
 * Default settings - useful for comparisons or resets
 */
export { DEFAULT_SETTINGS } from './config/defaults.config';

/**
 * Theme class mappings - useful for custom CSS implementations
 */
export {
  FONT_SIZE_CLASSES,
  FONT_SCALE_VALUES,
  LINE_SPACING_CLASSES,
  LETTER_SPACING_CLASSES,
  BODY_LETTER_SPACING_CLASSES,
  HEADER_LETTER_SPACING_CLASSES,
  COLOR_BLIND_MODE_CLASSES,
} from './config/theme.config';

// ============================================================================
// Constant Exports (for validation and UI)
// ============================================================================

export {
  LANGUAGES,
  FONT_SIZES,
  LINE_SPACINGS,
  LETTER_SPACINGS,
  FONT_WEIGHTS,
  THEMES,
  COLOR_BLIND_MODES,
  ENHANCED_FOCUS_OPACITIES,
  AUTO_THEME_SCHEDULES,
} from './types/accessibility.types';

// ============================================================================
// Type Guard Exports (for runtime validation)
// ============================================================================

export {
  isLanguage,
  isFontSize,
  isLineSpacing,
  isLetterSpacing,
  isFontWeight,
  isTheme,
  isColorBlindMode,
  isEnhancedFocusOpacity,
  isSettingKey,
  isAutoThemeSchedule,
} from './types/accessibility.types';

// ============================================================================
// Utility Exports (for advanced usage)
// ============================================================================

/**
 * Persistence utilities
 */
export {
  loadSettingsFromStorage,
  clearSettingsFromStorage,
  cleanupLegacyStorage,
  hasLegacySettings,
  LEGACY_KEYS,
} from './hooks/useSettingsPersistence';

/**
 * CSS application utilities
 */
export {
  applyThemeClasses,
  removeThemeClasses,
  validateAndMergeSettings,
} from './utils/cssApplicator';

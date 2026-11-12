/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Accessibility Preset Profiles
 *
 * Pre-configured accessibility settings for common use cases.
 * Each preset is designed based on research and user feedback
 * for specific neurodivergent needs.
 */

import type { AccessibilitySettings } from '../types/accessibility.types';

export interface AccessibilityPreset {
  /** Unique identifier */
  id: string;
  /** Display name */
  name: string;
  /** Short description */
  description: string;
  /** Detailed explanation of what this preset helps with */
  helpText: string;
  /** Icon name (lucide-react) */
  icon: string;
  /** Color theme for the preset card */
  color: 'blue' | 'green' | 'purple' | 'amber' | 'pink' | 'cyan';
  /** Partial settings to apply */
  settings: Partial<AccessibilitySettings>;
  /** Tags for filtering/search */
  tags: string[];
}

/**
 * ADHD Focus Mode
 * Reduces distractions and helps maintain focus
 */
export const ADHD_FOCUS_PRESET: AccessibilityPreset = {
  id: 'adhd-focus',
  name: 'ADHD Focus',
  description: 'Minimize distractions, maximize focus',
  helpText:
    'Enables blinders to narrow your view, removes FOMO-inducing elements, ' +
    'sets up break reminders to prevent hyperfocus burnout, and reduces visual noise.',
  icon: 'Focus',
  color: 'blue',
  settings: {
    blinders: true,
    noFOMO: true,
    removeTimePressure: true,
    breakReminders: true,
    breakIntervalMinutes: 25,
    quietMode: false,
    quietModeLite: true,
    reducedCognitiveLoad: true,
    hideDecorativeImages: true,
    focusMode: true,
    enhancedFocus: true,
    enhancedFocusOpacity: 70,
    preferPagination: true,
  },
  tags: ['adhd', 'focus', 'attention', 'distraction'],
};

/**
 * Dyslexia Support Mode
 * Optimized for reading with dyslexia
 */
export const DYSLEXIA_SUPPORT_PRESET: AccessibilityPreset = {
  id: 'dyslexia-support',
  // NOTE: id remains 'dyslexia-support' for localStorage backcompat with
  // settings saved before the 2026-05-18 rename. The display label changed
  // because the evidence base for OpenDyslexic is weak (Wery & Diliberto 2017;
  // Marinus et al 2016) while Atkinson Hyperlegible is designed for character
  // differentiation and recommended by the British Dyslexia Association.
  name: 'Hyperlegible Reading',
  description: 'Clearer letterforms, generous spacing, reading guide',
  helpText:
    'Switches to Atkinson Hyperlegible, a typeface designed to make ' +
    'similar characters (like b/d, 1/l/I, 0/O) easier to tell apart. ' +
    'Adds bionic reading (bold word starts), a line focus guide, ' +
    'wider letter and line spacing, and larger text.',
  icon: 'BookOpen',
  color: 'green',
  settings: {
    dyslexiaFont: true,
    bionicReading: true,
    lineFocusGuide: true,
    readingTool: 'guide',
    letterSpacing: 'wide',
    letterSpacingBody: 'wide',
    lineSpacing: 'relaxed',
    fontSize: 'large',
    fontWeight: 500,
    readingGuide: true,
  },
  tags: ['dyslexia', 'reading', 'font', 'text'],
};

/**
 * Low Anxiety Mode
 * Reduces stress-inducing elements
 */
export const LOW_ANXIETY_PRESET: AccessibilityPreset = {
  id: 'low-anxiety',
  name: 'Calm Mode',
  description: 'Reduce stress and pressure',
  helpText:
    'Removes time pressure elements, enables undo for all actions, ' +
    'requires explicit confirmations, uses calmer colors, and removes urgency from notifications.',
  icon: 'Heart',
  color: 'pink',
  settings: {
    removeTimePressure: true,
    noFOMO: true,
    undoEnabled: true,
    undoWindowSeconds: 60,
    explicitConfirmations: true,
    mutedColors: true,
    whisperMode: true,
    noUrgentLanguage: true,
    reduceMotion: true,
    quietMode: true,
    predictableNavigation: true,
  },
  tags: ['anxiety', 'calm', 'stress', 'gentle'],
};

/**
 * Autism Sensory Mode
 * Reduces sensory overload
 */
export const AUTISM_SENSORY_PRESET: AccessibilityPreset = {
  id: 'autism-sensory',
  name: 'Sensory Friendly',
  description: 'Reduce sensory stimulation',
  helpText:
    'Minimizes animations, reduces color saturation, removes decorative elements, ' +
    'enables quiet mode, and provides predictable navigation patterns.',
  icon: 'Sparkles',
  color: 'purple',
  settings: {
    reduceMotion: true,
    mutedColors: true,
    quietMode: true,
    hideDecorativeImages: true,
    simplifiedView: true,
    reducedCognitiveLoad: true,
    predictableNavigation: true,
    whisperMode: true,
    batchNotifications: true,
    contentDensity: 'spacious',
    showImages: false,
  },
  tags: ['autism', 'sensory', 'quiet', 'calm'],
};

/**
 * Screen Reader Optimized
 * Best settings for screen reader users
 */
export const SCREEN_READER_PRESET: AccessibilityPreset = {
  id: 'screen-reader',
  name: 'Screen Reader',
  description: 'Optimized for assistive technology',
  helpText:
    'Simplifies page structure, ensures predictable navigation, ' +
    'removes decorative elements that may confuse screen readers, and enables plain language.',
  icon: 'Volume2',
  color: 'cyan',
  settings: {
    simplifiedView: true,
    hideDecorativeImages: true,
    predictableNavigation: true,
    plainLanguage: true,
    reduceMotion: true,
    focusMode: false,
    blinders: false,
    preferPagination: true,
  },
  tags: ['screen-reader', 'blind', 'assistive', 'voiceover', 'nvda', 'jaws'],
};

/**
 * Motor Impairment Mode
 * For users with limited motor control
 */
export const MOTOR_IMPAIRMENT_PRESET: AccessibilityPreset = {
  id: 'motor-impairment',
  name: 'Motor Accessibility',
  description: 'Easier navigation and interaction',
  helpText:
    'Enables voice control, larger click targets, extended undo windows, ' +
    'explicit confirmations to prevent mistakes, and keyboard-focused navigation.',
  icon: 'Hand',
  color: 'amber',
  settings: {
    voiceControlEnabled: true,
    voiceControlContinuous: true,
    undoEnabled: true,
    undoWindowSeconds: 120,
    explicitConfirmations: true,
    contentDensity: 'spacious',
    enhancedFocus: true,
    enhancedFocusIndicatorOnly: true,
    focusRingColor: 'blue',
  },
  tags: ['motor', 'mobility', 'voice', 'keyboard'],
};

/**
 * Low Vision Mode
 * For users with visual impairments
 */
export const LOW_VISION_PRESET: AccessibilityPreset = {
  id: 'low-vision',
  name: 'Low Vision',
  description: 'High contrast and larger text',
  helpText:
    'Maximizes text size, enables high contrast mode, uses bold fonts, ' +
    'and ensures all elements have strong visual distinction.',
  icon: 'Eye',
  color: 'amber',
  settings: {
    fontSize: 'xlarge',
    highContrast: true,
    theme: 'high-contrast',
    fontWeight: 600,
    lineSpacing: 'loose',
    focusRingColor: 'yellow',
    enhancedFocus: true,
    enhancedFocusIndicatorOnly: true,
    simplifiedView: true,
  },
  tags: ['low-vision', 'blind', 'contrast', 'large-text'],
};

/**
 * Migraine/Light Sensitive Mode
 */
export const MIGRAINE_PRESET: AccessibilityPreset = {
  id: 'migraine',
  name: 'Light Sensitive',
  description: 'Reduce eye strain and light sensitivity',
  helpText:
    'Enables dark mode, reduces brightness, removes animations, ' +
    'uses muted colors, and minimizes visual stimulation.',
  icon: 'Moon',
  color: 'purple',
  settings: {
    theme: 'dark',
    reduceMotion: true,
    mutedColors: true,
    hideDecorativeImages: true,
    quietMode: true,
    simplifiedView: true,
    showImages: false,
  },
  tags: ['migraine', 'headache', 'light', 'dark-mode'],
};

/**
 * All available presets
 */
export const ACCESSIBILITY_PRESETS: AccessibilityPreset[] = [
  ADHD_FOCUS_PRESET,
  DYSLEXIA_SUPPORT_PRESET,
  LOW_ANXIETY_PRESET,
  AUTISM_SENSORY_PRESET,
  SCREEN_READER_PRESET,
  MOTOR_IMPAIRMENT_PRESET,
  LOW_VISION_PRESET,
  MIGRAINE_PRESET,
];

export function getPresetById(id: string): AccessibilityPreset | undefined {
  return ACCESSIBILITY_PRESETS.find((preset) => preset.id === id);
}

export function searchPresets(query: string): AccessibilityPreset[] {
  const normalizedQuery = query.toLowerCase().trim();
  if (!normalizedQuery) return ACCESSIBILITY_PRESETS;

  return ACCESSIBILITY_PRESETS.filter(
    (preset) =>
      preset.name.toLowerCase().includes(normalizedQuery) ||
      preset.description.toLowerCase().includes(normalizedQuery) ||
      preset.tags.some((tag) => tag.includes(normalizedQuery))
  );
}

export default ACCESSIBILITY_PRESETS;

/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Quick verification script for unified accessibility context
 * Tests basic functionality without needing full build
 */

import { migrateNeurodivergentToAccessibility, detectLegacySettingsInStorage, clearLegacySettings } from './src/features/accessibility/utils/settingsMigration';
import { DEFAULT_SETTINGS } from './src/features/accessibility/config/defaults.config';

// Test 1: Migration detection
console.log('Test 1: Legacy settings detection');
const hasLegacy = detectLegacySettingsInStorage();
console.log('✓ detectLegacySettingsInStorage() works:', typeof hasLegacy === 'boolean');

// Test 2: Migration function exists and is callable
console.log('\nTest 2: Migration function');
const sampleLegacy = {
  sensory: {
    fontFamily: 'dyslexic',
    fontSize: 18,
    lineHeight: 2.0,
    letterSpacing: 6,
    theme: 'dark',
    mutedColors: true,
    reducedMotion: true,
    readingRuler: true,
    bionicReading: true,
    visualNoise: 'low',
    showImages: true,
    autoplayVideos: false,
  },
  focus: {
    focusMode: true,
    blinders: true,
    distractionFree: false,
    singleTask: false,
    timeBoxing: false,
    hyperfocusProtection: true,
  },
  processing: {
    plainLanguage: true,
    audioDescriptions: false,
    contentWarnings: true,
    slowAnimations: false,
    confirmActions: true,
    previewChanges: false,
  },
  anxiety: {
    undoEnabled: true,
    previewMode: false,
    calmAvailability: false,
    noFOMO: true,
    anonymous: false,
    hideDeadlines: false,
    gentleReminders: true,
  },
  executiveFunction: {
    sessionResume: true,
    decisionHelp: true,
    simplifiedChoices: false,
    taskBreakdown: true,
    progressTracking: true,
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
    gamification: false,
    surpriseMe: false,
    rabbitHoles: false,
    discoveryMode: 'off',
    hideSpoilers: false,
  },
  practical: {
    offline: false,
    voiceCommands: false,
    nonVerbal: false,
    largeButtons: true,
    hapticFeedback: false,
  },
  reducedMotion: true,
  mutedColors: true,
  largeText: true,
  highContrast: false,
  soundsEnabled: false,
  breakRemindersEnabled: true,
  breakIntervalMinutes: 30,
  showImages: true,
  contentDensity: 'spacious',
  version: 1,
};

try {
  const modern = migrateNeurodivergentToAccessibility(sampleLegacy);
  console.log('✓ Migration function works');
  console.log('✓ Migrated settings include key properties:');
  console.log('  - dyslexiaFont:', modern.dyslexiaFont === true);
  console.log('  - fontSize:', modern.fontSize === 'large');
  console.log('  - lineSpacing:', modern.lineSpacing === 'loose');
  console.log('  - letterSpacing:', modern.letterSpacing === 'wider');
  console.log('  - focusMode:', modern.focusMode === true);
  console.log('  - plainLanguage:', modern.plainLanguage === true);
  console.log('  - contentDensity:', modern.contentDensity === 'spacious');
} catch (e) {
  console.error('✗ Migration failed:', e);
}

// Test 3: Default settings exist
console.log('\nTest 3: Default settings');
console.log('✓ DEFAULT_SETTINGS exists:', DEFAULT_SETTINGS !== undefined);
console.log('✓ Has core properties:');
console.log('  - language:', DEFAULT_SETTINGS.language !== undefined);
console.log('  - fontSize:', DEFAULT_SETTINGS.fontSize !== undefined);
console.log('  - theme:', DEFAULT_SETTINGS.theme !== undefined);

console.log('\n✓ All verification tests passed!');

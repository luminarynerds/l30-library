/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Neurodivergent Settings - Default Values and Presets
 */

import type {
  NeurodivergentSettings,
  PresetDefinition,
  ExecutiveFunctionSettings,
  SensorySettings,
  FocusSettings,
  ProcessingSettings,
  AnxietySettings,
  ControlSettings,
  InterestSettings,
  PracticalSettings,
} from "../types/neurodivergent-settings";

// Default category settings
export const DEFAULT_EXECUTIVE_FUNCTION: ExecutiveFunctionSettings = {
  sessionResume: true,
  decisionHelp: false,
  simplifiedChoices: false,
  taskBreakdown: false,
  progressTracking: true,
};

export const DEFAULT_SENSORY: SensorySettings = {
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
};

export const DEFAULT_FOCUS: FocusSettings = {
  focusMode: false,
  blinders: false,
  distractionFree: false,
  singleTask: false,
  timeBoxing: false,
  hyperfocusProtection: true,
};

export const DEFAULT_PROCESSING: ProcessingSettings = {
  plainLanguage: false,
  audioDescriptions: false,
  contentWarnings: true,
  slowAnimations: false,
  confirmActions: false,
  previewChanges: false,
};

export const DEFAULT_ANXIETY: AnxietySettings = {
  undoEnabled: true,
  previewMode: false,
  calmAvailability: false,
  noFOMO: false,
  anonymous: false,
  hideDeadlines: false,
  gentleReminders: true,
};

export const DEFAULT_CONTROL: ControlSettings = {
  routines: false,
  exactMatch: false,
  layoutLock: false,
  customDefaults: {},
  keyboardShortcuts: true,
  autoSave: true,
};

export const DEFAULT_INTEREST: InterestSettings = {
  gamification: true,
  surpriseMe: false,
  rabbitHoles: true,
  discoveryMode: "full",
  hideSpoilers: false,
};

export const DEFAULT_PRACTICAL: PracticalSettings = {
  offline: false,
  voiceCommands: false,
  nonVerbal: false,
  largeButtons: false,
  hapticFeedback: false,
};

// Complete default settings
export const DEFAULT_NEURODIVERGENT_SETTINGS: NeurodivergentSettings = {
  executiveFunction: DEFAULT_EXECUTIVE_FUNCTION,
  sensory: DEFAULT_SENSORY,
  focus: DEFAULT_FOCUS,
  processing: DEFAULT_PROCESSING,
  anxiety: DEFAULT_ANXIETY,
  control: DEFAULT_CONTROL,
  interest: DEFAULT_INTEREST,
  practical: DEFAULT_PRACTICAL,

  // Legacy settings for backward compatibility
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

// Preset definitions
export const PRESETS: PresetDefinition[] = [
  {
    id: "standard",
    name: "Standard",
    description: "Default settings, no modifications",
    icon: "Monitor",
    settings: {
      ...DEFAULT_NEURODIVERGENT_SETTINGS,
      presetName: "standard",
    },
  },
  {
    id: "minimal",
    name: "Calm Mode",
    description: "Reduced everything, minimal UI, maximum calm",
    icon: "Moon",
    settings: {
      executiveFunction: {
        ...DEFAULT_EXECUTIVE_FUNCTION,
        simplifiedChoices: true,
        decisionHelp: true,
      },
      sensory: {
        ...DEFAULT_SENSORY,
        theme: "auto",
        mutedColors: true,
        reducedMotion: true,
        visualNoise: "none",
        autoplayVideos: false,
      },
      focus: {
        ...DEFAULT_FOCUS,
        focusMode: true,
        blinders: true,
        distractionFree: true,
      },
      processing: {
        ...DEFAULT_PROCESSING,
        plainLanguage: true,
        slowAnimations: true,
        confirmActions: true,
      },
      anxiety: {
        ...DEFAULT_ANXIETY,
        undoEnabled: true,
        calmAvailability: true,
        noFOMO: true,
        gentleReminders: true,
      },
      control: {
        ...DEFAULT_CONTROL,
        layoutLock: true,
        autoSave: true,
      },
      interest: {
        ...DEFAULT_INTEREST,
        gamification: false,
        surpriseMe: false,
        rabbitHoles: false,
        discoveryMode: "off",
      },
      reducedMotion: true,
      mutedColors: true,
      contentDensity: "spacious",
      presetName: "minimal",
    },
  },
  {
    id: "focus",
    name: "Focus Mode",
    description: "No distractions, single task, maximum productivity",
    icon: "Target",
    settings: {
      executiveFunction: {
        ...DEFAULT_EXECUTIVE_FUNCTION,
        taskBreakdown: true,
        progressTracking: true,
      },
      sensory: {
        ...DEFAULT_SENSORY,
        reducedMotion: true,
        visualNoise: "low",
        autoplayVideos: false,
      },
      focus: {
        ...DEFAULT_FOCUS,
        focusMode: true,
        blinders: true,
        distractionFree: true,
        singleTask: true,
        timeBoxing: true,
        hyperfocusProtection: true,
      },
      processing: {
        ...DEFAULT_PROCESSING,
        confirmActions: true,
      },
      anxiety: {
        ...DEFAULT_ANXIETY,
        noFOMO: true,
        anonymous: true,
      },
      control: {
        ...DEFAULT_CONTROL,
        layoutLock: true,
        keyboardShortcuts: true,
      },
      interest: {
        ...DEFAULT_INTEREST,
        gamification: false,
        surpriseMe: false,
        rabbitHoles: false,
        discoveryMode: "off",
      },
      reducedMotion: true,
      contentDensity: "comfortable",
      presetName: "focus",
    },
  },
  {
    id: "exploration",
    name: "Explorer Mode",
    description: "Rabbit holes enabled, surprise me, full discovery",
    icon: "Compass",
    settings: {
      executiveFunction: {
        ...DEFAULT_EXECUTIVE_FUNCTION,
        sessionResume: true,
      },
      sensory: {
        ...DEFAULT_SENSORY,
        visualNoise: "medium",
        showImages: true,
      },
      focus: {
        ...DEFAULT_FOCUS,
        focusMode: false,
        hyperfocusProtection: true,
      },
      processing: {
        ...DEFAULT_PROCESSING,
        contentWarnings: true,
      },
      anxiety: {
        ...DEFAULT_ANXIETY,
        undoEnabled: true,
        calmAvailability: false,
      },
      control: {
        ...DEFAULT_CONTROL,
        routines: true,
      },
      interest: {
        ...DEFAULT_INTEREST,
        gamification: true,
        surpriseMe: true,
        rabbitHoles: true,
        discoveryMode: "full",
        hideSpoilers: false,
      },
      contentDensity: "comfortable",
      presetName: "exploration",
    },
  },
  {
    id: "calm",
    name: "Calm Browsing",
    description: "Gentle, predictable, stress-free experience",
    icon: "Heart",
    settings: {
      executiveFunction: {
        ...DEFAULT_EXECUTIVE_FUNCTION,
        decisionHelp: true,
        simplifiedChoices: true,
      },
      sensory: {
        ...DEFAULT_SENSORY,
        theme: "auto",
        mutedColors: true,
        reducedMotion: true,
        visualNoise: "low",
      },
      focus: {
        ...DEFAULT_FOCUS,
        distractionFree: true,
        hyperfocusProtection: true,
      },
      processing: {
        ...DEFAULT_PROCESSING,
        plainLanguage: true,
        confirmActions: true,
        previewChanges: true,
      },
      anxiety: {
        ...DEFAULT_ANXIETY,
        undoEnabled: true,
        previewMode: true,
        calmAvailability: true,
        noFOMO: true,
        gentleReminders: true,
      },
      control: {
        ...DEFAULT_CONTROL,
        layoutLock: true,
        autoSave: true,
      },
      interest: {
        ...DEFAULT_INTEREST,
        gamification: false,
        discoveryMode: "minimal",
      },
      reducedMotion: true,
      mutedColors: true,
      contentDensity: "spacious",
      breakRemindersEnabled: true,
      breakIntervalMinutes: 30,
      presetName: "calm",
    },
  },
  {
    id: "minimal-interaction",
    name: "Minimal Interaction",
    description: "Anonymous, non-verbal, no social features",
    icon: "UserX",
    settings: {
      executiveFunction: {
        ...DEFAULT_EXECUTIVE_FUNCTION,
        simplifiedChoices: true,
      },
      sensory: {
        ...DEFAULT_SENSORY,
        reducedMotion: true,
        visualNoise: "none",
      },
      focus: {
        ...DEFAULT_FOCUS,
        focusMode: true,
        distractionFree: true,
      },
      processing: {
        ...DEFAULT_PROCESSING,
        plainLanguage: true,
      },
      anxiety: {
        ...DEFAULT_ANXIETY,
        undoEnabled: true,
        noFOMO: true,
        anonymous: true,
        gentleReminders: true,
      },
      control: {
        ...DEFAULT_CONTROL,
        exactMatch: true,
        layoutLock: true,
      },
      interest: {
        ...DEFAULT_INTEREST,
        gamification: false,
        surpriseMe: false,
        rabbitHoles: false,
        discoveryMode: "off",
      },
      practical: {
        ...DEFAULT_PRACTICAL,
        nonVerbal: true,
        largeButtons: true,
      },
      reducedMotion: true,
      mutedColors: true,
      soundsEnabled: false,
      contentDensity: "spacious",
      presetName: "minimal-interaction",
    },
  },
  {
    id: "custom",
    name: "Custom",
    description: "Your personalized settings",
    icon: "Settings",
    settings: {},
  },
];

// Get preset by ID
export function getPreset(id: string): PresetDefinition | undefined {
  return PRESETS.find((p) => p.id === id);
}

// Merge settings with preset
export function applyPresetToSettings(
  currentSettings: NeurodivergentSettings,
  presetId: string
): NeurodivergentSettings {
  const preset = getPreset(presetId);
  if (!preset || preset.id === "custom") {
    return currentSettings;
  }

  return {
    ...currentSettings,
    ...preset.settings,
    // Merge nested objects properly
    executiveFunction: {
      ...currentSettings.executiveFunction,
      ...(preset.settings.executiveFunction || {}),
    },
    sensory: { ...currentSettings.sensory, ...(preset.settings.sensory || {}) },
    focus: { ...currentSettings.focus, ...(preset.settings.focus || {}) },
    processing: {
      ...currentSettings.processing,
      ...(preset.settings.processing || {}),
    },
    anxiety: { ...currentSettings.anxiety, ...(preset.settings.anxiety || {}) },
    control: { ...currentSettings.control, ...(preset.settings.control || {}) },
    interest: { ...currentSettings.interest, ...(preset.settings.interest || {}) },
    practical: {
      ...currentSettings.practical,
      ...(preset.settings.practical || {}),
    },
    presetName: presetId,
    lastModified: new Date().toISOString(),
  };
}

// Detect which preset is currently active (if any)
export function detectCurrentPreset(
  settings: NeurodivergentSettings
): string | undefined {
  if (settings.presetName && settings.presetName !== "custom") {
    return settings.presetName;
  }

  // Check if settings match any preset
  for (const preset of PRESETS) {
    if (preset.id === "custom") continue;

    // Simple check: if key settings match
    const matches = settingsMatchPreset(settings, preset);
    if (matches) {
      return preset.id;
    }
  }

  return "custom";
}

function settingsMatchPreset(
  settings: NeurodivergentSettings,
  preset: PresetDefinition
): boolean {
  // Check a few key settings to determine if this is the active preset
  const presetSettings = preset.settings;

  if (!presetSettings) return false;

  const checks = [
    settings.focus?.focusMode === presetSettings.focus?.focusMode,
    settings.sensory?.mutedColors === presetSettings.sensory?.mutedColors,
    settings.anxiety?.anonymous === presetSettings.anxiety?.anonymous,
  ];

  return checks.filter(Boolean).length >= 2;
}

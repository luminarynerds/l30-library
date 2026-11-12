/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
// Executive Function Settings
export interface ExecutiveFunctionSettings {
  sessionResume: boolean; // Resume where you left off
  decisionHelp: boolean; // Simplified decision prompts
  simplifiedChoices: boolean; // Reduce number of options
  taskBreakdown: boolean; // Break complex tasks into steps
  progressTracking: boolean; // Show progress indicators
}

// Sensory Settings
export interface SensorySettings {
  // Visual
  fontFamily: "standard" | "dyslexic" | "monospace";
  fontSize: number; // 12-24
  lineHeight: number; // 1.0-2.5
  letterSpacing: number; // 0-10

  // Themes
  theme: "light" | "dark" | "auto" | "sepia" | "high-contrast";
  mutedColors: boolean;
  reducedMotion: boolean;

  // Reading aids
  readingRuler: boolean; // Highlight current line
  bionicReading: boolean; // Bold first part of words
  visualNoise: "none" | "low" | "medium";

  // Content
  showImages: boolean;
  autoplayVideos: boolean;
}

// Focus Settings
export interface FocusSettings {
  focusMode: boolean; // Hide all non-essential UI
  blinders: boolean; // Narrow content column, hide periphery
  distractionFree: boolean; // Hide notifications, sounds
  singleTask: boolean; // One action at a time
  timeBoxing: boolean; // Suggest time limits for browsing
  hyperfocusProtection: boolean; // Break reminders
}

// Processing Settings
export interface ProcessingSettings {
  plainLanguage: boolean; // Simplify text, remove jargon
  audioDescriptions: boolean; // Enable screen reader optimizations
  contentWarnings: boolean; // Show content warnings
  slowAnimations: boolean; // Reduce animation speed
  confirmActions: boolean; // Confirm before major actions
  previewChanges: boolean; // Preview before applying
}

// Anxiety Settings
export interface AnxietySettings {
  undoEnabled: boolean; // Allow undo for most actions
  previewMode: boolean; // Preview results before committing
  calmAvailability: boolean; // "Don't worry, it'll be here when it's available"
  noFOMO: boolean; // Hide "others are viewing" messages
  anonymous: boolean; // Browse privately (hide from history)
  hideDeadlines: boolean; // Don't show due dates prominently
  gentleReminders: boolean; // Soft reminder language
}

// Control Settings
export interface ControlSettings {
  routines: boolean; // Save and reuse common workflows
  exactMatch: boolean; // Exact search by default (not fuzzy)
  layoutLock: boolean; // Prevent layout shifts
  customDefaults: Record<string, unknown>; // User-defined defaults
  keyboardShortcuts: boolean; // Enable keyboard navigation
  autoSave: boolean; // Save state automatically
}

// Interest Settings
export interface InterestSettings {
  gamification: boolean; // Show badges, achievements
  surpriseMe: boolean; // Show random recommendations
  rabbitHoles: boolean; // Show "related to" suggestions
  discoveryMode: "off" | "minimal" | "full";
  hideSpoilers: boolean; // Hide plot summaries
}

// Practical Settings
export interface PracticalSettings {
  offline: boolean; // Enable offline features
  voiceCommands: boolean; // Voice control
  nonVerbal: boolean; // Prefer icons over text
  largeButtons: boolean; // Bigger touch targets
  hapticFeedback: boolean; // Vibration feedback
}

// Complete Neurodivergent Settings
export interface NeurodivergentSettings {
  // Core settings
  executiveFunction: ExecutiveFunctionSettings;
  sensory: SensorySettings;
  focus: FocusSettings;
  processing: ProcessingSettings;
  anxiety: AnxietySettings;
  control: ControlSettings;
  interest: InterestSettings;
  practical: PracticalSettings;

  // Legacy calm settings (for backward compatibility)
  reducedMotion: boolean;
  mutedColors: boolean;
  largeText: boolean;
  highContrast: boolean;
  soundsEnabled: boolean;
  breakRemindersEnabled: boolean;
  breakIntervalMinutes: number;
  showImages: boolean;
  contentDensity: "compact" | "comfortable" | "spacious";

  // Meta
  presetName?: string; // Current preset name
  lastModified?: string; // ISO timestamp
  version: number; // Settings schema version
}

// Preset profiles
export type SettingsPreset =
  | "standard"
  | "minimal"
  | "focus"
  | "exploration"
  | "calm"
  | "minimal-interaction"
  | "custom";

export interface PresetDefinition {
  id: SettingsPreset;
  name: string;
  description: string;
  settings: Partial<NeurodivergentSettings>;
  icon?: string;
}

// Settings context type
export interface NeurodivergentSettingsContextType {
  settings: NeurodivergentSettings;
  updateSettings: (updates: Partial<NeurodivergentSettings>) => void;
  updateCategory: <K extends keyof NeurodivergentSettings>(
    category: K,
    updates: Partial<NeurodivergentSettings[K]>
  ) => void;
  applyPreset: (preset: SettingsPreset) => void;
  resetToDefaults: () => void;
  resetCategory: <K extends keyof NeurodivergentSettings>(category: K) => void;
  exportSettings: () => string;
  importSettings: (json: string) => boolean;
  isSettingsOpen: boolean;
  setIsSettingsOpen: (open: boolean) => void;
  quickSettingsVisible: boolean;
  setQuickSettingsVisible: (visible: boolean) => void;
}

// Quick settings - most commonly toggled
export interface QuickSetting {
  id: string;
  label: string;
  category: keyof NeurodivergentSettings;
  path: string; // Dot notation path to setting
  icon?: string;
}

export const DEFAULT_QUICK_SETTINGS: QuickSetting[] = [
  { id: "focus-mode", label: "Focus Mode", category: "focus", path: "focusMode" },
  { id: "reduced-motion", label: "Reduced Motion", category: "sensory", path: "reducedMotion" },
  { id: "reading-ruler", label: "Reading Ruler", category: "sensory", path: "readingRuler" },
  { id: "plain-language", label: "Plain Language", category: "processing", path: "plainLanguage" },
  { id: "no-fomo", label: "No FOMO", category: "anxiety", path: "noFOMO" },
  { id: "anonymous", label: "Anonymous", category: "anxiety", path: "anonymous" },
];

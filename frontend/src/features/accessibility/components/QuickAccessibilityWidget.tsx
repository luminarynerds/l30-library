/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Quick Accessibility Widget
 *
 * A floating widget that provides quick access to commonly-used
 * accessibility settings without opening the full settings panel.
 */

import { useState, useCallback, useEffect, useRef } from 'react';
import {
  X,
  Sun,
  Moon,
  Eye,
  Type,
  Focus,
  Volume2,
  Sparkles,
  BookOpen,
  Settings,
  ChevronUp,
  Monitor,
  Save,
  Trash2,
  Keyboard,
  SlidersHorizontal,
  Check,
  RotateCcw,
} from 'lucide-react';
import type { AccessibilityProfile, AccessibilitySettings } from '../types/accessibility.types';
import { LOW_ANXIETY_PRESET } from '../config/presets.config';
import { useUnifiedAccessibility } from '../hooks/useUnifiedAccessibility';
import { t } from '@/i18n'
import FocusTrap from 'focus-trap-react'
import { Link } from 'react-router-dom'

interface QuickToggleProps {
  label: string;
  description?: string;
  icon: React.ReactNode;
  isActive: boolean;
  onClick: () => void;
}

function QuickToggle({
  label,
  description,
  icon,
  isActive,
  onClick,
}: QuickToggleProps) {
  return (
    <button
      onClick={onClick}
      className={`
        flex items-center gap-3 w-full p-3 rounded-lg text-left transition-colors
        ${
          isActive
            ? 'bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-700 dark:text-status-warning-300'
            : 'hover:bg-earth-100 dark:bg-earth-700 dark:hover:bg-earth-800 text-lsc-dark/70 dark:text-lsc-cream/70'
        }
      `}
      aria-checked={isActive}
      aria-label={label}
      role="switch"
    >
      <div
        className={`
          p-2 rounded-lg
          ${isActive ? 'bg-status-warning-200 dark:bg-status-warning-800' : 'bg-earth-100 dark:bg-earth-800'}
        `}
      >
        {icon}
      </div>
      <div className="flex-1 min-w-0">
        <div className="font-medium text-sm text-lsc-dark dark:text-lsc-cream">{label}</div>
        {description && (
          <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 truncate" title={description}>
            {description}
          </div>
        )}
      </div>
      <div
        className={`
          w-10 h-6 rounded-full relative transition-colors
          ${isActive ? 'bg-status-warning-500' : 'bg-earth-300 dark:bg-earth-600'}
        `}
        aria-hidden="true"
      >
        <div
          className={`
            absolute top-1 w-4 h-4 bg-lsc-white dark:bg-earth-800 rounded-full shadow transition-transform
            ${isActive ? 'translate-x-5' : 'translate-x-1'}
          `}
        />
      </div>
    </button>
  );
}

const SHORTCUT_LIST = [
  { keys: 'Alt+Shift+T', action: 'Cycle theme' },
  { keys: 'Alt+Shift+C', action: 'Toggle high contrast' },
  { keys: 'Alt+Shift+F', action: 'Toggle focus mode' },
  { keys: 'Alt+Shift+D', action: 'Toggle dyslexia font' },
  { keys: 'Alt+Shift+M', action: 'Toggle reduce motion' },
  { keys: 'Alt+Shift+R', action: 'Toggle reading guide' },
  { keys: 'Alt+Shift+A', action: 'Open/close widget' },
] as const;

const TOGGLE_REGISTRY: Record<string, {
  label: string;
  description: string;
  icon: React.ReactNode;
  settingKey: keyof AccessibilitySettings;
}> = {
  theme: {
    label: 'Theme',
    description: 'Cycle through themes',
    icon: <Sun className="w-4 h-4" />,
    settingKey: 'theme',
  },
  highContrast: {
    label: 'High Contrast',
    description: 'Increases contrast for better readability',
    icon: <Eye className="w-4 h-4" />,
    settingKey: 'highContrast',
  },
  fontSize: {
    label: 'Large Text',
    description: 'Toggle larger text',
    icon: <Type className="w-4 h-4" />,
    settingKey: 'fontSize',
  },
  dyslexiaFont: {
    label: 'Dyslexia Font',
    description: 'Uses Atkinson Hyperlegible for clearer letterforms',
    icon: <BookOpen className="w-4 h-4" />,
    settingKey: 'dyslexiaFont',
  },
  focusMode: {
    label: 'Focus Mode',
    description: 'Dims surrounding content to reduce distractions',
    icon: <Focus className="w-4 h-4" />,
    settingKey: 'focusMode',
  },
  reduceMotion: {
    label: 'Reduce Motion',
    description: 'Minimizes animations and transitions',
    icon: <Sparkles className="w-4 h-4" />,
    settingKey: 'reduceMotion',
  },
  lineFocusGuide: {
    label: 'Line Focus Guide',
    description: 'Highlights the line you are reading',
    icon: <BookOpen className="w-4 h-4" />,
    settingKey: 'lineFocusGuide',
  },
  readingGuide: {
    label: 'Reading Guide',
    description: 'Highlights the line you are reading',
    icon: <BookOpen className="w-4 h-4" />,
    settingKey: 'readingGuide',
  },
  voiceControlEnabled: {
    label: 'Voice Control',
    description: 'Navigate using voice commands',
    icon: <Volume2 className="w-4 h-4" />,
    settingKey: 'voiceControlEnabled',
  },
  anonymousMode: {
    label: 'Anonymous Mode',
    description: 'Browse without tracking',
    icon: <Eye className="w-4 h-4" />,
    settingKey: 'anonymousMode',
  },
};

const DEFAULT_PINNED = ['focusMode', 'theme', 'readingGuide', 'anonymousMode'];

const PROFILE_ICONS: Record<string, React.ReactNode> = {
  BookOpen: <BookOpen className="w-4 h-4" />,
  Monitor: <Monitor className="w-4 h-4" />,
  Moon: <Moon className="w-4 h-4" />,
  Save: <Save className="w-4 h-4" />,
};

function getProfileIcon(iconName?: string): React.ReactNode {
  return (iconName && PROFILE_ICONS[iconName]) || <Settings className="w-4 h-4" />;
}

interface ProfileCardProps {
  profile: AccessibilityProfile;
  isBuiltIn: boolean;
  onApply: () => void;
  onDelete?: () => void;
}

function ProfileCard({ profile, isBuiltIn, onApply, onDelete }: ProfileCardProps) {
  return (
    <div className="flex items-center gap-2">
      <button
        onClick={onApply}
        className="flex items-center gap-2 flex-1 p-2 rounded-lg text-left text-sm transition-colors hover:bg-status-warning-50 dark:hover:bg-status-warning-900/20 text-lsc-dark/70 dark:text-lsc-cream/70 border border-earth-200 dark:border-earth-700"
        aria-label={`Apply ${profile.name} profile`}
      >
        <div className="p-1.5 rounded-lg bg-earth-100 dark:bg-earth-800">
          {getProfileIcon(profile.icon)}
        </div>
        <span className="font-medium truncate text-lsc-dark dark:text-lsc-cream">{profile.name}</span>
      </button>
      {!isBuiltIn && onDelete && (
        <button
          onClick={onDelete}
          className="p-1.5 text-earth-600 hover:text-status-danger-500 dark:text-earth-500 dark:hover:text-status-danger-400 rounded-lg hover:bg-status-danger-50 dark:hover:bg-status-danger-900/20 transition-colors"
          aria-label={`Delete ${profile.name} profile`}
        >
          <Trash2 className="w-3.5 h-3.5" />
        </button>
      )}
    </div>
  );
}

interface QuickAccessibilityWidgetProps {
  /** Position of the widget */
  position?: 'bottom-right' | 'bottom-left' | 'top-right' | 'top-left';
  /** Callback to open full settings */
  onOpenSettings?: () => void;
  /**
   * Controlled open state. When provided, the widget renders no floating
   * launcher button (the host supplies its own trigger) and reports open/close
   * via onOpenChange. Leaving this undefined keeps the original self-managed
   * floating-widget behaviour.
   */
  open?: boolean;
  /** Open-state change callback for controlled usage. */
  onOpenChange?: (open: boolean) => void;
  /** Show a one-click "Calm work session" preset button inside the panel. */
  showCalmSession?: boolean;
}

export function QuickAccessibilityWidget({
  position = 'bottom-right',
  onOpenSettings,
  open,
  onOpenChange,
  showCalmSession = false,
}: QuickAccessibilityWidgetProps) {
  const { settings, updateSetting, resetSettings } = useUnifiedAccessibility();
  const isControlled = open !== undefined;
  const [internalOpen, setInternalOpen] = useState(false);
  const isOpen = isControlled ? open : internalOpen;
  const setIsOpen = useCallback(
    (next: boolean | ((prev: boolean) => boolean)) => {
      const resolved = typeof next === 'function' ? next(isOpen) : next;
      if (isControlled) {
        onOpenChange?.(resolved);
      } else {
        setInternalOpen(resolved);
      }
    },
    [isControlled, isOpen, onOpenChange],
  );
  const [isMinimized, setIsMinimized] = useState(false);
  const [announcement, setAnnouncement] = useState('');
  const [showShortcuts, setShowShortcuts] = useState(false);
  const [isCustomizing, setIsCustomizing] = useState(false);
  const [showSavePrompt, setShowSavePrompt] = useState(false);
  const [newProfileName, setNewProfileName] = useState('');
  const [showResetConfirm, setShowResetConfirm] = useState(false);
  const widgetRef = useRef<HTMLDivElement>(null);
  const announcementTimerRef = useRef<ReturnType<typeof setTimeout>>();

  const allProfiles = [
    ...(settings.builtInProfiles || []),
    ...(settings.savedProfiles || []),
  ];

  const applyProfile = useCallback((profile: AccessibilityProfile) => {
    const entries = Object.entries(profile.settings) as Array<[keyof typeof profile.settings, unknown]>;
    for (const [key, value] of entries) {
      if (key !== 'builtInProfiles' && key !== 'savedProfiles') {
        (updateSetting as (k: string, v: unknown) => void)(key as string, value);
      }
    }
  }, [updateSetting]);

  // One-click "Calm work session": applies the existing Calm Mode (low-anxiety)
  // preset — reduce motion + muted colors + quiet mode and friends — via the
  // same updateSetting path the preset selector uses. Invents no new keys.
  const applyCalmSession = useCallback(() => {
    Object.entries(LOW_ANXIETY_PRESET.settings).forEach(([key, value]) => {
      (updateSetting as (k: string, v: unknown) => void)(key, value);
    });
  }, [updateSetting]);

  const saveCurrentProfile = useCallback(() => {
    const name = newProfileName.trim();
    if (!name) return;

    const newProfile: AccessibilityProfile = {
      id: `custom-${Date.now()}`,
      name,
      icon: 'Save',
      settings: {
        focusMode: settings.focusMode,
        dyslexiaFont: settings.dyslexiaFont,
        lineSpacing: settings.lineSpacing,
        fontSize: settings.fontSize,
        reduceMotion: settings.reduceMotion,
        highContrast: settings.highContrast,
        theme: settings.theme,
        mutedColors: settings.mutedColors,
        readingGuide: settings.readingGuide,
        lineFocusGuide: settings.lineFocusGuide,
        bionicReading: settings.bionicReading,
        quietMode: settings.quietMode,
        enhancedFocus: settings.enhancedFocus,
        colorBlindMode: settings.colorBlindMode,
        contentDensity: settings.contentDensity,
        fontWeight: settings.fontWeight,
      },
      createdAt: new Date().toISOString(),
    };

    const current = settings.savedProfiles || [];
    updateSetting('savedProfiles', [...current, newProfile]);
    setNewProfileName('');
    setShowSavePrompt(false);
  }, [newProfileName, settings, updateSetting]);

  const deleteProfile = useCallback((profileId: string) => {
    const current = settings.savedProfiles || [];
    updateSetting('savedProfiles', current.filter((p: AccessibilityProfile) => p.id !== profileId));
  }, [settings.savedProfiles, updateSetting]);

  // "Reset to defaults": turn every visual/sensory accommodation back to its
  // default so a patron who can't undo a change by hand can get the page back
  // to normal in one tap. resetSettings keeps their saved profiles (language
  // lives in I18nContext, so reset never touches it).
  // announce() is called inline in the onClick (it's declared below), matching
  // the Calm work session pattern.
  const handleReset = useCallback(() => {
    resetSettings();
    setShowResetConfirm(false);
  }, [resetSettings]);

  // Position classes
  const positionClasses = {
    'bottom-right': 'bottom-20 right-4 lg:bottom-4',
    'bottom-left': 'bottom-20 left-4 lg:bottom-4',
    'top-right': 'top-4 right-4',
    'top-left': 'top-4 left-4',
  };

  const announce = useCallback((message: string) => {
    if (announcementTimerRef.current) {
      clearTimeout(announcementTimerRef.current);
    }
    setAnnouncement(message);
    announcementTimerRef.current = setTimeout(() => setAnnouncement(''), 3000);
  }, []);

  // Clean up announcement timer on unmount
  useEffect(() => {
    return () => {
      if (announcementTimerRef.current) {
        clearTimeout(announcementTimerRef.current);
      }
    };
  }, []);

  // Toggle functions
  const toggleTheme = useCallback(() => {
    const themes = ['light', 'dark', 'high-contrast', 'system'] as const;
    const currentIndex = themes.indexOf(settings.theme);
    const nextIndex = (currentIndex + 1) % themes.length;
    const next = themes[nextIndex]!;
    updateSetting('theme', next);
    return next;
  }, [settings.theme, updateSetting]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Escape closes the widget
      if (e.key === 'Escape' && isOpen) {
        if (isCustomizing) {
          setIsCustomizing(false);
        } else if (showSavePrompt) {
          setShowSavePrompt(false);
        } else {
          setIsOpen(false);
        }
        return;
      }

      // ? toggles shortcut reference when widget is open
      if (e.key === '?' && isOpen && !isMinimized) {
        const target = e.target as HTMLElement;
        if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA') return;
        e.preventDefault();
        setShowShortcuts((prev) => !prev);
        return;
      }

      // Alt+Shift shortcuts
      if (e.altKey && e.shiftKey) {
        const key = e.key.toUpperCase();

        switch (key) {
          case 'T': {
            e.preventDefault();
            const next = toggleTheme();
            announce(`Theme changed to ${next}`);
            break;
          }
          case 'C': {
            e.preventDefault();
            const next = !settings.highContrast;
            updateSetting('highContrast', next);
            announce(`High contrast ${next ? 'enabled' : 'disabled'}`);
            break;
          }
          case 'F': {
            e.preventDefault();
            const next = !settings.focusMode;
            updateSetting('focusMode', next);
            announce(`Focus mode ${next ? 'enabled' : 'disabled'}`);
            break;
          }
          case 'D': {
            e.preventDefault();
            const next = !settings.dyslexiaFont;
            updateSetting('dyslexiaFont', next);
            announce(`Dyslexia font ${next ? 'enabled' : 'disabled'}`);
            break;
          }
          case 'M': {
            e.preventDefault();
            const next = !settings.reduceMotion;
            updateSetting('reduceMotion', next);
            announce(`Reduce motion ${next ? 'enabled' : 'disabled'}`);
            break;
          }
          case 'R': {
            e.preventDefault();
            const next = !settings.lineFocusGuide;
            updateSetting('lineFocusGuide', next);
            announce(`Reading guide ${next ? 'enabled' : 'disabled'}`);
            break;
          }
          case 'A': {
            e.preventDefault();
            setIsOpen((prev) => !prev);
            break;
          }
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, isMinimized, isCustomizing, showSavePrompt, settings, toggleTheme, updateSetting, announce]);

  // Close on click outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (widgetRef.current && !widgetRef.current.contains(e.target as Node)) {
        setIsOpen(false);
        setIsCustomizing(false);
        setShowSavePrompt(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [isOpen]);

  const getThemeIcon = () => {
    switch (settings.theme) {
      case 'dark':
        return <Moon className="w-4 h-4" />;
      case 'system':
        return <Monitor className="w-4 h-4" />;
      default:
        return <Sun className="w-4 h-4" />;
    }
  };

  const pinnedKeys = settings.quickSettingsPinned?.length
    ? settings.quickSettingsPinned
    : DEFAULT_PINNED;

  const togglePinned = useCallback((key: string) => {
    const current = settings.quickSettingsPinned?.length
      ? [...settings.quickSettingsPinned]
      : [...DEFAULT_PINNED];
    const idx = current.indexOf(key);
    if (idx >= 0) {
      current.splice(idx, 1);
    } else {
      current.push(key);
    }
    updateSetting('quickSettingsPinned', current);
  }, [settings.quickSettingsPinned, updateSetting]);

  const getToggleActive = (key: string): boolean => {
    const toggle = TOGGLE_REGISTRY[key];
    if (!toggle) return false;
    if (key === 'theme') return false;
    if (key === 'fontSize') return settings.fontSize !== 'normal';
    return !!settings[toggle.settingKey];
  };

  const handleToggleClick = (key: string) => {
    if (key === 'theme') {
      const next = toggleTheme();
      announce(`Theme changed to ${next}`);
      return;
    }
    const toggle = TOGGLE_REGISTRY[key];
    if (!toggle) return;
    if (key === 'fontSize') {
      updateSetting('fontSize', settings.fontSize === 'normal' ? 'large' : 'normal');
      return;
    }
    const currentVal = settings[toggle.settingKey];
    updateSetting(toggle.settingKey, !currentVal);
  };

  // Don't show if disabled in settings — but a controlled host (e.g. the
  // staff shell) supplies its own trigger, so always honour its open state.
  if (!isControlled && !settings.showQuickSettings) return null;

  return (
    <div
      ref={widgetRef}
      className={`fixed ${positionClasses[settings.quickSettingsPosition || position]} z-[9980]`}
    >
      {/* Screen reader announcements */}
      <div className="sr-only" role="status" aria-live="polite" aria-atomic="true">
        {announcement}
      </div>

      {/* Floating button when closed (uncontrolled mode only — a controlled
          host renders its own trigger) */}
      {!isOpen && !isControlled && (
        <button
          onClick={() => setIsOpen(true)}
          className={`p-3 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-full shadow-lg hover:shadow-lg ${settings.reduceMotion ? '' : 'transition-all'}`}
          aria-label={t('aria.accessibility.openAccessibilityQuickSettings')}
          aria-expanded={isOpen}
        >
          <Settings className="w-6 h-6" aria-hidden="true" />
        </button>
      )}

      {/* Expanded widget */}
      {isOpen && (
        <FocusTrap active={true} focusTrapOptions={{ escapeDeactivates: false, allowOutsideClick: true, returnFocusOnDeactivate: true, fallbackFocus: () => document.body }}>
        <div>
          {/* Mobile backdrop */}
          <div
            className="fixed inset-0 bg-black/30 z-[9979] lg:hidden"
            onClick={() => setIsOpen(false)}
            onKeyDown={(e) => { if (e.key === 'Escape') setIsOpen(false) }}
            role="presentation"
          />

          <div
            className={`
              fixed inset-x-0 bottom-0 z-[9980]
              lg:relative lg:inset-auto
              bg-lsc-white dark:bg-earth-900
              rounded-t-xl lg:rounded-xl
              shadow-lg border border-lsc-border dark:border-earth-700
              max-h-[70vh] lg:max-h-none
              lg:w-[min(20rem,calc(100vw-2rem))] overflow-hidden transition-all
              ${isMinimized ? 'lg:h-14' : ''}
            `}
            role="dialog"
            aria-label={t('aria.accessibility.quickAccessibilitySettings')}
          >
            {/* Drag handle - mobile only */}
            <div className="flex justify-center pt-2 pb-1 lg:hidden">
              <div className="w-10 h-1 rounded-full bg-earth-300 dark:bg-earth-600" />
            </div>

            {/* Header */}
            <div className="flex items-center justify-between p-3 border-b border-lsc-border dark:border-earth-700 bg-earth-50 dark:bg-earth-800">
              <div className="flex items-center gap-2">
                <Settings className="w-5 h-5 text-status-warning-500" aria-hidden="true" />
                <span className="font-medium text-lsc-dark dark:text-lsc-cream">
                  Quick Settings
                </span>
              </div>
              <div className="flex items-center gap-1">
                <button
                  onClick={() => setIsMinimized(!isMinimized)}
                  className="p-1.5 text-earth-600 hover:text-lsc-dark/70 dark:text-lsc-cream/70 dark:hover:text-earth-300 rounded-lg hover:bg-earth-200 dark:bg-earth-600 dark:hover:bg-earth-700 transition-colors hidden lg:block"
                  aria-label={isMinimized ? 'Expand' : 'Minimize'}
                >
                  <ChevronUp
                    className={`w-4 h-4 transition-transform ${isMinimized ? 'rotate-180' : ''}`}
                    aria-hidden="true"
                  />
                </button>
                <button
                  onClick={() => setIsOpen(false)}
                  className="p-1.5 text-earth-600 hover:text-lsc-dark/70 dark:text-lsc-cream/70 dark:hover:text-earth-300 rounded-lg hover:bg-earth-200 dark:bg-earth-600 dark:hover:bg-earth-700 transition-colors"
                  aria-label={t('aria.accessibility.closeQuickSettings')}
                >
                  <X className="w-4 h-4" aria-hidden="true" />
                </button>
              </div>
            </div>

            {/* Quick toggles */}
            {!isMinimized && !isCustomizing && (
              <div className="p-2 space-y-1 max-h-[calc(70vh-8rem)] lg:max-h-96 overflow-y-auto">
                {/* One-click Calm work session preset */}
                {showCalmSession && (
                  <div className="pb-2 mb-1 border-b border-earth-200 dark:border-earth-700">
                    <button
                      type="button"
                      onClick={() => {
                        applyCalmSession();
                        announce('Calm work session enabled');
                      }}
                      className="flex items-center gap-2 w-full p-2.5 rounded-lg text-left text-sm font-medium transition-colors bg-lsc-rose/10 dark:bg-lsc-rose/15 text-lsc-rose dark:text-lsc-cream hover:bg-lsc-rose/20 dark:hover:bg-lsc-rose/25 focus:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose"
                    >
                      <Sparkles className="w-4 h-4 flex-shrink-0" aria-hidden="true" />
                      <span>Calm work session</span>
                    </button>
                    <p className="px-1 pt-1 text-xs text-lsc-dark/60 dark:text-lsc-cream/60">
                      Reduces motion, mutes colors, and quiets the interface.
                    </p>
                  </div>
                )}

                {/* Profiles section */}
                {allProfiles.length > 0 && (
                  <div className="pb-2 mb-1 border-b border-earth-200 dark:border-earth-700">
                    <div className="px-1 pb-1.5 flex items-center justify-between">
                      <span className="text-xs font-semibold uppercase tracking-wider text-earth-600 dark:text-earth-400">
                        Profiles
                      </span>
                      <button
                        onClick={() => setShowSavePrompt(!showSavePrompt)}
                        className="text-xs text-status-warning-700 dark:text-status-warning-400 hover:text-status-warning-800 dark:hover:text-status-warning-300 font-medium transition-colors"
                        aria-label="Save current settings as profile"
                      >
                        + Save Current
                      </button>
                    </div>
                    {showSavePrompt && (
                      <div className="flex gap-1.5 px-1 pb-2">
                        <input
                          type="text"
                          value={newProfileName}
                          onChange={(e) => setNewProfileName(e.target.value)}
                          onKeyDown={(e) => { if (e.key === 'Enter') saveCurrentProfile(); if (e.key === 'Escape') setShowSavePrompt(false); }}
                          placeholder="Profile name..."
                          className="flex-1 px-2 py-1 text-sm rounded-lg border border-earth-300 dark:border-earth-600 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream placeholder:text-earth-400 focus:outline-none focus:ring-1 focus:ring-status-warning-500"
                          autoFocus
                        />
                        <button
                          onClick={saveCurrentProfile}
                          disabled={!newProfileName.trim()}
                          className="px-2 py-1 text-sm font-medium rounded-lg bg-status-warning-500 text-white hover:bg-status-warning-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                        >
                          Save
                        </button>
                      </div>
                    )}
                    <div className="space-y-1 px-1">
                      {(settings.builtInProfiles || []).map((profile: AccessibilityProfile) => (
                        <ProfileCard
                          key={profile.id}
                          profile={profile}
                          isBuiltIn={true}
                          onApply={() => applyProfile(profile)}
                        />
                      ))}
                      {(settings.savedProfiles || []).map((profile: AccessibilityProfile) => (
                        <ProfileCard
                          key={profile.id}
                          profile={profile}
                          isBuiltIn={false}
                          onApply={() => applyProfile(profile)}
                          onDelete={() => deleteProfile(profile.id)}
                        />
                      ))}
                    </div>
                  </div>
                )}

                {/* Pinned toggles */}
                {pinnedKeys.map(key => {
                  const toggle = TOGGLE_REGISTRY[key];
                  if (!toggle) return null;

                  if (key === 'theme') {
                    return (
                      <button
                        key={key}
                        onClick={() => handleToggleClick(key)}
                        className="flex items-center gap-3 w-full p-3 rounded-lg text-left hover:bg-earth-100 dark:bg-earth-700 dark:hover:bg-earth-800 text-lsc-dark/70 dark:text-lsc-cream/70 transition-colors"
                      >
                        <div className="p-2 rounded-lg bg-earth-100 dark:bg-earth-800">
                          {getThemeIcon()}
                        </div>
                        <div className="flex-1">
                          <div className="font-medium text-sm text-lsc-dark dark:text-lsc-cream">Theme</div>
                          <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 capitalize">
                            {settings.theme}
                          </div>
                        </div>
                      </button>
                    );
                  }

                  const description = key === 'fontSize'
                    ? `Currently: ${settings.fontSize}`
                    : toggle.description;

                  return (
                    <QuickToggle
                      key={key}
                      label={toggle.label}
                      description={description}
                      icon={toggle.icon}
                      isActive={getToggleActive(key)}
                      onClick={() => handleToggleClick(key)}
                    />
                  );
                })}

                {/* Customize button */}
                <button
                  onClick={() => setIsCustomizing(true)}
                  className="flex items-center gap-3 w-full p-3 rounded-lg text-left hover:bg-earth-100 dark:bg-earth-700 dark:hover:bg-earth-800 text-lsc-dark/70 dark:text-lsc-cream/70 transition-colors mt-1 border-t border-lsc-border dark:border-earth-700 pt-3"
                >
                  <div className="p-2 rounded-lg bg-earth-100 dark:bg-earth-800">
                    <SlidersHorizontal className="w-4 h-4" />
                  </div>
                  <span className="font-medium text-sm text-lsc-dark dark:text-lsc-cream">Customize</span>
                </button>

                {/* Open full settings */}
                {onOpenSettings && (
                  <button
                    onClick={() => {
                      setIsOpen(false);
                      onOpenSettings();
                    }}
                    className="flex items-center gap-3 w-full p-3 rounded-lg text-left hover:bg-earth-100 dark:bg-earth-700 dark:hover:bg-earth-800 text-lsc-dark/70 dark:text-lsc-cream/70 transition-colors mt-2 border-t border-lsc-border dark:border-earth-700 pt-3"
                  >
                    <div className="p-2 rounded-lg bg-earth-100 dark:bg-earth-800">
                      <Settings className="w-4 h-4" />
                    </div>
                    <span className="font-medium text-sm text-lsc-dark dark:text-lsc-cream">All Settings</span>
                  </button>
                )}

                {/* Links to accessibility pages */}
                <div className="mt-2 border-t border-lsc-border dark:border-earth-700 pt-3 space-y-1">
                  <Link
                    to="/accessibility/settings"
                    onClick={() => setIsOpen(false)}
                    className="flex items-center gap-3 w-full p-3 rounded-lg text-left hover:bg-earth-100 dark:bg-earth-700 dark:hover:bg-earth-800 text-lsc-dark/70 dark:text-lsc-cream/70 transition-colors"
                  >
                    <div className="p-2 rounded-lg bg-earth-100 dark:bg-earth-800">
                      <Settings className="w-4 h-4" aria-hidden="true" />
                    </div>
                    <span className="font-medium text-sm text-lsc-dark dark:text-lsc-cream">All accessibility settings</span>
                  </Link>
                  <Link
                    to="/accessibility"
                    onClick={() => setIsOpen(false)}
                    className="flex items-center gap-3 w-full p-3 rounded-lg text-left hover:bg-earth-100 dark:bg-earth-700 dark:hover:bg-earth-800 text-lsc-dark/70 dark:text-lsc-cream/70 transition-colors"
                  >
                    <div className="p-2 rounded-lg bg-earth-100 dark:bg-earth-800">
                      <BookOpen className="w-4 h-4" aria-hidden="true" />
                    </div>
                    <span className="font-medium text-sm text-lsc-dark dark:text-lsc-cream">View our accessibility statement</span>
                  </Link>
                </div>

                {/* Reset to defaults — one tap back to normal for patrons who
                    can't undo changes by hand. Two-step inline confirm because
                    the reset can't be undone. */}
                <div className="mt-2 border-t border-lsc-border dark:border-earth-700 pt-3">
                  {!showResetConfirm ? (
                    <button
                      type="button"
                      onClick={() => setShowResetConfirm(true)}
                      className="flex items-center gap-3 w-full p-3 rounded-lg text-left text-status-danger-600 dark:text-status-danger-400 hover:bg-status-danger-50 dark:hover:bg-status-danger-900/20 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-status-danger-500"
                    >
                      <div className="p-2 rounded-lg bg-earth-100 dark:bg-earth-800">
                        <RotateCcw className="w-4 h-4" aria-hidden="true" />
                      </div>
                      <span className="font-medium text-sm">Reset to defaults</span>
                    </button>
                  ) : (
                    <div className="px-1">
                      <p className="px-2 pb-2 text-sm text-lsc-dark/80 dark:text-lsc-cream/80">
                        Turn off all accessibility settings and go back to normal? Your saved profiles are kept.
                      </p>
                      <div className="flex gap-1.5 px-1">
                        <button
                          type="button"
                          onClick={() => {
                            handleReset();
                            announce('Accessibility settings reset to defaults');
                          }}
                          className="flex-1 px-3 py-2 text-sm font-medium rounded-lg bg-status-danger-600 text-white hover:bg-status-danger-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-status-danger-500 focus-visible:ring-offset-2"
                        >
                          Reset
                        </button>
                        <button
                          type="button"
                          onClick={() => setShowResetConfirm(false)}
                          className="flex-1 px-3 py-2 text-sm font-medium rounded-lg border border-earth-300 dark:border-earth-600 text-lsc-dark dark:text-lsc-cream hover:bg-earth-100 dark:hover:bg-earth-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Customize view */}
            {!isMinimized && isCustomizing && (
              <div className="p-2 space-y-1 max-h-[calc(70vh-8rem)] lg:max-h-96 overflow-y-auto">
                <div className="px-3 pt-2 pb-1">
                  <p className="text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase tracking-wide">
                    Choose pinned toggles
                  </p>
                </div>
                {Object.entries(TOGGLE_REGISTRY).map(([key, toggle]) => {
                  const isPinned = pinnedKeys.includes(key);
                  return (
                    <button
                      key={key}
                      onClick={() => togglePinned(key)}
                      className={`
                        flex items-center gap-3 w-full p-3 rounded-lg text-left transition-colors
                        ${isPinned
                          ? 'bg-status-warning-50 dark:bg-status-warning-900/20 text-status-warning-700 dark:text-status-warning-300'
                          : 'hover:bg-earth-100 dark:hover:bg-earth-800 text-lsc-dark/70 dark:text-lsc-cream/70'
                        }
                      `}
                      role="checkbox"
                      aria-checked={isPinned}
                      aria-label={`${isPinned ? 'Unpin' : 'Pin'} ${toggle.label}`}
                    >
                      <div
                        className={`
                          w-5 h-5 rounded border-2 flex items-center justify-center flex-shrink-0
                          ${isPinned
                            ? 'bg-status-warning-500 border-status-warning-500 text-white'
                            : 'border-earth-300 dark:border-earth-600'
                          }
                        `}
                      >
                        {isPinned && <Check className="w-3 h-3" />}
                      </div>
                      <div className="p-1.5 rounded-lg bg-earth-100 dark:bg-earth-800">
                        {toggle.icon}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="font-medium text-sm text-lsc-dark dark:text-lsc-cream">{toggle.label}</div>
                        <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 truncate" title={toggle.description}>
                          {toggle.description}
                        </div>
                      </div>
                    </button>
                  );
                })}

                {/* Done button */}
                <button
                  onClick={() => setIsCustomizing(false)}
                  className="flex items-center justify-center w-full p-2.5 rounded-lg text-sm font-medium bg-lsc-rose hover:bg-lsc-rose/90 text-white transition-colors mt-2"
                >
                  Done
                </button>
              </div>
            )}

            {/* Keyboard shortcut reference */}
            {!isMinimized && showShortcuts && (
              <div className="px-3 py-2 border-t border-lsc-border dark:border-earth-700">
                <div className="flex items-center gap-2 mb-2">
                  <Keyboard className="w-3.5 h-3.5 text-status-warning-500" aria-hidden="true" />
                  <span className="text-xs font-medium text-lsc-dark dark:text-lsc-cream">Keyboard Shortcuts</span>
                </div>
                <div className="space-y-1">
                  {SHORTCUT_LIST.map(({ keys, action }) => (
                    <div key={keys} className="flex items-center justify-between text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                      <span>{action}</span>
                      <kbd className="px-1.5 py-0.5 bg-earth-200 dark:bg-earth-700 rounded font-mono text-[10px]">{keys}</kbd>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Keyboard hint */}
            {!isMinimized && (
              <div className="px-3 py-2 bg-earth-50 dark:bg-earth-800 border-t border-lsc-border dark:border-earth-700">
                <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 text-center">
                  Press <kbd className="px-1 py-0.5 bg-earth-200 dark:bg-earth-700 rounded">?</kbd> for keyboard shortcuts
                </p>
              </div>
            )}
          </div>
        </div>
        </FocusTrap>
      )}
    </div>
  );
}

export default QuickAccessibilityWidget;

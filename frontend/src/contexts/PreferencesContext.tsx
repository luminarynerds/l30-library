/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useState, useEffect, useCallback, useMemo, useRef, ReactNode } from 'react';
import { useAuth } from './AuthContext';
import { useAccessibility } from '../features/accessibility/hooks/useAccessibility';
import api from '../api/api';
import { API_BASE } from '@/api/types'

export interface UserPreferences {
  id: number;
  user_id: number;
  theme: 'light' | 'dark' | 'system';
  font_size: 'small' | 'medium' | 'large';
  dyslexia_font: boolean;
  reduced_motion: boolean;
  high_contrast: boolean;
  focus_mode: 'balanced' | 'quick_scan' | 'deep_dive';
  hide_streaks: boolean;
  hide_gamification: boolean;
  preferred_content_variant: string;
  // Dashboard layout customization
  dashboard_layout: Record<string, unknown>;
  sidebar_collapsed: boolean;
  compact_mode: boolean;
  // Favorite actions and shortcuts
  favorite_actions: (string | { id: string; label: string; icon: string; action: string; metadata?: Record<string, unknown> })[];
  action_shortcuts: Record<string, string>;
  // Notification preferences
  notification_preferences: Record<string, unknown>;
  email_digests_enabled: boolean;
  digest_frequency: 'daily' | 'weekly' | 'monthly';
  quiet_hours_start?: string;
  quiet_hours_end?: string;
  // Workflow and productivity settings
  workflow_templates: unknown[];
  default_list_view: 'grid' | 'list' | 'card';
  auto_expand_details: boolean;
  keyboard_shortcuts_enabled: boolean;
  search_filters_saved: Record<string, unknown>;
  // Productivity settings
  focus_timer_duration: number;
  break_duration: number;
  enable_focus_timer: boolean;
  enable_break_reminders: boolean;
}

interface PreferencesContextType {
  preferences: UserPreferences;
  loading: boolean;
  updatePreferences: (updates: Partial<UserPreferences>) => Promise<void>;
  refreshPreferences: () => Promise<void>;
}

const defaultPreferences: UserPreferences = {
  id: 0,
  user_id: 0,
  theme: 'system',
  font_size: 'medium',
  dyslexia_font: false,
  reduced_motion: false,
  high_contrast: false,
  focus_mode: 'balanced',
  hide_streaks: false,
  hide_gamification: false,
  preferred_content_variant: 'default',
  // Dashboard layout customization
  dashboard_layout: {},
  sidebar_collapsed: false,
  compact_mode: false,
  // Favorite actions and shortcuts
  favorite_actions: [],
  action_shortcuts: {},
  // Notification preferences
  notification_preferences: {},
  email_digests_enabled: true,
  digest_frequency: 'daily',
  // Workflow and productivity settings
  workflow_templates: [],
  default_list_view: 'grid',
  auto_expand_details: false,
  keyboard_shortcuts_enabled: true,
  search_filters_saved: {},
  // Productivity settings
  focus_timer_duration: 25,
  break_duration: 5,
  enable_focus_timer: false,
  enable_break_reminders: false,
};

const PreferencesContext = createContext<PreferencesContextType>({
  preferences: defaultPreferences,
  loading: false,
  updatePreferences: async () => {},
  refreshPreferences: async () => {},
});

export function PreferencesProvider({ children }: { children: ReactNode }) {
  const { isAuthenticated } = useAuth();
  const { updateSetting } = useAccessibility();
  const [preferences, setPreferences] = useState<UserPreferences>(() => {
    // Security note: User preferences are stored in localStorage for persistence across sessions.
    // This is a deliberate tradeoff - these preferences (theme, font size, accessibility settings)
    // are non-sensitive UI settings that don't contain PII or auth tokens. The benefit of
    // instant preference loading on page load outweighs the XSS risk for this non-sensitive data.
    // Auth tokens are stored in memory only (see AuthContext) for security.
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem('lsc-preferences');
      if (stored) {
        try {
          return { ...defaultPreferences, ...JSON.parse(stored) };
        } catch {
          return defaultPreferences;
        }
      }
    }
    return defaultPreferences;
  });
  const [loading, setLoading] = useState(false);

  const refreshPreferences = useCallback(async () => {
    if (!isAuthenticated) return;

    setLoading(true);
    try {
      const data = await api.get(`${API_BASE}/learning/preferences`);
      // Merge over defaults so a partial (or disabled-feature) payload never
      // leaves required fields undefined.
      setPreferences({ ...defaultPreferences, ...(data as Partial<UserPreferences>) });
    } catch {
      // Feature disabled (404) or API unavailable: keep the current local
      // preferences (loaded from localStorage) rather than wiping them.
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated]);

  useEffect(() => {
    if (isAuthenticated) {
      refreshPreferences();
    }
  }, [isAuthenticated, refreshPreferences]);

  // Sync accessibility-related preferences to UnifiedAccessibilityContext.
  // DOM class application (dyslexia-font, high-contrast, reduce-motion) is managed
  // exclusively by cssApplicator.ts via UnifiedAccessibilityProvider. We bridge
  // the two systems here so that API-loaded preferences are reflected in the DOM.
  const prevSyncRef = useRef({ dyslexia_font: preferences.dyslexia_font, high_contrast: preferences.high_contrast, reduced_motion: preferences.reduced_motion });
  useEffect(() => {
    const prev = prevSyncRef.current;
    if (prev.dyslexia_font !== preferences.dyslexia_font) {
      updateSetting('dyslexiaFont', preferences.dyslexia_font);
    }
    if (prev.high_contrast !== preferences.high_contrast) {
      updateSetting('highContrast', preferences.high_contrast);
    }
    if (prev.reduced_motion !== preferences.reduced_motion) {
      updateSetting('reduceMotion', preferences.reduced_motion);
    }
    prevSyncRef.current = { dyslexia_font: preferences.dyslexia_font, high_contrast: preferences.high_contrast, reduced_motion: preferences.reduced_motion };
  }, [preferences.dyslexia_font, preferences.high_contrast, preferences.reduced_motion, updateSetting]);

  // Apply non-theme preferences to document.
  // NOTE: Theme (.dark class) is NOT applied here — it is managed exclusively by
  // UnifiedAccessibilityProvider via cssApplicator.ts. Applying it in both places
  // caused the two providers to fight over the .dark class, flipping the user's
  // theme preference on every render cycle.
  useEffect(() => {
    const root = document.documentElement;

    // Font size
    const fontSizes: Record<string, string> = { small: '14px', medium: '16px', large: '18px' };
    root.style.fontSize = fontSizes[preferences.font_size] || '16px';

    // Dyslexia-friendly font, high contrast, and reduced motion are applied
    // EXCLUSIVELY by cssApplicator.ts (UnifiedAccessibilityProvider) and bridged
    // from this store via the updateSetting() sync effect above. Toggling them
    // here too made the two providers fight: on reload this effect re-ran with
    // lsc-preferences' defaults (all false) and stripped whatever the a11y widget
    // had set in accessibility-settings, leaving a half-applied, broken-looking page.

    // Focus mode
    root.classList.remove('focus-quick-scan', 'focus-deep-dive');
    if (preferences.focus_mode === 'quick_scan') {
      root.classList.add('focus-quick-scan');
    } else if (preferences.focus_mode === 'deep_dive') {
      root.classList.add('focus-deep-dive');
    }

    // Save to localStorage for persistence
    localStorage.setItem('lsc-preferences', JSON.stringify(preferences));

  }, [preferences]);

  const preferencesRef = useRef(preferences);
  preferencesRef.current = preferences;

  const updatePreferences = useCallback(async (updates: Partial<UserPreferences>) => {
    // Save previous state for rollback (use ref to avoid stale closure)
    const previousPrefs = preferencesRef.current;

    // Optimistically update local state
    const newPrefs = { ...previousPrefs, ...updates };
    setPreferences(newPrefs);

    if (isAuthenticated) {
      try {
        const data = await api.put(`${API_BASE}/learning/preferences`, updates);
        setPreferences({ ...defaultPreferences, ...(data as Partial<UserPreferences>) });
      } catch (error: unknown) {
        // A 404 means the learning-platform endpoint is disabled. The preference
        // still works locally (persisted to localStorage), so keep the optimistic
        // value and degrade quietly instead of rolling back and rejecting.
        if ((error as { status?: number })?.status === 404) {
          return;
        }
        // Rollback on real errors so the caller can surface the failure.
        setPreferences(previousPrefs);
        throw error;
      }
    }
  }, [isAuthenticated]);

  const contextValue = useMemo(() => ({
    preferences, loading, updatePreferences, refreshPreferences,
  }), [preferences, loading, updatePreferences, refreshPreferences]);

  return (
    <PreferencesContext.Provider value={contextValue}>
      {children}
    </PreferencesContext.Provider>
  );
}

export function usePreferences() {
  return useContext(PreferencesContext);
}
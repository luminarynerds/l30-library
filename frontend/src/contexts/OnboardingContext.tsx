/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/* eslint-disable react-refresh/only-export-components */
/**
 * OnboardingContext - Manages user onboarding state across the application
 *
 * Server is the source of truth for the patron 5-step welcome wizard:
 * on mount (when authenticated), we hydrate the wizard flags from
 * `GET /patrons/me/onboarding-status`. localStorage remains as an
 * immediate/offline cache for UI-only state (tooltips, checklist,
 * feature highlights) and as a render-fast fallback before hydration
 * completes.
 *
 * Without the server hydrate, a patron who completed onboarding on
 * device A would get re-onboarded on device B because device B's
 * localStorage starts empty.
 */
import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useAuth } from './AuthContext';
import { patronOnboardingApi, PatronOnboardingStatus } from '@/api/domains/patron/patron-onboarding-api';
import { isApiError } from '@/lib/api-client';

// Current onboarding version - increment when adding new onboarding steps
const ONBOARDING_VERSION = '1.0';

// Getting started checklist items
export interface ChecklistItem {
  id: string;
  title: string;
  description: string;
  completed: boolean;
  action?: string; // Route or action to take
  icon?: string;
}

export const DEFAULT_CHECKLIST_ITEMS: Omit<ChecklistItem, 'completed'>[] = [
  {
    id: 'complete_profile',
    title: 'Complete your profile',
    description: 'Add your contact information and preferences',
    action: '/account',
    icon: 'user',
  },
  {
    id: 'first_search',
    title: 'Search the catalog',
    description: 'Discover books, movies, and more in our collection',
    action: '/catalog',
    icon: 'search',
  },
  {
    id: 'first_hold',
    title: 'Place your first hold',
    description: 'Reserve an item and we\'ll notify you when it\'s ready',
    action: '/catalog',
    icon: 'bookmark',
  },
  {
    id: 'create_reading_list',
    title: 'Create a reading list',
    description: 'Organize books you want to read',
    action: '/reading-lists',
    icon: 'list',
  },
  {
    id: 'explore_events',
    title: 'Explore library events',
    description: 'Find programs, classes, and activities',
    action: '/events',
    icon: 'calendar',
  },
];

interface OnboardingState {
  // Welcome wizard
  welcomeWizardCompleted: boolean;
  welcomeWizardSkipped: boolean;
  showWelcomeWizard: boolean;

  // Tooltips
  showTooltips: boolean;
  dismissedTooltips: string[];

  // Feature highlights
  showFeatureHighlights: boolean;

  // Getting started checklist
  checklistItems: ChecklistItem[];
  checklistDismissed: boolean;

  // Version tracking
  onboardingVersion: string;

  // Server-derived current step (1-5), null when unknown / pre-hydration
  currentStep: number | null;
}

interface OnboardingContextType extends OnboardingState {
  // Welcome wizard actions
  completeWelcomeWizard: () => void;
  skipWelcomeWizard: () => void;
  resetWelcomeWizard: () => void;

  // Tooltip actions
  toggleTooltips: (show: boolean) => void;
  dismissTooltip: (tooltipId: string) => void;
  resetTooltips: () => void;
  isTooltipDismissed: (tooltipId: string) => boolean;

  // Feature highlights actions
  toggleFeatureHighlights: (show: boolean) => void;

  // Checklist actions
  completeChecklistItem: (itemId: string) => void;
  dismissChecklist: () => void;
  resetChecklist: () => void;

  // Full reset
  resetAllOnboarding: () => void;

  // Patron onboarding flow - should the wizard redirect be triggered?
  shouldShowPatronOnboarding: boolean;

  // Loading state (true while server-hydration is in flight)
  isLoading: boolean;
}

const OnboardingContext = createContext<OnboardingContextType | null>(null);

const STORAGE_KEY = 'lsc-onboarding-state';

function getInitialState(): OnboardingState {
  // Try to load from localStorage first
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      const parsed = JSON.parse(stored);
      // Merge with defaults to handle new fields
      return {
        welcomeWizardCompleted: parsed.welcomeWizardCompleted ?? false,
        welcomeWizardSkipped: parsed.welcomeWizardSkipped ?? false,
        showWelcomeWizard: parsed.showWelcomeWizard ?? true,
        showTooltips: parsed.showTooltips ?? true,
        dismissedTooltips: parsed.dismissedTooltips ?? [],
        showFeatureHighlights: parsed.showFeatureHighlights ?? true,
        checklistItems: parsed.checklistItems ?? DEFAULT_CHECKLIST_ITEMS.map(item => ({ ...item, completed: false })),
        checklistDismissed: parsed.checklistDismissed ?? false,
        onboardingVersion: parsed.onboardingVersion ?? ONBOARDING_VERSION,
        currentStep: null,
      };
    }
  } catch {
    // Ignore parse errors, use defaults
  }

  return {
    welcomeWizardCompleted: false,
    welcomeWizardSkipped: false,
    showWelcomeWizard: true,
    showTooltips: true,
    dismissedTooltips: [],
    showFeatureHighlights: true,
    checklistItems: DEFAULT_CHECKLIST_ITEMS.map(item => ({ ...item, completed: false })),
    checklistDismissed: false,
    onboardingVersion: ONBOARDING_VERSION,
    currentStep: null,
  };
}

export function OnboardingProvider({ children }: { children: ReactNode }): React.ReactElement {
  const { user, isAuthenticated } = useAuth();
  const [state, setState] = useState<OnboardingState>(getInitialState);

  // Persist state to localStorage whenever it changes
  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  }, [state]);

  // Server hydration: source of truth for wizard flags.
  // Runs once per authenticated session; gated on user.role to skip for staff.
  const isPatron = !!user && (user.role === 'patron' || user.role === 'child');
  const {
    data: serverStatus,
    isFetching: isHydrating,
  } = useQuery<PatronOnboardingStatus | null>({
    queryKey: ['onboarding-status', user?.id],
    enabled: isAuthenticated && isPatron,
    queryFn: async () => {
      try {
        return await patronOnboardingApi.getStatus();
      } catch (err) {
        // If the endpoint is unavailable (network/server hiccup) we fall
        // back to localStorage rather than blocking the UI. A 401/403
        // means the user isn't actually a patron — silently no-op.
        if (isApiError(err) && (err.status === 401 || err.status === 403)) {
          return null;
        }
        // For other errors, return null and keep local state.
        return null;
      }
    },
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  });

  // Apply server state to context (single source of truth for the wizard).
  // UI-only state (tooltips, checklist, feature highlights) is left alone —
  // those have no server counterpart.
  useEffect(() => {
    if (!serverStatus) return;
    const completed = serverStatus.step_complete_completed || !!serverStatus.completed_at;
    const skipped = serverStatus.skipped;
    // eslint-disable-next-line react-hooks/set-state-in-effect -- hydrate server-fetched onboarding status (useQuery result) into locally-mutable state, merging UI-only fields
    setState(prev => ({
      ...prev,
      welcomeWizardCompleted: completed,
      welcomeWizardSkipped: skipped,
      showWelcomeWizard: !completed && !skipped,
      currentStep: serverStatus.current_step ?? null,
    }));
  }, [serverStatus]);

  // Welcome wizard actions
  const completeWelcomeWizard = useCallback(() => {
    setState(prev => ({
      ...prev,
      welcomeWizardCompleted: true,
      welcomeWizardSkipped: false,
      showWelcomeWizard: false,
    }));
  }, []);

  const skipWelcomeWizard = useCallback(() => {
    setState(prev => ({
      ...prev,
      welcomeWizardSkipped: true,
      showWelcomeWizard: false,
    }));
  }, []);

  const resetWelcomeWizard = useCallback(() => {
    setState(prev => ({
      ...prev,
      welcomeWizardCompleted: false,
      welcomeWizardSkipped: false,
      showWelcomeWizard: true,
    }));
  }, []);

  // Tooltip actions
  const toggleTooltips = useCallback((show: boolean) => {
    setState(prev => ({
      ...prev,
      showTooltips: show,
    }));
  }, []);

  const dismissTooltip = useCallback((tooltipId: string) => {
    setState(prev => ({
      ...prev,
      dismissedTooltips: [...new Set([...prev.dismissedTooltips, tooltipId])],
    }));
  }, []);

  const resetTooltips = useCallback(() => {
    setState(prev => ({
      ...prev,
      dismissedTooltips: [],
      showTooltips: true,
    }));
  }, []);

  const isTooltipDismissed = useCallback((tooltipId: string) => {
    return state.dismissedTooltips.includes(tooltipId);
  }, [state.dismissedTooltips]);

  // Feature highlights actions
  const toggleFeatureHighlights = useCallback((show: boolean) => {
    setState(prev => ({
      ...prev,
      showFeatureHighlights: show,
    }));
  }, []);

  // Checklist actions
  const completeChecklistItem = useCallback((itemId: string) => {
    setState(prev => ({
      ...prev,
      checklistItems: prev.checklistItems.map(item =>
        item.id === itemId ? { ...item, completed: true } : item
      ),
    }));
  }, []);

  const dismissChecklist = useCallback(() => {
    setState(prev => ({
      ...prev,
      checklistDismissed: true,
    }));
  }, []);

  const resetChecklist = useCallback(() => {
    setState(prev => ({
      ...prev,
      checklistItems: DEFAULT_CHECKLIST_ITEMS.map(item => ({ ...item, completed: false })),
      checklistDismissed: false,
    }));
  }, []);

  // Full reset
  const resetAllOnboarding = useCallback(() => {
    const freshState: OnboardingState = {
      welcomeWizardCompleted: false,
      welcomeWizardSkipped: false,
      showWelcomeWizard: true,
      showTooltips: true,
      dismissedTooltips: [],
      showFeatureHighlights: true,
      checklistItems: DEFAULT_CHECKLIST_ITEMS.map(item => ({ ...item, completed: false })),
      checklistDismissed: false,
      onboardingVersion: ONBOARDING_VERSION,
      currentStep: null,
    };
    setState(freshState);
  }, []);

  // Determine if patron onboarding flow should be triggered:
  // Show on first login after account creation, or if patron has never completed onboarding.
  // Server hydration above keeps welcomeWizardCompleted/Skipped in sync with the DB.
  const shouldShowPatronOnboarding =
    isAuthenticated &&
    !!user &&
    !state.welcomeWizardCompleted &&
    !state.welcomeWizardSkipped &&
    !user.onboarding_completed_at &&
    isPatron;

  const value: OnboardingContextType = {
    ...state,
    completeWelcomeWizard,
    skipWelcomeWizard,
    resetWelcomeWizard,
    toggleTooltips,
    dismissTooltip,
    resetTooltips,
    isTooltipDismissed,
    toggleFeatureHighlights,
    completeChecklistItem,
    dismissChecklist,
    resetChecklist,
    resetAllOnboarding,
    shouldShowPatronOnboarding,
    isLoading: isHydrating && !serverStatus,
  };

  return (
    <OnboardingContext.Provider value={value}>
      {children}
    </OnboardingContext.Provider>
  );
}


export function useOnboarding(): OnboardingContextType {
  const context = useContext(OnboardingContext);
  if (!context) {
    throw new Error('useOnboarding must be used within an OnboardingProvider');
  }
  return context;
}

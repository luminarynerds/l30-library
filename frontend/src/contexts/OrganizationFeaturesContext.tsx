/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { createContext, useContext, useState, useEffect, useCallback, useMemo, ReactNode } from 'react';
import { getOrganizationFeatures } from '../api/organization-features-api';
import type { OrganizationFeatures } from '../api/organization-features-api';
import { setJourneyTrackingEnabled } from '../api/journey-tracker-api';

// Re-export the canonical OrganizationFeatures type (defined in
// api/domains/operations/organization-features-api.ts) so existing
// `import { OrganizationFeatures } from '.../OrganizationFeaturesContext'`
// callsites keep working.
export type { AgeGroupLimitConfig, AgeGroupLimits, OrganizationFeatures } from '../api/organization-features-api';

interface OrganizationFeaturesContextType {
  features: OrganizationFeatures | null;
  loading: boolean;
  refetch: () => Promise<void>;
  isFeatureEnabled: (featureName: keyof OrganizationFeatures) => boolean;
}

const DEFAULT_FEATURES: OrganizationFeatures = {
  id: 1,
  gamification_enabled: true,
  reading_programs_enabled: true,
  board_features_enabled: true,
  training_modules_enabled: true,
  community_features_enabled: true,
  email_notifications_enabled: true,
  banned_books_tracking_enabled: true,
  patron_portal_enabled: true,
  self_checkout_enabled: true,
  acquisition_enabled: true,
  indie_platform_enabled: true,
  learning_platform_enabled: true,
  for_teachers_enabled: true,
  home_delivery_enabled: true,
  ai_tools_enabled: true,
  makerspace_enabled: true,
  meeting_rooms_enabled: true,
  events_enabled: true,
  ill_enabled: true,
  genealogy_enabled: true,
  free_ebooks_enabled: true,
  outreach_enabled: true,
  community_outcomes_enabled: true,
  ama_enabled: false,
  reading_shelf_enabled: true,
  reading_goals_enabled: false,
  shelf_data_export_enabled: true,
  saved_searches_enabled: false,
  reading_programs_booklist_enabled: false,
  reading_programs_paper_log_enabled: false,
  circulation_print_slip_enabled: true,
  circulation_hold_trap_card_enabled: true,
  customer_display_enabled: false,
  book_club_history_enabled: false,
  book_club_waitlist_enabled: false,
  pickup_authorization_enabled: false,
  cohort_enabled: false,
  aggregate_trending_enabled: true,
  front_desk_enabled: true,
  migration_enabled: true,
  legal_services_enabled: true,
  strategic_planning_enabled: true,
  literacy_programs_enabled: false,
  tech_services_enabled: true,
  emergency_services_enabled: true,
  compliance_enabled: true,
  volunteers_enabled: true,
  notifications_enabled: true,
  family_card_enabled: true,
  marketing_enabled: true,
  streaming_enabled: true,
  staff_scheduling_enabled: true,
  beta_features_enabled: false,
  storytime_enabled: true,
  digital_access_enabled: true,
  collection_management_enabled: true,
  patron_engagement_enabled: true,
  impact_measurement_enabled: false,
  staff_wellness_enabled: true,
  faq_chatbot_enabled: true,
  financial_reports_enabled: true,
  book_clubs_enabled: true,
  sip2_rfid_enabled: true,
  signage_enabled: true,
  printing_enabled: true,
  processing_queue_enabled: true,
  parent_onboarding_enabled: true,
  home_visit_safety_enabled: false,
  home_visit_day_plan_enabled: false,
  serials_enabled: true,
  enabled_focus_modes: [],
  enabled_themes: [],
  enabled_fonts: [],
  default_daily_goal_minutes: 30,
  max_holds_per_patron: 10,
  max_checkouts_per_patron: 5,
  configuration: null,
  age_group_limits: null,
  created_at: new Date().toISOString(),
  updated_at: null,
  updated_by_id: null,
};

const OrganizationFeaturesContext = createContext<OrganizationFeaturesContextType | undefined>(
  undefined
);

export function OrganizationFeaturesProvider({ children }: { children: ReactNode }) {
  const [features, setFeatures] = useState<OrganizationFeatures | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchFeatures = useCallback(async () => {
    try {
      setLoading(true);
      const response = await getOrganizationFeatures();
      setFeatures({ ...DEFAULT_FEATURES, ...response });
    } catch (_err) {
      if (import.meta.env.DEV) {
        Sentry.captureException(_err instanceof Error ? _err : new Error(String(_err)));
      }
      setFeatures(DEFAULT_FEATURES);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchFeatures();
    // Re-fetch feature flags every 30s for live demo responsiveness
    const interval = setInterval(fetchFeatures, 30_000);
    return () => clearInterval(interval);
  }, [fetchFeatures]);

  // Sync the patron_engagement_enabled flag into the journey-tracker module
  // so sendJourneyEvent/sendJourneyEventBatch can no-op when the backend
  // journey_analytics router is gated off (avoids 404 noise).
  // Cast: imported OrganizationFeatures type is narrower than the local
  // re-declaration and the runtime payload; runtime always carries the flag.
  const patronEngagementEnabled =
    (features as { patron_engagement_enabled?: boolean } | null)?.patron_engagement_enabled;
  useEffect(() => {
    if (patronEngagementEnabled === undefined) return;
    setJourneyTrackingEnabled(patronEngagementEnabled);
  }, [patronEngagementEnabled]);

  const isFeatureEnabled = useCallback((featureName: keyof OrganizationFeatures): boolean => {
    if (features === null) return true; // Still loading, show content by default
    const value = features[featureName];
    return typeof value === 'boolean' ? value : false;
  }, [features]);

  const contextValue = useMemo(() => ({
    features,
    loading,
    refetch: fetchFeatures,
    isFeatureEnabled,
  }), [features, loading, fetchFeatures, isFeatureEnabled]);

  return (
    <OrganizationFeaturesContext.Provider value={contextValue}>
      {children}
    </OrganizationFeaturesContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useOrganizationFeatures() {
  const context = useContext(OrganizationFeaturesContext);
  if (!context) {
    throw new Error(
      'useOrganizationFeatures must be used within OrganizationFeaturesProvider'
    );
  }
  return context;
}

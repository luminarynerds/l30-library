/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Organization Features API Service
 * Handles API calls for organization-wide feature management
 */
import { fetchApi, isApiError } from '@/lib/api-client'
import { getAccessToken } from '@/utils/tokenStore'

// ==================== Types ====================
// Canonical OrganizationFeatures type. Mirrors the columns in the
// `organization_features` DB table and the backend
// `OrganizationFeaturesResponse` Pydantic schema (backend/app/schemas/organization_features.py).
// All non-metadata fields should also appear (optional) in OrganizationFeaturesUpdate below.

export interface AgeGroupLimitConfig {
  max_checkouts: number
  max_holds: number
  checkout_duration_days: number
}

export interface AgeGroupLimits {
  juvenile: AgeGroupLimitConfig
  teen: AgeGroupLimitConfig
  adult: AgeGroupLimitConfig
  senior: AgeGroupLimitConfig
}

export interface OrganizationFeatures {
  id: number

  // Boolean toggles -- core
  gamification_enabled: boolean
  reading_programs_enabled: boolean
  board_features_enabled: boolean
  training_modules_enabled: boolean
  community_features_enabled: boolean
  email_notifications_enabled: boolean
  banned_books_tracking_enabled: boolean
  patron_portal_enabled: boolean
  self_checkout_enabled: boolean

  // Boolean toggles -- previously-ungated modules
  acquisition_enabled: boolean
  indie_platform_enabled: boolean
  learning_platform_enabled: boolean
  for_teachers_enabled: boolean
  home_delivery_enabled: boolean
  ai_tools_enabled: boolean
  makerspace_enabled: boolean
  meeting_rooms_enabled: boolean
  events_enabled: boolean
  ill_enabled: boolean
  genealogy_enabled: boolean
  free_ebooks_enabled: boolean
  outreach_enabled: boolean

  // Boolean toggles -- additional coverage
  legal_services_enabled: boolean
  strategic_planning_enabled: boolean
  literacy_programs_enabled: boolean
  tech_services_enabled: boolean
  emergency_services_enabled: boolean
  compliance_enabled: boolean
  volunteers_enabled: boolean
  notifications_enabled: boolean
  family_card_enabled: boolean
  marketing_enabled: boolean
  streaming_enabled: boolean
  staff_scheduling_enabled: boolean
  beta_features_enabled: boolean
  storytime_enabled: boolean
  digital_access_enabled: boolean
  collection_management_enabled: boolean
  patron_engagement_enabled: boolean
  staff_wellness_enabled: boolean
  faq_chatbot_enabled: boolean
  financial_reports_enabled: boolean
  book_clubs_enabled: boolean
  sip2_rfid_enabled: boolean
  signage_enabled: boolean
  printing_enabled: boolean
  ama_enabled: boolean
  community_outcomes_enabled: boolean
  front_desk_enabled: boolean
  serials_enabled: boolean
  migration_enabled: boolean
  parent_onboarding_enabled: boolean
  processing_queue_enabled: boolean
  reading_goals_enabled: boolean
  reading_shelf_enabled: boolean
  shelf_data_export_enabled: boolean
  saved_searches_enabled: boolean
  reading_programs_booklist_enabled: boolean
  reading_programs_paper_log_enabled: boolean
  circulation_print_slip_enabled: boolean
  circulation_hold_trap_card_enabled: boolean
  customer_display_enabled: boolean
  book_club_history_enabled: boolean
  book_club_waitlist_enabled: boolean
  pickup_authorization_enabled: boolean
  cohort_enabled: boolean
  aggregate_trending_enabled: boolean
  impact_measurement_enabled: boolean

  home_visit_safety_enabled: boolean
  home_visit_day_plan_enabled: boolean
  // Array configurations
  enabled_focus_modes: string[]
  enabled_themes: string[]
  enabled_fonts: string[]

  // Numeric configurations
  default_daily_goal_minutes: number
  max_holds_per_patron: number
  max_checkouts_per_patron: number

  // Extensible configuration
  configuration: Record<string, unknown> | null

  // Per-age-group circulation limits
  age_group_limits: AgeGroupLimits | null

  // Metadata
  created_at: string
  updated_at: string | null
  updated_by_id: number | null
}

export interface OrganizationFeaturesUpdate {
  // Boolean toggles -- core
  gamification_enabled?: boolean
  reading_programs_enabled?: boolean
  board_features_enabled?: boolean
  training_modules_enabled?: boolean
  community_features_enabled?: boolean
  email_notifications_enabled?: boolean
  banned_books_tracking_enabled?: boolean
  patron_portal_enabled?: boolean
  self_checkout_enabled?: boolean

  // Boolean toggles -- previously-ungated modules
  acquisition_enabled?: boolean
  indie_platform_enabled?: boolean
  learning_platform_enabled?: boolean
  for_teachers_enabled?: boolean
  home_delivery_enabled?: boolean
  ai_tools_enabled?: boolean
  makerspace_enabled?: boolean
  meeting_rooms_enabled?: boolean
  events_enabled?: boolean
  ill_enabled?: boolean
  genealogy_enabled?: boolean
  free_ebooks_enabled?: boolean
  outreach_enabled?: boolean

  // Boolean toggles -- additional coverage
  legal_services_enabled?: boolean
  strategic_planning_enabled?: boolean
  literacy_programs_enabled?: boolean
  tech_services_enabled?: boolean
  emergency_services_enabled?: boolean
  compliance_enabled?: boolean
  volunteers_enabled?: boolean
  notifications_enabled?: boolean
  family_card_enabled?: boolean
  marketing_enabled?: boolean
  streaming_enabled?: boolean
  staff_scheduling_enabled?: boolean
  beta_features_enabled?: boolean
  storytime_enabled?: boolean
  digital_access_enabled?: boolean
  collection_management_enabled?: boolean
  patron_engagement_enabled?: boolean
  staff_wellness_enabled?: boolean
  faq_chatbot_enabled?: boolean
  financial_reports_enabled?: boolean
  book_clubs_enabled?: boolean
  sip2_rfid_enabled?: boolean
  signage_enabled?: boolean
  printing_enabled?: boolean
  ama_enabled?: boolean
  community_outcomes_enabled?: boolean
  front_desk_enabled?: boolean
  serials_enabled?: boolean
  migration_enabled?: boolean
  parent_onboarding_enabled?: boolean
  processing_queue_enabled?: boolean
  reading_goals_enabled?: boolean
  reading_shelf_enabled?: boolean
  shelf_data_export_enabled?: boolean
  saved_searches_enabled?: boolean
  reading_programs_booklist_enabled?: boolean
  reading_programs_paper_log_enabled?: boolean
  circulation_print_slip_enabled?: boolean
  circulation_hold_trap_card_enabled?: boolean
  customer_display_enabled?: boolean
  book_club_history_enabled?: boolean
  book_club_waitlist_enabled?: boolean
  pickup_authorization_enabled?: boolean
  cohort_enabled?: boolean
  aggregate_trending_enabled?: boolean
  impact_measurement_enabled?: boolean

  home_visit_safety_enabled?: boolean
  home_visit_day_plan_enabled?: boolean
  // Array configurations
  enabled_focus_modes?: string[]
  enabled_themes?: string[]
  enabled_fonts?: string[]

  // Numeric configurations
  default_daily_goal_minutes?: number
  max_holds_per_patron?: number
  max_checkouts_per_patron?: number

  // Extensible configuration
  configuration?: Record<string, unknown> | null

  // Per-age-group circulation limits
  age_group_limits?: AgeGroupLimits | null

  // Audit reason
  reason?: string
}

export interface FeatureCheckResponse {
  feature_name: string
  enabled: boolean
}

export interface FeatureRegistryEntry {
  key: string
  label: string
}

// ==================== Public Endpoints ====================

export async function getOrganizationFeatures(): Promise<OrganizationFeatures> {
  try {
    return await fetchApi<OrganizationFeatures>('/organization-features')
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to load organization features')
    }
    throw error
  }
}

export async function getFeatureRegistry(): Promise<FeatureRegistryEntry[]> {
  try {
    return await fetchApi<FeatureRegistryEntry[]>('/organization-features/registry')
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to load feature registry')
    }
    throw error
  }
}

export async function checkFeatureEnabled(featureName: string): Promise<FeatureCheckResponse> {
  try {
    return await fetchApi<FeatureCheckResponse>(`/organization-features/check/${encodeURIComponent(featureName)}`)
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to check feature status')
    }
    throw error
  }
}

// ==================== Admin Endpoints ====================

export async function applyFeaturePreset(
  preset: 'barebones' | 'full' | 'small_library'
): Promise<OrganizationFeatures> {
  const token = getAccessToken()
  try {
    return await fetchApi<OrganizationFeatures>(
      `/organization-features/presets/${preset}`,
      {
        method: 'POST',
        ...(token ? { token } : {}),
      }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to apply feature preset')
    }
    throw error
  }
}

export async function updateOrganizationFeatures(
  data: OrganizationFeaturesUpdate
): Promise<OrganizationFeatures> {
  const token = getAccessToken()
  try {
    return await fetchApi<OrganizationFeatures>('/organization-features', {
      method: 'PUT',
      ...(token ? { token } : {}),
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to update organization features')
    }
    throw error
  }
}

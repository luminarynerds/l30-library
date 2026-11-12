/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Patron Onboarding API
 *
 * Wraps the `/patrons/me/onboarding*` and related endpoints used by the
 * 5-step welcome flow (WelcomePage → PreferencesPage → BranchPage →
 * TourPage → CompletePage) plus AccountPage and OnboardingContext.
 *
 * Backed by backend/app/api/v1/patron_onboarding.py.
 */
import { api } from '@/lib/api-client'
import { API_BASE } from '@/api/types'

// ==================== Types ====================

export interface PatronOnboardingStatus {
  patron_id: number
  current_step: number
  step_welcome_completed: boolean
  step_preferences_completed: boolean
  step_branch_completed: boolean
  step_tour_completed: boolean
  step_complete_completed: boolean
  preferred_genres?: string[] | null
  preferred_formats?: string[] | null
  reading_goal?: string | null
  skipped: boolean
  completed_at?: string | null
  started_at: string
  home_branch_id?: number | null
  home_branch_name?: string | null
}

export interface PatronPreferencesPayload {
  preferred_genres: string[]
  preferred_formats: string[]
  reading_goal: 'casual' | 'regular' | 'avid'
}

// ==================== API ====================

const BASE = `${API_BASE}/patrons/me`

export const patronOnboardingApi = {
  /** Fetch the current patron's onboarding progress + preferences. */
  getStatus: (): Promise<PatronOnboardingStatus> =>
    api.get<PatronOnboardingStatus>(`${BASE}/onboarding-status`),

  /** Step 2: save preferred genres, formats, reading goal. */
  savePreferences: (data: PatronPreferencesPayload): Promise<PatronOnboardingStatus> =>
    api.patch<PatronOnboardingStatus>(`${BASE}/preferences`, data),

  /** Step 3: pick a home branch. */
  setHomeBranch: (branchId: number): Promise<PatronOnboardingStatus> =>
    api.patch<PatronOnboardingStatus>(`${BASE}/home-branch`, { branch_id: branchId }),

  /** Mark a step (1–5) as completed. */
  completeStep: (step: number): Promise<PatronOnboardingStatus> =>
    api.post<PatronOnboardingStatus>(`${BASE}/onboarding/step`, { step }),

  /** Skip the wizard from the given step. */
  skip: (currentStep: number): Promise<PatronOnboardingStatus> =>
    api.post<PatronOnboardingStatus>(`${BASE}/onboarding/skip`, { current_step: currentStep }),
}

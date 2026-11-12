/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { apiClient } from "@/lib/api-client"
import { getAccessToken } from "@/utils/tokenStore"

// The backend rejects unknown journey types with HTTP 400 (JOURNEY_TYPES in
// app/models/journey_instrumentation.py) — keep this union in sync with it.
export type JourneyType =
  | 'search_to_hold'
  | 'register'
  | 'renewal'
  | 'account_self_service'
  | 'staff_checkin'

export interface JourneyEventPayload {
  journey_type: JourneyType
  session_id: string
  stage_name: string
  event_sequence: number
  time_since_journey_start_ms: number
  time_since_previous_event_ms?: number
  properties?: Record<string, unknown>
  error_code?: string
}

// Module-level snapshot of the patron_engagement_enabled feature flag.
// Defaults to true to match DEFAULT_FEATURES and OrganizationFeaturesContext's
// loading-state behavior (isFeatureEnabled returns true while features === null).
// OrganizationFeaturesProvider calls setJourneyTrackingEnabled() to keep this
// in sync after each features fetch (initial + 30s refresh interval).
// When false, sendJourneyEvent/sendJourneyEventBatch are no-ops — avoids 404
// noise because the backend mounts the journey_analytics router behind
// require_patron_engagement_enabled.
let journeyTrackingEnabled = true

export function setJourneyTrackingEnabled(enabled: boolean): void {
  journeyTrackingEnabled = enabled
}

export async function sendJourneyEvent(
  event: JourneyEventPayload,
  opts?: { isNewUser?: boolean; accessibilityMode?: boolean }
): Promise<void> {
  if (!journeyTrackingEnabled) return
  const token = getAccessToken()
  const headers: Record<string, string> = {}
  if (opts?.isNewUser) headers["x-new-user"] = "true"
  if (opts?.accessibilityMode) headers["x-accessibility-mode"] = "true"

  await apiClient("/analytics/journeys/events", {
    method: "POST",
    body: event,
    headers,
    ...(token ? { token } : {}),
  })
}

export async function sendJourneyEventBatch(
  events: JourneyEventPayload[],
  opts?: { isNewUser?: boolean; accessibilityMode?: boolean }
): Promise<void> {
  if (!journeyTrackingEnabled) return
  const token = getAccessToken()
  const headers: Record<string, string> = {}
  if (opts?.isNewUser) headers["x-new-user"] = "true"
  if (opts?.accessibilityMode) headers["x-accessibility-mode"] = "true"

  await apiClient("/analytics/journeys/events/batch", {
    method: "POST",
    body: { events },
    headers,
    ...(token ? { token } : {}),
  })
}

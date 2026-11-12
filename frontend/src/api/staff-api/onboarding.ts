/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { fetchApi } from '@/lib/api-client'

// ==================== Onboarding Types ====================

export interface CheckInPeriod {
  key: string
  label: string
  days_offset?: number | null
}

export interface FeedbackType {
  key: string
  label: string
}

// ==================== Onboarding Service Functions ====================

export async function getCheckInPeriods(token: string): Promise<CheckInPeriod[]> {
  try {
    return await fetchApi<CheckInPeriod[]>('/onboarding/config/periods', {
      token,
    })
  } catch (error) {
    Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
    return [] // Graceful fallback to empty array
  }
}

export async function getFeedbackTypes(token: string): Promise<FeedbackType[]> {
  try {
    return await fetchApi<FeedbackType[]>('/onboarding/config/feedback-types', {
      token,
    })
  } catch (error) {
    Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
    return [] // Graceful fallback to empty array
  }
}

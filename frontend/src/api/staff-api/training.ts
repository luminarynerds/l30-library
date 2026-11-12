/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { fetchApi } from '@/lib/api-client'

// ==================== Training Types ====================

export interface TrainingModule {
  id: number
  title: string
  duration_minutes: number
  category?: string | null
}

// ==================== Training Service Functions ====================

export async function getTrainingModules(token: string): Promise<TrainingModule[]> {
  try {
    return await fetchApi<TrainingModule[]>('/staff/training/modules', {
      token,
    })
  } catch (error) {
    Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
    return [] // Graceful fallback to empty array
  }
}

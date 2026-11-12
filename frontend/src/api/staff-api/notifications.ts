/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { fetchApi } from '@/lib/api-client'

// ==================== Notifications Types ====================

export interface NotificationTemplate {
  id: string
  name: string
  subject: string
  message: string
  notification_types: string[]
}

export interface ChecklistCategory {
  key: string
  label: string
}

export interface LostItemClassification {
  value: string
  label: string
  description: string
}

// ==================== Notifications Service Functions ====================

export async function getNotificationTemplates(token: string): Promise<NotificationTemplate[]> {
  try {
    return await fetchApi<NotificationTemplate[]>('/notifications/templates', {
      token,
    })
  } catch (error) {
    Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
    return [] // Graceful fallback to empty array
  }
}

export async function getChecklistCategories(token: string): Promise<ChecklistCategory[]> {
  try {
    return await fetchApi<ChecklistCategory[]>('/onboarding/config/checklist-categories', {
      token,
    })
  } catch (error) {
    Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
    return [] // Graceful fallback to empty array
  }
}

export async function getLostItemClassifications(token: string): Promise<LostItemClassification[]> {
  try {
    return await fetchApi<LostItemClassification[]>('/staff/lost-damaged/config/loss-classifications', {
      token,
    })
  } catch (error) {
    Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
    return [] // Graceful fallback to empty array
  }
}

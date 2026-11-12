/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { fetchApi } from '@/api/fetchApi'

// ==================== Types ====================

export interface VolunteerRoleOption {
  key: string
  label: string
  description: string
}

export interface SkillLevelOption {
  key: string
  label: string
  description: string
}

// ==================== Service Functions ====================

export async function getVolunteerRoles(token?: string): Promise<VolunteerRoleOption[]> {
  try {
    const result = await fetchApi('/volunteers/config/roles', {
      ...(token && { headers: { Authorization: `Bearer ${token}` } }),
    })
    return result || []
  } catch (error) {
    Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
    return [] // Graceful fallback to empty array
  }
}

export async function getSkillLevels(token?: string): Promise<SkillLevelOption[]> {
  try {
    const result = await fetchApi('/volunteers/config/skill-levels', {
      ...(token && { headers: { Authorization: `Bearer ${token}` } }),
    })
    return result || []
  } catch (error) {
    Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
    return [] // Graceful fallback to empty array
  }
}

/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi, isApiError } from '@/lib/api-client'
import { getAccessToken } from '@/utils/tokenStore'
import type { components } from '@/api/generated/schema';
import type { AlertSoundPreset } from '@/hooks/useAlertAudio'

// ==================== Panic Alert Types ====================

export type PanicAlertSource =
  | 'keyboard_shortcut'
  | 'physical_button'
  | 'mobile_gesture'
  | 'hidden_ui_button'

export type PanicAlertStatus = components['schemas']['PanicAlertStatus'];
export interface PanicAlertCreate {
  activation_source: PanicAlertSource
  situation_notes?: string
  metadata?: Record<string, unknown>
}

export interface PanicAlert {
  id: number
  triggered_by_user_id: number
  branch_id: number | null
  activation_source: PanicAlertSource
  status: PanicAlertStatus
  situation_notes: string | null
  acknowledged_by_user_id: number | null
  acknowledged_at: string | null
  resolution_notes: string | null
  resolved_at: string | null
  metadata: Record<string, unknown> | null
  created_at: string
  updated_at: string | null
}

export interface PanicAlertList {
  id: number
  triggered_by_user_id: number
  branch_id: number | null
  activation_source: PanicAlertSource
  status: PanicAlertStatus
  created_at: string
}

export interface PanicAlertNotificationPreferences {
  id: number
  user_id: number
  receive_panic_alerts: boolean
  notify_via_email: boolean
  notify_via_sms: boolean
  notify_via_in_app: boolean
  notify_for_all_branches: boolean
  branch_ids: number[] | null
  sound_enabled: boolean
  sound_preference: AlertSoundPreset
  vibration_enabled: boolean
  created_at: string
  updated_at: string | null
}

export interface PanicAlertNotificationPreferencesCreate {
  receive_panic_alerts?: boolean
  notify_via_email?: boolean
  notify_via_sms?: boolean
  notify_via_in_app?: boolean
  notify_for_all_branches?: boolean
  branch_ids?: number[] | null
  sound_enabled?: boolean
  sound_preference?: AlertSoundPreset
  vibration_enabled?: boolean
}

// ==================== Panic Alert Functions ====================

export async function triggerPanicAlert(
  data: PanicAlertCreate,
): Promise<PanicAlert> {
  try {
    return await fetchApi<PanicAlert>('/panic-alerts', {
      method: 'POST',
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to trigger panic alert')
    }
    throw error
  }
}

export async function getPanicAlert(alertId: number): Promise<PanicAlert> {
  try {
    return await fetchApi<PanicAlert>(`/panic-alerts/${alertId}`, {
      method: 'GET',
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch panic alert')
    }
    throw error
  }
}

export async function getActivePanicAlerts(
  branchId?: number,
  limit: number = 100,
): Promise<PanicAlertList[]> {
  try {
    const params = new URLSearchParams()
    if (branchId !== undefined) params.append('branch_id', branchId.toString())
    params.append('limit', limit.toString())

    const queryString = params.toString()
    return await fetchApi<PanicAlertList[]>(
      `/panic-alerts${queryString ? `?${queryString}` : ''}`,
      {
        method: 'GET',
      },
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch active alerts')
    }
    throw error
  }
}

export async function getUserRecentPanicAlerts(
  hours: number = 24,
  limit: number = 50,
): Promise<PanicAlertList[]> {
  try {
    const params = new URLSearchParams()
    params.append('hours', hours.toString())
    params.append('limit', limit.toString())

    return await fetchApi<PanicAlertList[]>(
      `/panic-alerts/user/recent?${params.toString()}`,
      {
        method: 'GET',
      },
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch recent alerts')
    }
    throw error
  }
}

export async function acknowledgePanicAlert(alertId: number): Promise<PanicAlert> {
  try {
    return await fetchApi<PanicAlert>(`/panic-alerts/${alertId}/acknowledge`, {
      method: 'PATCH',
      body: {},
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to acknowledge alert')
    }
    throw error
  }
}

export async function resolvePanicAlert(
  alertId: number,
  resolutionNotes?: string,
): Promise<PanicAlert> {
  try {
    return await fetchApi<PanicAlert>(`/panic-alerts/${alertId}/resolve`, {
      method: 'PATCH',
      body: {
        status: 'resolved',
        resolution_notes: resolutionNotes,
      },
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to resolve alert')
    }
    throw error
  }
}

// ==================== Statistics ====================

export type PanicAlertStats = components['schemas']['PanicAlertStatsResponse']

export interface PanicAlertStatsParams {
  startDate?: string
  endDate?: string
  branchId?: number
}

export async function getPanicAlertStats(
  params: PanicAlertStatsParams = {},
): Promise<PanicAlertStats> {
  const search = new URLSearchParams()
  if (params.startDate) search.append('start_date', params.startDate)
  if (params.endDate) search.append('end_date', params.endDate)
  if (params.branchId !== undefined) search.append('branch_id', params.branchId.toString())

  const queryString = search.toString()
  try {
    return await fetchApi<PanicAlertStats>(
      `/panic-alerts/stats/overview${queryString ? `?${queryString}` : ''}`,
      { method: 'GET' },
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch panic alert statistics')
    }
    throw error
  }
}

// ==================== Notification Preferences ====================

export async function getMyNotificationPreferences(): Promise<PanicAlertNotificationPreferences | null> {
  const token = getAccessToken()
  try {
    return await fetchApi<PanicAlertNotificationPreferences>(
      '/panic-alerts/preferences/me',
      {
        method: 'GET',
        ...(token ? { token } : {}),
      },
    )
  } catch (error: unknown) {
    if (isApiError(error) && (error.status === 404 || error.status === 403)) {
      // 404 = no preferences set; 403 = non-staff user (preferences are staff-only)
      return null
    }
    throw error
  }
}

export async function setMyNotificationPreferences(
  preferences: PanicAlertNotificationPreferencesCreate,
): Promise<PanicAlertNotificationPreferences> {
  const token = getAccessToken()
  try {
    return await fetchApi<PanicAlertNotificationPreferences>(
      '/panic-alerts/preferences/me',
      {
        method: 'POST',
        body: preferences,
        ...(token ? { token } : {}),
      },
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to update notification preferences')
    }
    throw error
  }
}

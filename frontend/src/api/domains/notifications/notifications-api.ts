/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi, isApiError } from '@/lib/api-client'

// ==================== Notification Types ====================

export interface NotificationPreferences {
  user_id: number
  // Email notification preferences
  email_checkout_receipt: boolean
  email_due_date_reminder: boolean
  email_overdue_notice: boolean
  email_hold_ready: boolean
  email_hold_expiring: boolean
  email_hold_cancelled: boolean
  email_fine_notice: boolean
  due_date_reminder_days: number
  hold_expiring_reminder_days: number
  overdue_notice_intervals: number[]
  // SMS notification preferences
  sms_notifications_enabled: boolean
  sms_phone_number: string | null
  sms_phone_verified: boolean
  sms_checkout_receipt: boolean
  sms_due_date_reminder: boolean
  sms_overdue_notice: boolean
  sms_hold_ready: boolean
  sms_hold_expiring: boolean
  sms_hold_cancelled: boolean
  sms_fine_notice: boolean
  sms_event_reminder: boolean
  sms_due_date_reminder_days: number
  sms_event_reminder_hours: number
}

export interface UpdateNotificationPreferencesData {
  email_checkout_receipt?: boolean
  email_due_date_reminder?: boolean
  email_overdue_notice?: boolean
  email_hold_ready?: boolean
  email_hold_expiring?: boolean
  email_hold_cancelled?: boolean
  email_fine_notice?: boolean
  due_date_reminder_days?: number
  hold_expiring_reminder_days?: number
  overdue_notice_intervals?: number[]
  // SMS fields
  sms_notifications_enabled?: boolean
  sms_phone_number?: string
  sms_checkout_receipt?: boolean
  sms_due_date_reminder?: boolean
  sms_overdue_notice?: boolean
  sms_hold_ready?: boolean
  sms_hold_expiring?: boolean
  sms_hold_cancelled?: boolean
  sms_fine_notice?: boolean
  sms_event_reminder?: boolean
  sms_due_date_reminder_days?: number
  sms_event_reminder_hours?: number
}

// ==================== Notification Functions ====================

export async function getNotificationPreferences(token: string): Promise<NotificationPreferences> {
  try {
    return await fetchApi<NotificationPreferences>('/notifications/preferences', { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to get notification preferences')
    }
    throw error
  }
}

export async function updateNotificationPreferences(
  token: string,
  data: UpdateNotificationPreferencesData
): Promise<{ ok: boolean; message: string; preferences: NotificationPreferences }> {
  try {
    return await fetchApi<{ ok: boolean; message: string; preferences: NotificationPreferences }>('/notifications/preferences', {
      method: 'PUT',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to update notification preferences')
    }
    throw error
  }
}


// ==================== Notification CRUD ====================
// (Merged from notification-api.ts)

import { getAccessToken } from '@/utils/tokenStore'

function requireToken(): string {
  const token = getAccessToken()
  if (!token) {
    throw new Error('Authentication required')
  }
  return token
}

export const notificationAPI = {
  getNotifications: async () => {
    return fetchApi('/notifications/live', {
      method: 'GET',
      token: requireToken(),
    })
  },

  markAsRead: async (notificationId: string) => {
    return fetchApi(`/notifications/live/${notificationId}/read`, {
      method: 'POST',
      token: requireToken(),
    })
  },

  deleteNotification: async (notificationId: string) => {
    return fetchApi(`/notifications/live/${notificationId}`, {
      method: 'DELETE',
      token: requireToken(),
    })
  },

  // NOTE: no backend route exists for staff to send an ad-hoc notification
  // to a user (the /notifications router is a read/dismiss feed of
  // system-generated notifications only). Left pointed at the historical
  // (nonexistent) path — this function has no caller anywhere in the app,
  // it's unreachable scaffold. Needs a build/delete product decision, not a
  // mechanical repoint (see W8 report).
  sendNotification: async (userId: string, message: string, type: string) => {
    return fetchApi('/notifications', {
      method: 'POST',
      token: requireToken(),
      body: { user_id: userId, message, type },
    })
  },
}

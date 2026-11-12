/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * SMS Notification API
 *
 * Provides functions for:
 * - Phone verification (opt-in workflow)
 * - SMS notification preferences
 * - Do Not Disturb configuration
 * - Staff ad-hoc SMS sending
 * - SMS statistics and cost tracking
 * - Template management (admin)
 */

import { fetchApi, isApiError } from '@/lib/api-client'

// ==================== Enums ====================

export type SMSNotificationType =
  | 'checkout_receipt'
  | 'due_date_reminder'
  | 'overdue_notice'
  | 'hold_ready'
  | 'hold_expiring'
  | 'hold_cancelled'
  | 'fine_notice'
  | 'event_reminder'
  | 'verification'
  | 'ad_hoc'

export type SMSDeliveryStatus =
  | 'pending'
  | 'queued'
  | 'sending'
  | 'sent'
  | 'delivered'
  | 'failed'
  | 'undelivered'
  | 'cancelled'

// ==================== Request Types ====================

export interface PhoneVerificationRequest {
  phone_number: string
}

export interface VerifyCodeRequest {
  phone_number: string
  verification_code: string
}

export interface SMSPreferencesUpdate {
  sms_notifications_enabled?: boolean
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

export interface DNDHoursRequest {
  start_hour: number
  start_minute?: number
  end_hour: number
  end_minute?: number
  timezone?: string
  active_days?: number[]
  is_enabled?: boolean
}

export interface SendAdHocSMSRequest {
  patron_id: number
  message: string
}

export interface BulkSMSRequest {
  patron_ids: number[]
  message: string
}

export interface SMSTemplateUpdate {
  template_body: string
  max_chars?: number
  allow_multipart?: boolean
  max_segments?: number
  description?: string
  is_active?: boolean
}

// ==================== Response Types ====================

export interface PhoneVerificationResponse {
  ok: boolean
  message: string
  phone_number: string
  expires_in_minutes: number
}

export interface VerifyCodeResponse {
  ok: boolean
  message: string
  sms_enabled: boolean
}

export interface SMSPreferencesResponse {
  sms_notifications_enabled: boolean
  phone_number: string | null
  phone_verified: boolean
  phone_verified_at: string | null
  preferences: {
    checkout_receipt: boolean
    due_date_reminder: boolean
    overdue_notice: boolean
    hold_ready: boolean
    hold_expiring: boolean
    hold_cancelled: boolean
    fine_notice: boolean
    event_reminder: boolean
  }
  timing: {
    due_date_reminder_days: number
    event_reminder_hours: number
  }
  do_not_disturb: {
    enabled: boolean
    start_time: string | null
    end_time: string | null
    timezone: string | null
    active_days: number[] | null
  } | null
}

export interface SimpleResponse {
  ok: boolean
  message: string
}

export interface SendSMSResponse {
  ok: boolean
  message: string
  sms_id: number
  status: SMSDeliveryStatus
}

export interface BulkSMSResponse {
  ok: boolean
  sent: number
  failed: number
  skipped: number
  errors: Array<{ patron_id: number; error: string }>
}

export interface SMSQueueItem {
  id: number
  user_id: number
  recipient_phone: string
  notification_type: SMSNotificationType
  status: SMSDeliveryStatus
  message_preview: string
  segments: number
  scheduled_for: string | null
  sent_at: string | null
  retry_count: number
  created_at: string | null
}

export interface SMSQueueResponse {
  items: SMSQueueItem[]
  total: number
  skip: number
  limit: number
}

export interface SMSStatsByType {
  sent: number
  delivered: number
  failed: number
  segments: number
  cost_cents: number
}

export interface SMSStatsResponse {
  period: {
    year: number
    month: number
  }
  summary: {
    total_sent: number
    total_delivered: number
    total_failed: number
    total_segments: number
    total_cost_cents: number
    total_cost_dollars: number
    delivery_rate: number
  }
  by_notification_type: Record<SMSNotificationType, SMSStatsByType>
  subscribers: {
    sms_enabled: number
    opted_out: number
  }
}

export interface PatronSMSHistoryItem {
  id: number
  notification_type: SMSNotificationType
  status: SMSDeliveryStatus
  message_body: string
  segments: number
  sent_at: string | null
  delivered_at: string | null
  failure_reason: string | null
  cost_cents: number | null
  created_at: string | null
}

export interface PatronSMSHistoryResponse {
  patron_id: number
  stats: {
    total_sent: number
    total_delivered: number
    total_failed: number
  }
  messages: PatronSMSHistoryItem[]
}

export interface SMSTemplate {
  id: number
  notification_type: SMSNotificationType
  template_body: string
  max_chars: number
  allow_multipart: boolean
  max_segments: number
  description: string | null
  is_active: boolean
  updated_at: string | null
}

export interface SMSTemplatesResponse {
  templates: SMSTemplate[]
}

export interface SMSTemplateUpdateResponse {
  ok: boolean
  message: string
  template: {
    id: number
    notification_type: SMSNotificationType
    template_body: string
  }
}

export interface GlobalDNDConfig {
  start_time: string
  end_time: string
  timezone: string
  active_days: number[]
  is_enabled: boolean
}

export interface GlobalDNDResponse {
  is_configured: boolean
  config: GlobalDNDConfig | null
}

// ==================== Phone Verification Functions ====================

export async function initiatePhoneVerification(
  token: string,
  data: PhoneVerificationRequest
): Promise<PhoneVerificationResponse> {
  try {
    return await fetchApi<PhoneVerificationResponse>('/sms/verify/initiate', {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to initiate phone verification')
    }
    throw error
  }
}

export async function confirmPhoneVerification(
  token: string,
  data: VerifyCodeRequest
): Promise<VerifyCodeResponse> {
  try {
    return await fetchApi<VerifyCodeResponse>('/sms/verify/confirm', {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to verify phone')
    }
    throw error
  }
}

export async function resendVerificationCode(
  token: string,
  data: PhoneVerificationRequest
): Promise<PhoneVerificationResponse> {
  try {
    return await fetchApi<PhoneVerificationResponse>('/sms/verify/resend', {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to resend verification code')
    }
    throw error
  }
}

// ==================== SMS Preferences Functions ====================

export async function getSMSPreferences(token: string): Promise<SMSPreferencesResponse> {
  try {
    return await fetchApi<SMSPreferencesResponse>('/sms/preferences', { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to get SMS preferences')
    }
    throw error
  }
}

export async function updateSMSPreferences(
  token: string,
  data: SMSPreferencesUpdate
): Promise<SimpleResponse> {
  try {
    return await fetchApi<SimpleResponse>('/sms/preferences', {
      method: 'PUT',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to update SMS preferences')
    }
    throw error
  }
}

export async function removeVerifiedPhone(token: string): Promise<SimpleResponse> {
  try {
    return await fetchApi<SimpleResponse>('/sms/phone', {
      method: 'DELETE',
      token,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to remove phone number')
    }
    throw error
  }
}

// ==================== Do Not Disturb Functions ====================

export async function updateDNDHours(
  token: string,
  data: DNDHoursRequest
): Promise<SimpleResponse> {
  try {
    return await fetchApi<SimpleResponse>('/sms/dnd', {
      method: 'PUT',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to update Do Not Disturb hours')
    }
    throw error
  }
}

export async function disableDNDHours(token: string): Promise<SimpleResponse> {
  try {
    return await fetchApi<SimpleResponse>('/sms/dnd', {
      method: 'DELETE',
      token,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to disable Do Not Disturb')
    }
    throw error
  }
}

// ==================== Staff Functions ====================

export async function staffSendSMS(
  token: string,
  data: SendAdHocSMSRequest
): Promise<SendSMSResponse> {
  try {
    return await fetchApi<SendSMSResponse>('/sms/staff/send', {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to send SMS')
    }
    throw error
  }
}

export async function staffBulkSMS(
  token: string,
  data: BulkSMSRequest
): Promise<BulkSMSResponse> {
  try {
    return await fetchApi<BulkSMSResponse>('/sms/staff/bulk', {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to send bulk SMS')
    }
    throw error
  }
}

export async function getSMSQueue(
  token: string,
  options?: {
    status?: SMSDeliveryStatus
    notification_type?: SMSNotificationType
    skip?: number
    limit?: number
  }
): Promise<SMSQueueResponse> {
  try {
    const params = new URLSearchParams()
    if (options?.status) params.set('status', options.status)
    if (options?.notification_type) params.set('notification_type', options.notification_type)
    if (options?.skip !== undefined) params.set('skip', options.skip.toString())
    if (options?.limit !== undefined) params.set('limit', options.limit.toString())
    const queryString = params.toString() ? `?${params.toString()}` : ''
    return await fetchApi<SMSQueueResponse>(`/sms/staff/queue${queryString}`, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to get SMS queue')
    }
    throw error
  }
}

export async function getSMSStats(
  token: string,
  options?: {
    year?: number
    month?: number
  }
): Promise<SMSStatsResponse> {
  try {
    const params = new URLSearchParams()
    if (options?.year !== undefined) params.set('year', options.year.toString())
    if (options?.month !== undefined) params.set('month', options.month.toString())
    const queryString = params.toString() ? `?${params.toString()}` : ''
    return await fetchApi<SMSStatsResponse>(`/sms/staff/stats${queryString}`, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to get SMS statistics')
    }
    throw error
  }
}

export async function getPatronSMSHistory(
  token: string,
  patronId: number,
  options?: {
    skip?: number
    limit?: number
  }
): Promise<PatronSMSHistoryResponse> {
  try {
    const params = new URLSearchParams()
    if (options?.skip !== undefined) params.set('skip', options.skip.toString())
    if (options?.limit !== undefined) params.set('limit', options.limit.toString())
    const queryString = params.toString() ? `?${params.toString()}` : ''
    return await fetchApi<PatronSMSHistoryResponse>(
      `/sms/staff/patron/${patronId}/history${queryString}`,
      { token }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to get patron SMS history')
    }
    throw error
  }
}

// ==================== Admin Template Functions ====================

export async function getSMSTemplates(token: string): Promise<SMSTemplatesResponse> {
  try {
    return await fetchApi<SMSTemplatesResponse>('/sms/admin/templates', { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to get SMS templates')
    }
    throw error
  }
}

export async function updateSMSTemplate(
  token: string,
  notificationType: SMSNotificationType,
  data: SMSTemplateUpdate
): Promise<SMSTemplateUpdateResponse> {
  try {
    return await fetchApi<SMSTemplateUpdateResponse>(
      `/sms/admin/templates/${notificationType}`,
      {
        method: 'PUT',
        token,
        body: data,
      }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to update SMS template')
    }
    throw error
  }
}

// ==================== Admin Global DND Functions ====================

export async function getGlobalDND(token: string): Promise<GlobalDNDResponse> {
  try {
    return await fetchApi<GlobalDNDResponse>('/sms/admin/dnd/global', { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to get global DND configuration')
    }
    throw error
  }
}

export async function setGlobalDND(
  token: string,
  data: DNDHoursRequest
): Promise<SimpleResponse> {
  try {
    return await fetchApi<SimpleResponse>('/sms/admin/dnd/global', {
      method: 'PUT',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to set global DND configuration')
    }
    throw error
  }
}

// ==================== Helper Functions ====================

export function getSMSNotificationTypeLabel(type: SMSNotificationType): string {
  switch (type) {
    case 'checkout_receipt':
      return 'Checkout Receipt'
    case 'due_date_reminder':
      return 'Due Date Reminder'
    case 'overdue_notice':
      return 'Overdue Notice'
    case 'hold_ready':
      return 'Hold Ready'
    case 'hold_expiring':
      return 'Hold Expiring'
    case 'hold_cancelled':
      return 'Hold Cancelled'
    case 'fine_notice':
      return 'Fine Notice'
    case 'event_reminder':
      return 'Event Reminder'
    case 'verification':
      return 'Verification'
    case 'ad_hoc':
      return 'Ad Hoc Message'
    default:
      return type
  }
}

export function getSMSDeliveryStatusLabel(status: SMSDeliveryStatus): string {
  switch (status) {
    case 'pending':
      return 'Pending'
    case 'queued':
      return 'Queued'
    case 'sending':
      return 'Sending'
    case 'sent':
      return 'Sent'
    case 'delivered':
      return 'Delivered'
    case 'failed':
      return 'Failed'
    case 'undelivered':
      return 'Undelivered'
    case 'cancelled':
      return 'Cancelled'
    default:
      return status
  }
}

export function getSMSDeliveryStatusColor(status: SMSDeliveryStatus): string {
  switch (status) {
    case 'pending':
    case 'queued':
      return 'bg-earth-100 dark:bg-earth-800 text-earth-700 dark:text-earth-300'
    case 'sending':
      return 'bg-earth-100 dark:bg-earth-800/30 text-lsc-rose dark:text-lsc-rose-light'
    case 'sent':
      return 'bg-cyan-100 dark:bg-cyan-900/30 text-cyan-700 dark:text-cyan-400'
    case 'delivered':
      return 'bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-400'
    case 'failed':
    case 'undelivered':
      return 'bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-700 dark:text-status-danger-400'
    case 'cancelled':
      return 'bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-700 dark:text-status-warning-400'
    default:
      return 'bg-earth-100 dark:bg-earth-800 text-earth-700 dark:text-earth-300'
  }
}

export function getSMSNotificationTypes(): Array<{
  value: SMSNotificationType
  label: string
}> {
  return [
    { value: 'checkout_receipt', label: 'Checkout Receipt' },
    { value: 'due_date_reminder', label: 'Due Date Reminder' },
    { value: 'overdue_notice', label: 'Overdue Notice' },
    { value: 'hold_ready', label: 'Hold Ready' },
    { value: 'hold_expiring', label: 'Hold Expiring' },
    { value: 'hold_cancelled', label: 'Hold Cancelled' },
    { value: 'fine_notice', label: 'Fine Notice' },
    { value: 'event_reminder', label: 'Event Reminder' },
    { value: 'verification', label: 'Verification' },
    { value: 'ad_hoc', label: 'Ad Hoc Message' },
  ]
}

export function getDNDWeekdayLabels(): Array<{ value: number; label: string; short: string }> {
  return [
    { value: 0, label: 'Monday', short: 'Mon' },
    { value: 1, label: 'Tuesday', short: 'Tue' },
    { value: 2, label: 'Wednesday', short: 'Wed' },
    { value: 3, label: 'Thursday', short: 'Thu' },
    { value: 4, label: 'Friday', short: 'Fri' },
    { value: 5, label: 'Saturday', short: 'Sat' },
    { value: 6, label: 'Sunday', short: 'Sun' },
  ]
}

export function formatSMSCost(cents: number): string {
  return `$${(cents / 100).toFixed(2)}`
}

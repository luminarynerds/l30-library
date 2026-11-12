/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi } from '@/lib/api-client'

// ==================== Types ====================

export interface TwoFactorSetupResponse {
  secret: string
  qr_image: string
  message: string
}

export interface TwoFactorConfirmResponse {
  recovery_codes: string[]
  message: string
}

export interface TwoFactorLoginResponse {
  requires_2fa: boolean
  pending_token: string
  message: string
}

export interface RecoveryCodesCountResponse {
  total: number
  remaining: number
}

export interface RecoveryCodesResponse {
  recovery_codes: string[]
  message: string
}

export interface RecoveryEmailResponse {
  recovery_email: string | null
  verified: boolean
  message: string
}

export interface SecurityAlertPreferences {
  security_alert_new_login: boolean
  security_alert_changes: boolean
}

export interface SecurityActivityItem {
  action: string
  action_label: string
  timestamp: string
  ip_address: string | null
  device: string | null
  status: 'success' | 'failed' | 'blocked' | 'change'
}

export interface SecurityActivityResponse {
  items: SecurityActivityItem[]
  total: number
  page: number
  per_page: number
}

export interface SecurityOverview {
  totp_enabled: boolean
  totp_confirmed_at: string | null
  recovery_email_set: boolean
  recovery_email_verified: boolean
  recovery_codes_remaining: number
  recovery_codes_total: number
  security_alert_new_login: boolean
  security_alert_changes: boolean
  active_sessions_count: number
  known_devices_count: number
  has_stripe_connected: boolean
}

// ==================== 2FA ====================

export async function setup2FA(): Promise<TwoFactorSetupResponse> {
  return fetchApi('/account/security/2fa/setup', { method: 'POST' })
}

export async function confirm2FA(code: string): Promise<TwoFactorConfirmResponse> {
  return fetchApi('/account/security/2fa/confirm', {
    method: 'POST',
    body: JSON.stringify({ code }),
  })
}

export async function disable2FA(password: string, code: string): Promise<{ message: string }> {
  return fetchApi('/account/security/2fa/disable', {
    method: 'POST',
    body: JSON.stringify({ password, code }),
  })
}

export async function verify2FALogin(
  pendingToken: string,
  code: string,
  trustDevice: boolean = false,
  turnstileToken?: string,
): Promise<{ access_token: string; token_type: string }> {
  return fetchApi('/account/security/2fa/verify', {
    method: 'POST',
    body: JSON.stringify({
      pending_token: pendingToken,
      code,
      trust_device: trustDevice,
      turnstile_token: turnstileToken,
    }),
  })
}

export async function verify2FARecovery(
  pendingToken: string,
  recoveryCode: string,
  turnstileToken?: string,
): Promise<{ access_token: string; recovery_codes_remaining: number }> {
  return fetchApi('/account/security/2fa/recovery', {
    method: 'POST',
    body: JSON.stringify({
      pending_token: pendingToken,
      recovery_code: recoveryCode,
      turnstile_token: turnstileToken,
    }),
  })
}

// ==================== Recovery Codes ====================

export async function getRecoveryCodesCount(): Promise<RecoveryCodesCountResponse> {
  return fetchApi('/account/security/recovery-codes/count')
}

export async function regenerateRecoveryCodes(
  password: string,
  code: string
): Promise<RecoveryCodesResponse> {
  return fetchApi('/account/security/recovery-codes/regenerate', {
    method: 'POST',
    body: JSON.stringify({ password, code }),
  })
}

// ==================== Recovery Email ====================

export async function setRecoveryEmail(email: string): Promise<RecoveryEmailResponse> {
  return fetchApi('/account/security/recovery-email', {
    method: 'POST',
    body: JSON.stringify({ email }),
  })
}

export async function verifyRecoveryEmail(token: string): Promise<RecoveryEmailResponse> {
  return fetchApi('/account/security/recovery-email/verify', {
    method: 'POST',
    body: JSON.stringify({ token }),
  })
}

export async function removeRecoveryEmail(): Promise<{ message: string }> {
  return fetchApi('/account/security/recovery-email', { method: 'DELETE' })
}

// ==================== Alert Preferences ====================

export async function getSecurityAlertPreferences(): Promise<SecurityAlertPreferences> {
  return fetchApi('/account/security/alert-preferences')
}

export async function updateSecurityAlertPreferences(
  prefs: SecurityAlertPreferences
): Promise<SecurityAlertPreferences> {
  return fetchApi('/account/security/alert-preferences', {
    method: 'PUT',
    body: JSON.stringify(prefs),
  })
}

// ==================== Security Activity ====================

export async function getSecurityActivity(
  page: number = 1,
  perPage: number = 20
): Promise<SecurityActivityResponse> {
  return fetchApi(`/account/security/activity?page=${page}&per_page=${perPage}`)
}

// ==================== Security Overview ====================

export async function getSecurityOverview(): Promise<SecurityOverview> {
  return fetchApi('/account/security/overview')
}

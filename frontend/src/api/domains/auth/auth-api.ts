/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi, isApiError } from '@/lib/api-client'
import { AuthError } from '@/utils/authErrors'
import { AUTH_CONFIG } from '@/constants/authConfig'
import { MessageResponse } from '@/api/types'

// ==================== Auth Types ====================

export interface IndieAuthorInfo {
  id: number
  pen_name: string
}

export interface User {
  id: number
  email: string
  first_name: string
  last_name: string
  full_name?: string
  role: 'super_admin' | 'admin' | 'director' | 'legal' | 'library_admin' | 'staff' | 'teacher' | 'patron' | 'child' | 'bookmobile' | 'homebond'
  is_active: boolean
  library_card: string | null
  phone: string | null
  address: string | null
  pronouns: string | null
  email_verified: boolean
  track_reading_history: boolean
  aggregate_recommendations_opt_out?: boolean
  created_at: string
  onboarding_completed_at: string | null
  onboarding_skipped: boolean
  home_branch_id: number | null
  school_id?: number | null
  ui_mode?: 'full' | 'essentials'
  profile_image?: string | null
  preferred_language?: string
  patron_status?: string
  card_expires_at?: string | null
  last_login_at?: string
  indie_author?: IndieAuthorInfo | null
  card_type?: 'temporary' | 'full' | null
  card_trial_expires_at?: string | null
  is_board_member?: boolean
}

export interface RegisterData {
  email: string
  password: string
  first_name: string
  last_name: string
  full_name?: string
  phone?: string
  address?: string
  turnstile_token?: string
}

export interface UpdateProfileData {
  first_name?: string
  last_name?: string
  phone?: string
  address?: string
  pronouns?: string
  track_reading_history?: boolean
  aggregate_recommendations_opt_out?: boolean
}

export interface TokenResponse {
  access_token: string
  token_type: string
  // refresh_token is now stored in httpOnly cookie, not returned in body
  requires_2fa?: boolean
  pending_token?: string
}

export interface RefreshTokenResponse {
  access_token: string
  token_type: string
}

export interface Session {
  id: number
  device_info: string | null
  ip_address: string | null
  created_at: string
  last_active_at: string | null
  is_current: boolean
}

export interface RevokeAllSessionsResponse {
  message: string
  revoked_count: number
}

// ==================== Auth Functions ====================

export async function login(
  email: string,
  password: string,
  turnstileToken?: string,
): Promise<TokenResponse> {
  try {
    return await fetchApi<TokenResponse>('/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password, turnstile_token: turnstileToken }),
    })
  } catch (error: unknown) {
    // Patron-facing copy from AUTH_CONFIG (b8e47395e); 423 prefers the backend
    // detail because it carries the configured lockout duration.
    if (isApiError(error)) {
      if (error.status === 423) throw new AuthError(error.detail || AUTH_CONFIG.ERROR_MESSAGES.ACCOUNT_LOCKED, 423, false)
      if (error.status === 429) throw new AuthError(AUTH_CONFIG.ERROR_MESSAGES.RATE_LIMITED, 429, true)
      if (error.status === 401) throw new AuthError(AUTH_CONFIG.ERROR_MESSAGES.INVALID_CREDENTIALS, 401, false)
      if (error.status >= 500) throw new AuthError(AUTH_CONFIG.ERROR_MESSAGES.SERVER_ERROR, error.status, true)
      throw new AuthError(error.detail || AUTH_CONFIG.ERROR_MESSAGES.GENERIC_LOGIN_FAILED, error.status, false)
    }
    if (error instanceof TypeError) {
      throw new AuthError(AUTH_CONFIG.ERROR_MESSAGES.NETWORK_ERROR, undefined, true)
    }
    throw new AuthError(AUTH_CONFIG.ERROR_MESSAGES.GENERIC_LOGIN_FAILED, undefined, false)
  }
}

export async function register(data: RegisterData): Promise<User> {
  try {
    return await fetchApi<User>('/auth/register', {
      method: 'POST',
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new AuthError(error.detail || AUTH_CONFIG.ERROR_MESSAGES.GENERIC_REGISTER_FAILED, error.status, false)
    }
    if (error instanceof TypeError) {
      throw new AuthError(AUTH_CONFIG.ERROR_MESSAGES.NETWORK_ERROR, undefined, true)
    }
    throw new AuthError(AUTH_CONFIG.ERROR_MESSAGES.GENERIC_REGISTER_FAILED, undefined, false)
  }
}

export async function logout(token: string): Promise<void> {
  // Refresh token is sent automatically via httpOnly cookie
  await fetchApi('/auth/logout', {
    method: 'POST',
    token,
    skipJsonParse: true,
  })
}

export async function refreshAccessToken(): Promise<RefreshTokenResponse> {
  // Refresh token is sent automatically via httpOnly cookie
  try {
    return await fetchApi<RefreshTokenResponse>('/auth/refresh', {
      method: 'POST',
    })
  } catch {
    throw new Error('Failed to refresh token')
  }
}

export async function forgotPassword(email: string, turnstileToken?: string): Promise<MessageResponse> {
  try {
    return await fetchApi<MessageResponse>('/auth/forgot-password', {
      method: 'POST',
      body: { email, turnstile_token: turnstileToken },
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to send reset email')
    }
    throw error
  }
}

export async function resetPassword(token: string, newPassword: string): Promise<MessageResponse> {
  try {
    return await fetchApi<MessageResponse>('/auth/reset-password', {
      method: 'POST',
      body: { token, new_password: newPassword },
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to reset password')
    }
    throw error
  }
}

export async function acceptInvite(token: string, newPassword: string): Promise<MessageResponse> {
  try {
    return await fetchApi<MessageResponse>('/auth/accept-invite', {
      method: 'POST',
      body: { token, new_password: newPassword },
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to activate account')
    }
    throw error
  }
}

export async function verifyEmail(token: string): Promise<MessageResponse> {
  try {
    return await fetchApi<MessageResponse>('/auth/verify-email', {
      method: 'POST',
      body: { token },
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to verify email')
    }
    throw error
  }
}

export async function resendVerification(email: string, turnstileToken?: string): Promise<MessageResponse> {
  try {
    return await fetchApi<MessageResponse>('/auth/resend-verification', {
      method: 'POST',
      body: { email, turnstile_token: turnstileToken },
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to resend verification')
    }
    throw error
  }
}

export async function requestMagicLink(email: string, turnstileToken?: string): Promise<MessageResponse> {
  try {
    return await fetchApi<MessageResponse>('/auth/magic-link', {
      method: 'POST',
      body: { email, turnstile_token: turnstileToken },
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to send magic link')
    }
    throw error
  }
}

export async function verifyMagicLink(token: string): Promise<TokenResponse> {
  try {
    return await fetchApi<TokenResponse>('/auth/magic-link/verify', {
      method: 'POST',
      body: { token },
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      // Same warm-copy mapping as login() (b8e47395e) — 423 prefers the
      // backend detail because it carries the configured lockout duration.
      if (error.status === 423) throw new AuthError(error.detail || AUTH_CONFIG.ERROR_MESSAGES.ACCOUNT_LOCKED, 423, false)
      if (error.status === 401) throw new Error(error.detail || 'Invalid or expired magic link')
      throw new Error(error.detail || 'Magic link verification failed')
    }
    throw error
  }
}

export async function changePassword(token: string, currentPassword: string, newPassword: string): Promise<MessageResponse> {
  try {
    return await fetchApi<MessageResponse>('/auth/change-password', {
      method: 'POST',
      token,
      body: { current_password: currentPassword, new_password: newPassword },
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to change password')
    }
    throw error
  }
}

export async function getSessions(token: string): Promise<{ sessions: Session[] }> {
  try {
    return await fetchApi<{ sessions: Session[] }>('/auth/sessions', { token })
  } catch {
    throw new Error('Failed to get sessions')
  }
}

export async function revokeSession(token: string, sessionId: number): Promise<MessageResponse> {
  try {
    return await fetchApi<MessageResponse>(`/auth/sessions/${sessionId}`, {
      method: 'DELETE',
      token,
    })
  } catch {
    throw new Error('Failed to revoke session')
  }
}

export async function revokeAllOtherSessions(token: string): Promise<RevokeAllSessionsResponse> {
  try {
    return await fetchApi<RevokeAllSessionsResponse>('/auth/sessions/revoke-all-others', {
      method: 'POST',
      token,
    })
  } catch {
    throw new Error('Failed to revoke sessions')
  }
}

export async function getMe(token: string): Promise<User> {
  try {
    return await fetchApi<User>('/auth/me', { token })
  } catch {
    throw new Error('Failed to get user profile')
  }
}

export async function updateMe(token: string, data: UpdateProfileData): Promise<User> {
  try {
    return await fetchApi<User>('/auth/me', {
      method: 'PUT',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Update failed')
    }
    throw error
  }
}

export async function checkDuplicate(email?: string, phone?: string): Promise<MessageResponse> {
  try {
    const params = new URLSearchParams()
    if (email) params.append('email', email)
    if (phone) params.append('phone', phone)

    return await fetchApi<MessageResponse>(`/auth/check-duplicate?${params.toString()}`, {
      method: 'POST',
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Duplicate check failed')
    }
    throw error
  }
}

export async function saveRegistrationPreferences(
  token: string,
  cardDelivery?: string,
  autoEnrollSummerReading: boolean = true
): Promise<MessageResponse> {
  try {
    const params = new URLSearchParams()
    if (cardDelivery) params.append('card_delivery', cardDelivery)
    params.append('auto_enroll_summer_reading', String(autoEnrollSummerReading))

    return await fetchApi<MessageResponse>(`/auth/registration-preferences?${params.toString()}`, {
      method: 'POST',
      token,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to save preferences')
    }
    throw error
  }
}

export interface AddressSuggestion {
  address: string
  city?: string
  state?: string
  zip_code?: string
}

export async function getAddressSuggestions(partial: string): Promise<{ suggestions: AddressSuggestion[] }> {
  try {
    const params = new URLSearchParams()
    params.append('partial', partial)

    return await fetchApi<{ suggestions: AddressSuggestion[] }>(`/auth/address-suggestions?${params.toString()}`, {
      method: 'GET',
    })
  } catch (_error: unknown) {
    // Silently fail for address suggestions - not critical
    return { suggestions: [] }
  }
}

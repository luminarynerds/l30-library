/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * In-memory token store for access tokens.
 *
 * This module provides a centralized way to store and retrieve access tokens
 * in memory only (not localStorage) for XSS protection.
 *
 * The AuthContext is responsible for setting/clearing the token.
 * API helpers can read the token without needing React context access.
 */

let accessToken: string | null = null

export function setAccessToken(token: string | null): void {
  accessToken = token
}

export function getAccessToken(): string | null {
  return accessToken
}

export function clearAccessToken(): void {
  accessToken = null
}

// Session hint — lightweight localStorage flag so we know whether to attempt
// a token refresh on page load.  The actual refresh token is an httpOnly cookie
// that JavaScript cannot read, so without this hint every anonymous page-load
// would fire a /auth/refresh request that returns 401 (console noise).
const SESSION_HINT_KEY = 'lsc_has_session'

export function setSessionHint(): void {
  try { localStorage.setItem(SESSION_HINT_KEY, '1') } catch { /* private browsing */ }
}

export function clearSessionHint(): void {
  try { localStorage.removeItem(SESSION_HINT_KEY) } catch { /* private browsing */ }
}

export function hasSessionHint(): boolean {
  try { return localStorage.getItem(SESSION_HINT_KEY) === '1' } catch { return false }
}

/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * API helper utilities for query string construction and error message extraction.
 * Re-exports common utilities used across API service files.
 */

import { getErrorMessage } from './api-client'

export function buildQueryString(params?: Record<string, unknown>): string {
  if (!params) return ''
  const searchParams = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null) {
      if (Array.isArray(value)) {
        for (const item of value) {
          searchParams.append(key, String(item))
        }
      } else {
        searchParams.set(key, String(value))
      }
    }
  }
  const qs = searchParams.toString()
  return qs ? `?${qs}` : ''
}

/**
 * Extract a human-readable error message from an unknown error value.
 * Alias for getErrorMessage from api-client.
 */
export const extractErrorMessage = getErrorMessage

/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { ApiError } from '../lib/api-client'

export function friendlyErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    const s = error.status
    if (s === 500 || s === 502 || s === 503 || s === 504) {
      return 'Something went wrong on our end. Please try again in a moment.'
    }
    if (s === 404) return 'This content could not be found.'
    if (s === 429) return "You're moving fast — give it a few seconds and try again."
    if (s === 401) return 'Please sign in to access this content.'
    if (s === 403) return 'You do not have permission to access this content.'
    if (s === 408) return 'The request timed out. Please try again.'
  }

  if (error instanceof Error) {
    const msg = error.message.toLowerCase()
    if (msg.includes('502') || msg.includes('bad gateway') ||
        msg.includes('503') || msg.includes('service unavailable') ||
        msg.includes('500') || msg.includes('internal server') ||
        msg.includes('504') || msg.includes('gateway timeout')) {
      return 'Something went wrong on our end. Please try again in a moment.'
    }
    if (msg.includes('404') || msg.includes('not found')) {
      return 'This content could not be found.'
    }
    if (msg.includes('429') || msg.includes('too many')) {
      return "You're moving fast — give it a few seconds and try again."
    }
    if (msg.includes('401') || msg.includes('unauthorized')) {
      return 'Please sign in to access this content.'
    }
    if (msg.includes('403') || msg.includes('forbidden')) {
      return 'You do not have permission to access this content.'
    }
    if (msg.includes('network') || msg.includes('fetch') || msg.includes('timeout') || msg.includes('aborted')) {
      return 'Could not connect to the server. Please check your connection and try again.'
    }
  }

  return 'An unexpected error occurred. Please try again.'
}

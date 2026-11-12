/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Authentication error handling utilities
 */

import { AUTH_CONFIG } from '../constants/authConfig'

export class AuthError extends Error {
  constructor(
    message: string,
    public code?: number,
    public isRetryable: boolean = false
  ) {
    super(message)
    this.name = 'AuthError'
  }
}

export function getAuthErrorMessage(error: unknown): {
  message: string
  isRetryable: boolean
  code?: number
} {
  // Handle AuthError specifically
  if (error instanceof AuthError) {
    const result: { message: string; isRetryable: boolean; code?: number } = {
      message: error.message,
      isRetryable: error.isRetryable,
    }
    if (error.code !== undefined) {
      result.code = error.code
    }
    return result
  }

  // Handle generic Error
  if (error instanceof Error) {
    return {
      message: error.message,
      isRetryable: false,
    }
  }

  // Handle object with message property
  if (error && typeof error === 'object' && 'message' in error) {
    const errorObj = error as { message: unknown }
    if (typeof errorObj.message === 'string') {
      return {
        message: errorObj.message,
        isRetryable: false,
      }
    }
  }

  // Default fallback
  return {
    message: AUTH_CONFIG.ERROR_MESSAGES.GENERIC_LOGIN_FAILED,
    isRetryable: false,
  }
}

export function getErrorMessageByCode(code: number | undefined): {
  message: string
  isRetryable: boolean
} {
  switch (code) {
    case AUTH_CONFIG.ERROR_CODES.RATE_LIMITED:
      return {
        message: AUTH_CONFIG.ERROR_MESSAGES.RATE_LIMITED,
        isRetryable: true,
      }
    case AUTH_CONFIG.ERROR_CODES.ACCOUNT_LOCKED:
      return {
        message: AUTH_CONFIG.ERROR_MESSAGES.ACCOUNT_LOCKED,
        isRetryable: false,
      }
    case AUTH_CONFIG.ERROR_CODES.INVALID_CREDENTIALS:
      return {
        message: AUTH_CONFIG.ERROR_MESSAGES.INVALID_CREDENTIALS,
        isRetryable: false,
      }
    case AUTH_CONFIG.ERROR_CODES.SERVER_ERROR:
      return {
        message: AUTH_CONFIG.ERROR_MESSAGES.SERVER_ERROR,
        isRetryable: true,
      }
    default:
      return {
        message: AUTH_CONFIG.ERROR_MESSAGES.GENERIC_LOGIN_FAILED,
        isRetryable: false,
      }
  }
}

export function normalizeAuthError(error: unknown): AuthError {
  if (error instanceof AuthError) {
    return error
  }

  const { message, isRetryable, code } = getAuthErrorMessage(error)
  return new AuthError(message, code, isRetryable)
}

/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/* eslint-disable no-constant-binary-expression */
import { getAccessToken, setAccessToken } from '../utils/tokenStore'

const API_BASE = import.meta.env.VITE_API_BASE || '/api/v1'

// 401 retry-with-refresh support.
// AuthContext registers its refresh function here to avoid circular imports.
type TokenRefresher = () => Promise<string | null>
let _tokenRefresher: TokenRefresher | null = null
let _refreshPromise: Promise<string | null> | null = null

export function setTokenRefresher(fn: TokenRefresher | null): void {
  _tokenRefresher = fn
}

const REFRESH_TIMEOUT_MS = 10_000

function doRefresh(): Promise<string | null> {
  if (!_tokenRefresher) return Promise.resolve(null)
  if (_refreshPromise) return _refreshPromise

  const timeout = new Promise<null>((resolve) =>
    setTimeout(() => resolve(null), REFRESH_TIMEOUT_MS)
  )
  _refreshPromise = Promise.race([_tokenRefresher(), timeout]).finally(() => {
    _refreshPromise = null
  })
  return _refreshPromise
}

export class ApiError extends Error {
  status: number
  detail: string
  // Raw parsed JSON body (when the response was JSON). Lets callers inspect
  // structured FastAPI detail dicts (e.g. 409 conflicts with `existing_card_number`)
  // without losing fields to the legacy stringified `detail`.
  body?: unknown
  isAuthError: boolean
  userMessage?: string
  details?: unknown[]

  constructor(message: string, status: number, detail: string, details?: unknown[], body?: unknown) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
    this.body = body
    this.isAuthError = status === 401 || status === 403
    this.userMessage = detail
    this.details = details
  }
}

export interface RequestOptions {
  method?: string
  params?: Record<string, unknown>
  body?: unknown
  headers?: Record<string, string>
  token?: string
  skipJsonParse?: boolean
  timeoutMs?: number
  signal?: AbortSignal
  responseType?: string
}

// Auth endpoints that should never trigger a retry-with-refresh (would cause loops)
const AUTH_PATHS = ['/auth/refresh', '/auth/login', '/auth/logout']

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export async function apiClient<T = any>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', params, body, headers = {}, token: explicitToken, skipJsonParse, signal } = options

  let url = `${API_BASE}${path}`
  if (params) {
    const searchParams = new URLSearchParams()
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        searchParams.append(key, String(value))
      }
    })
    const qs = searchParams.toString()
    if (qs) url += `?${qs}`
  }

  const serializedBody = body != null
    ? (typeof body === 'string' ? body : JSON.stringify(body))
    : undefined

  const token = explicitToken || getAccessToken()
  const res = await fetch(url, {
    method,
    credentials: 'include', // Required so httpOnly refresh token cookie is sent on /auth/refresh and /auth/logout
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...headers,
    },
    ...(serializedBody ? { body: serializedBody } : {}),
    ...(signal ? { signal } : {}),
  })

  // On 401, attempt a single token refresh and retry (unless this IS an auth endpoint)
  if (res.status === 401 && !explicitToken && !AUTH_PATHS.some(p => path.startsWith(p))) {
    const newToken = await doRefresh()
    if (newToken) {
      setAccessToken(newToken)
      const retryRes = await fetch(url, {
        method,
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${newToken}`,
          ...headers,
        },
        ...(serializedBody ? { body: serializedBody } : {}),
      })

      if (retryRes.ok) {
        if (skipJsonParse) return undefined as T
        if (retryRes.status === 204) return null as T
        return retryRes.json()
      }
      // Retry also failed — fall through to throw the retry's error
      return parseAndThrow(retryRes)
    }
  }

  if (!res.ok) {
    return parseAndThrow(res)
  }

  if (skipJsonParse) return undefined as T

  if (res.status === 204) return null as T

  return res.json()
}

async function parseAndThrow(res: Response): Promise<never> {
  let detail: string = res.statusText || 'Unknown error'
  let details: unknown[] | undefined
  let parsedBody: unknown = undefined

  try {
    // Try to parse as JSON first
    try {
      const errorBody = await res.json()
      parsedBody = errorBody
      // Support both FastAPI format ({detail: ...}) and app format ({error: {message: ...}})
      const rawDetail = errorBody.detail ?? errorBody.error?.message ?? errorBody.message
      if (typeof rawDetail === 'string') {
        detail = rawDetail
      } else if (Array.isArray(rawDetail)) {
        detail = rawDetail.map((d: { msg?: string }) => d.msg || JSON.stringify(d)).join('; ')
      } else if (rawDetail && typeof rawDetail === 'object') {
        // Structured detail (FastAPI allows dict in HTTPException(detail=...))
        // Prefer a human-readable `message` field; fall back to JSON so callers
        // never see "[object Object]".
        const obj = rawDetail as Record<string, unknown>
        if (typeof obj.message === 'string') {
          detail = obj.message
        } else {
          try {
            detail = JSON.stringify(rawDetail)
          } catch {
            detail = String(rawDetail)
          }
        }
      } else if (rawDetail) {
        detail = String(rawDetail)
      }
      // Preserve the structured `details` array (problem-resolution and
      // hold-override context blocks) so callers can act on it.
      if (Array.isArray(errorBody.details)) {
        details = errorBody.details
      }
    } catch (_parseError) {
      // If JSON parsing fails, try to get text content
      try {
        const textContent = await res.text()
        if (textContent && textContent.length > 0 && textContent.length < 500) {
          // Use text content if it's a reasonable error message (not HTML, etc.)
          if (!textContent.toLowerCase().includes('<!doctype') && !textContent.toLowerCase().includes('<html')) {
            detail = textContent
          }
        }
      } catch {
        // Fall back to statusText if all else fails
        detail = `${res.status} ${res.statusText}` || 'Request failed'
      }
    }
  } catch {
    // Absolute fallback
    detail = `${res.status} ${res.statusText}` || 'Request failed'
  }

  throw new ApiError(detail, res.status, detail, details, parsedBody)
}

// Alias used by most API modules
export const fetchApi = apiClient

// Convenience methods
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function get<T = any>(path: string, params?: Record<string, unknown>): Promise<T> {
  const opts: RequestOptions = { method: 'GET' }
  if (params) opts.params = params
  return apiClient<T>(path, opts)
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function post<T = any>(path: string, data?: unknown): Promise<T> {
  return apiClient<T>(path, { method: 'POST', body: data ? JSON.stringify(data) : undefined })
}

// Error utilities
export function isApiError(error: unknown): error is ApiError {
  return error instanceof ApiError
}

export function getErrorMessage(error: unknown, fallback?: string): string {
  if (error instanceof Error) return error.message
  if (fallback) return fallback
  return String(error)
}

export function getUserMessage(error: unknown, fallback: string): string {
  if (error instanceof Error && error.message.startsWith('API error:')) return fallback
  return fallback
}

// Drop-in replacement for the old api/client.ts object.
// Accepts full URLs (with API_BASE prefix) for backward compatibility.
function stripBase(url: string): string {
  if (url.startsWith(API_BASE)) return url.slice(API_BASE.length)
  return url
}

export const api = {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  async get<T = any>(url: string, options?: { params?: Record<string, unknown>; signal?: AbortSignal }): Promise<T> {
    const opts: RequestOptions = { method: 'GET' }
    if (options?.params) opts.params = options.params
    if (options?.signal) opts.signal = options.signal
    return apiClient<T>(stripBase(url), opts)
  },
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  async post<T = any>(url: string, data?: unknown): Promise<T> {
    return apiClient<T>(stripBase(url), { method: 'POST', body: data ? JSON.stringify(data) : undefined })
  },
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  async put<T = any>(url: string, data?: unknown): Promise<T> {
    return apiClient<T>(stripBase(url), { method: 'PUT', body: data ? JSON.stringify(data) : undefined })
  },
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  async patch<T = any>(url: string, data?: unknown): Promise<T> {
    return apiClient<T>(stripBase(url), { method: 'PATCH', body: data ? JSON.stringify(data) : undefined })
  },
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  async delete<T = any>(url: string): Promise<T> {
    return apiClient<T>(stripBase(url), { method: 'DELETE' })
  },
}

export default api

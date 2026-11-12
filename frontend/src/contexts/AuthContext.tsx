/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/* eslint-disable react-refresh/only-export-components */
import * as Sentry from "@/lib/sentry-lazy"
import { createContext, useContext, useState, useEffect, useCallback, useMemo, useRef, ReactNode } from 'react'
import toast from 'react-hot-toast'
import {
  User,
  login as apiLogin,
  register as apiRegister,
  logout as apiLogout,
  getMe,
  updateMe,
  refreshAccessToken,
  verifyMagicLink as apiVerifyMagicLink,
  RegisterData,
  UpdateProfileData
} from '../api/api'
import { setAccessToken, clearAccessToken, setSessionHint, clearSessionHint, hasSessionHint } from '../utils/tokenStore'
import { setTokenRefresher } from '../lib/api-client'
import SessionTimeoutWarning from '../components/SessionTimeoutWarning'

// Session event types for activity logging
export type SessionEventType =
  | 'session_start'
  | 'session_refresh'
  | 'session_extend'
  | 'session_warning_shown'
  | 'session_warning_dismissed'
  | 'session_timeout'
  | 'session_absolute_timeout'
  | 'session_logout'
  | 'session_activity_detected'

export interface SessionEvent {
  type: SessionEventType
  timestamp: Date
  userId?: string
  metadata?: Record<string, unknown>
}

interface TwoFactorRequired {
  requires_2fa: true
  pending_token: string
}

interface AuthContextType {
  user: User | null
  token: string | null
  accessToken?: string | null
  proxyUser?: User | null
  isLoading: boolean
  isAuthenticated: boolean
  sessionExpired: boolean
  sessionStartTime: Date | null
  login: (credential: string, secret: string, turnstileToken?: string) => Promise<TwoFactorRequired | void>
  loginWithMagicLink: (token: string) => Promise<void>
  completeLogin: (accessToken: string) => Promise<void>
  register: (data: RegisterData) => Promise<User>
  logout: () => Promise<void>
  updateProfile: (data: UpdateProfileData) => Promise<void>
  refreshUser: () => Promise<void>
  clearSessionExpired: () => void
  getSessionDuration: () => number | null
}

const AuthContext = createContext<AuthContextType | null>(null)

// Refresh token 5 minutes before it expires (access tokens are 15 min)
const REFRESH_INTERVAL_MS = 10 * 60 * 1000 // 10 minutes
const TIMEOUT_WARNING_MS = 2 * 60 * 1000 // Show warning 2 minutes before timeout (WCAG 2.2.1)
const IDLE_EVENTS = ['mousedown', 'keydown', 'scroll', 'touchstart', 'click'] as const
const ACTIVITY_THROTTLE_MS = 30 * 1000 // Throttle activity detection to every 30 seconds

// Absolute session timeout - forces logout regardless of activity (configurable, default 8 hours)
// Set to 0 or negative to disable absolute timeout
const DEFAULT_ABSOLUTE_TIMEOUT_HOURS = 8

export function parseAbsoluteSessionTimeoutMs(rawHours: string | undefined): number {
  if (!rawHours || rawHours.trim() === '') {
    return DEFAULT_ABSOLUTE_TIMEOUT_HOURS * 60 * 60 * 1000
  }

  const parsedHours = Number(rawHours)

  // Invalid values should not silently disable absolute timeout.
  if (!Number.isFinite(parsedHours)) {
    return DEFAULT_ABSOLUTE_TIMEOUT_HOURS * 60 * 60 * 1000
  }

  if (parsedHours <= 0) {
    return 0
  }

  return parsedHours * 60 * 60 * 1000
}

const ABSOLUTE_TIMEOUT_MS = parseAbsoluteSessionTimeoutMs(
  import.meta.env.VITE_ABSOLUTE_SESSION_TIMEOUT_HOURS
)

// Session activity logging - can be enabled for audit purposes
const SESSION_LOGGING_ENABLED = import.meta.env.VITE_SESSION_LOGGING_ENABLED === 'true'

// Session event log (in-memory, can be sent to backend periodically)
const sessionEventLog: SessionEvent[] = []
const MAX_LOG_SIZE = 100 // Keep last 100 events in memory

function logSessionEvent(
  type: SessionEventType,
  userId?: string,
  metadata?: Record<string, unknown>
): void {
  if (!SESSION_LOGGING_ENABLED && import.meta.env.PROD) return

  const event: SessionEvent = {
    type,
    timestamp: new Date(),
    ...(userId !== undefined ? { userId } : {}),
    ...(metadata !== undefined ? { metadata } : {}),
  }

  // Add to in-memory log
  sessionEventLog.push(event)

  // Trim log if it exceeds max size
  if (sessionEventLog.length > MAX_LOG_SIZE) {
    sessionEventLog.shift()
  }

  // Log to console in development
  if (import.meta.env.DEV) {
    console.log('[Session Event]', event.type, {
      timestamp: event.timestamp.toISOString(),
      userId: event.userId,
      ...event.metadata,
    })
  }

  // In production with logging enabled, could send to backend
  // This is left as a hook point for future implementation
  if (SESSION_LOGGING_ENABLED && import.meta.env.PROD) {
    // Could implement: sendSessionEventToBackend(event)
  }
}

export function getSessionEventLog(): readonly SessionEvent[] {
  return sessionEventLog
}

export function clearSessionEventLog(): void {
  sessionEventLog.length = 0
}

async function notifyServiceWorkerLogout(): Promise<void> {
  if (!('serviceWorker' in navigator)) {
    return
  }

  try {
    const registration = await navigator.serviceWorker.ready
    if (registration.active) {
      registration.active.postMessage({ type: 'USER_LOGOUT' })
      if (import.meta.env.DEV) {
        console.log('[Auth] Notified service worker to clear sensitive data')
      }
    }
  } catch (_error: unknown) {
    // Log but don't fail logout if service worker notification fails
    if (import.meta.env.DEV) {
      Sentry.captureMessage('[Auth] Failed to notify service worker:', 'warning')
    }
  }
}

export function AuthProvider({ children }: { children: ReactNode }): React.ReactElement {
  // Access token stored in memory only (not localStorage) for XSS protection
  // Refresh token is handled via httpOnly cookie by the browser
  const [user, setUser] = useState<User | null>(null)
  const [token, setToken] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [showTimeoutWarning, setShowTimeoutWarning] = useState(false)
  const [timeoutSeconds, setTimeoutSeconds] = useState(120) // 2 minutes
  const [sessionExpired, setSessionExpired] = useState(false)
  const [sessionStartTime, setSessionStartTime] = useState<Date | null>(null)
  const refreshTimerRef = useRef<number | null>(null)
  const timeoutWarningTimerRef = useRef<number | null>(null)
  const absoluteTimeoutTimerRef = useRef<number | null>(null)
  const lastActivityRef = useRef<number>(Date.now())
  const lastThrottledResetRef = useRef<number>(Date.now())
  const activityThrottleRef = useRef<number | null>(null)

  // Get session duration in milliseconds
  const getSessionDuration = useCallback((): number | null => {
    if (!sessionStartTime) return null
    return Date.now() - sessionStartTime.getTime()
  }, [sessionStartTime])

  const clearAuth = useCallback((wasSessionTimeout = false, wasAbsoluteTimeout = false) => {
    const currentUserId = user?.id

    setUser(null)
    setToken(null)
    setSessionStartTime(null)
    clearAccessToken() // Clear token from memory store
    clearSessionHint() // Remove session hint so future page loads skip refresh
    setShowTimeoutWarning(false)

    // SECURITY: Notify service worker to clear any cached sensitive data
    // This ensures no patron PII persists in browser storage after logout
    notifyServiceWorkerLogout()

    if (wasAbsoluteTimeout) {
      setSessionExpired(true)
      logSessionEvent('session_absolute_timeout', currentUserId?.toString(), {
        reason: 'Maximum session duration exceeded',
      })
      toast.error('Your session has reached its maximum duration. Please sign in again.', {
        duration: 5000,
        id: 'session-absolute-timeout',
      })
    } else if (wasSessionTimeout) {
      setSessionExpired(true)
      logSessionEvent('session_timeout', currentUserId?.toString(), {
        reason: 'Session expired due to inactivity',
      })
      toast.error('Your session has expired. Please sign in again.', {
        duration: 5000,
        id: 'session-expired',
      })
    }

    if (refreshTimerRef.current) {
      clearInterval(refreshTimerRef.current)
      refreshTimerRef.current = null
    }
    if (timeoutWarningTimerRef.current) {
      clearTimeout(timeoutWarningTimerRef.current)
      timeoutWarningTimerRef.current = null
    }
    if (absoluteTimeoutTimerRef.current) {
      clearTimeout(absoluteTimeoutTimerRef.current)
      absoluteTimeoutTimerRef.current = null
    }
    if (activityThrottleRef.current) {
      clearTimeout(activityThrottleRef.current)
      activityThrottleRef.current = null
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const doRefreshToken = useCallback(async (isSessionRefresh = false): Promise<string | null> => {
    // Refresh token is sent automatically via httpOnly cookie
    try {
      const response = await refreshAccessToken()
      const newToken = response.access_token
      setToken(newToken)
      setAccessToken(newToken) // Update token store for API helpers
      lastActivityRef.current = Date.now() // Reset activity on successful refresh

      if (isSessionRefresh) {
        logSessionEvent('session_refresh', user?.id?.toString(), {
          refreshedAt: new Date().toISOString(),
        })
      }

      return newToken
    } catch (error: unknown) {
      if (import.meta.env.DEV) {
        Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      }
      // Only show session expired message if this was an active session refresh,
      // not the initial page load check
      clearAuth(isSessionRefresh)
      return null
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clearAuth])

  // Register the token refresher with the API client so it can
  // transparently retry on 401 (closing the 10-15 min race window)
  useEffect(() => {
    setTokenRefresher(() => doRefreshToken(true))
    return () => setTokenRefresher(null)
  }, [doRefreshToken])

  const clearSessionExpired = useCallback(() => {
    setSessionExpired(false)
  }, [])

  const startRefreshTimer = useCallback(() => {
    // Clear any existing timers
    if (refreshTimerRef.current) {
      clearInterval(refreshTimerRef.current)
    }
    if (timeoutWarningTimerRef.current) {
      clearTimeout(timeoutWarningTimerRef.current)
    }
    if (absoluteTimeoutTimerRef.current) {
      clearTimeout(absoluteTimeoutTimerRef.current)
    }

    // Reset activity timestamp
    lastActivityRef.current = Date.now()

    // Set up periodic refresh - pass isSessionRefresh=true so timeout shows message
    refreshTimerRef.current = window.setInterval(() => {
      doRefreshToken(true)
    }, REFRESH_INTERVAL_MS)

    // Set up timeout warning (2 minutes before session expires)
    // Session expires after 15 minutes, so show warning at 13 minutes
    const warningDelay = REFRESH_INTERVAL_MS + (REFRESH_INTERVAL_MS / 2) - TIMEOUT_WARNING_MS
    timeoutWarningTimerRef.current = window.setTimeout(() => {
      logSessionEvent('session_warning_shown', user?.id?.toString())
      setShowTimeoutWarning(true)
      setTimeoutSeconds(120)
    }, warningDelay)

    // Set up absolute timeout if enabled (forces logout after max session duration)
    if (ABSOLUTE_TIMEOUT_MS > 0) {
      absoluteTimeoutTimerRef.current = window.setTimeout(() => {
        clearAuth(false, true) // wasSessionTimeout=false, wasAbsoluteTimeout=true
      }, ABSOLUTE_TIMEOUT_MS)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [doRefreshToken, clearAuth])

  // Reset timeout warning timer when user is active
  const resetWarningTimer = useCallback(() => {
    if (!user) return // Only track activity for authenticated users

    // Reset the warning timer if it exists
    if (timeoutWarningTimerRef.current) {
      clearTimeout(timeoutWarningTimerRef.current)

      // Set up a new warning timer from now
      const warningDelay = REFRESH_INTERVAL_MS + (REFRESH_INTERVAL_MS / 2) - TIMEOUT_WARNING_MS
      timeoutWarningTimerRef.current = window.setTimeout(() => {
        setShowTimeoutWarning(true)
        setTimeoutSeconds(120)
      }, warningDelay)
    }

    // Hide warning if currently shown and user is active
    setShowTimeoutWarning(false)

    lastActivityRef.current = Date.now()
  }, [user])

  // Idle detection - track user activity
  useEffect(() => {
    if (!user) return // Only track activity for authenticated users

    const handleActivity = () => {
      const now = Date.now()
      // Always record latest activity time so timeout checks are accurate
      lastActivityRef.current = now
      // Throttle the expensive timer reset to avoid excessive overhead
      if (now - (lastThrottledResetRef.current ?? 0) >= ACTIVITY_THROTTLE_MS) {
        lastThrottledResetRef.current = now
        resetWarningTimer()
      }
    }

    // Add event listeners for activity detection
    IDLE_EVENTS.forEach(event => {
      window.addEventListener(event, handleActivity, { passive: true })
    })

    return () => {
      IDLE_EVENTS.forEach(event => {
        window.removeEventListener(event, handleActivity)
      })
    }
  }, [user, resetWarningTimer])

  const handleExtendSession = useCallback(async () => {
    logSessionEvent('session_extend', user?.id?.toString(), {
      extendedAt: new Date().toISOString(),
    })
    setShowTimeoutWarning(false)
    await doRefreshToken()
    startRefreshTimer()
  }, [doRefreshToken, startRefreshTimer, user?.id])

  const refreshUser = useCallback(async () => {
    // Skip the refresh attempt entirely when there is no session hint.
    // The refresh token is an httpOnly cookie (not readable by JS), so
    // without this guard every anonymous page-load would POST to
    // /auth/refresh, get a 401, and pollute the browser console.
    if (!hasSessionHint()) {
      setIsLoading(false)
      return
    }

    // On page load, try to refresh the token using httpOnly cookie
    // If successful, we have a valid session
    try {
      const newToken = await doRefreshToken()
      if (newToken) {
        setSessionHint() // keep hint fresh
        const userData = await getMe(newToken)
        setUser(userData)
        // Set session start time if not already set (resuming existing session)
        if (!sessionStartTime) {
          setSessionStartTime(new Date())
        }
        startRefreshTimer()
      } else {
        clearSessionHint()
      }
    } catch {
      // No valid session, user needs to login
      clearSessionHint()
      clearAuth()
    } finally {
      setIsLoading(false)
    }
  }, [clearAuth, doRefreshToken, startRefreshTimer, sessionStartTime])

  useEffect(() => {
    refreshUser()

    // Cleanup on unmount
    return () => {
      if (refreshTimerRef.current) {
        clearInterval(refreshTimerRef.current)
      }
      if (timeoutWarningTimerRef.current) {
        clearTimeout(timeoutWarningTimerRef.current)
      }
      if (absoluteTimeoutTimerRef.current) {
        clearTimeout(absoluteTimeoutTimerRef.current)
      }
    }
    // Only run on mount to avoid recreating callback dependencies on every render
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // eslint-disable-next-line react-hooks/exhaustive-deps
  const login = async (
    credential: string,
    secret: string,
    turnstileToken?: string,
  ): Promise<TwoFactorRequired | void> => {
    // Determine if credential is email or card number based on format
    const isCardLogin = /^LSC\d{6}$/i.test(credential)

    const response = isCardLogin
      ? await apiLogin(credential, secret, turnstileToken)
      : await apiLogin(credential, secret, turnstileToken)

    // Check if 2FA is required
    if (response.requires_2fa && response.pending_token) {
      return { requires_2fa: true, pending_token: response.pending_token } as TwoFactorRequired
    }

    // Access token stored in memory only (refresh token is in httpOnly cookie)
    setToken(response.access_token)
    setAccessToken(response.access_token)
    setSessionHint()

    const userData = await getMe(response.access_token)
    setUser(userData)

    // Track session start time
    const startTime = new Date()
    setSessionStartTime(startTime)

    // Log session start event
    logSessionEvent('session_start', userData.id.toString(), {
      loginMethod: isCardLogin ? 'card' : 'email',
      startedAt: startTime.toISOString(),
    })

    // Start refresh timer
    startRefreshTimer()
  }

  // eslint-disable-next-line react-hooks/exhaustive-deps
  const completeLogin = async (accessToken: string) => {
    setToken(accessToken)
    setAccessToken(accessToken)
    setSessionHint()

    const userData = await getMe(accessToken)
    setUser(userData)

    const startTime = new Date()
    setSessionStartTime(startTime)

    logSessionEvent('session_start', userData.id.toString(), {
      loginMethod: '2fa',
      startedAt: startTime.toISOString(),
    })

    startRefreshTimer()
  }

  // eslint-disable-next-line react-hooks/exhaustive-deps
  const loginWithMagicLink = async (magicToken: string) => {
    const response = await apiVerifyMagicLink(magicToken)

    // Access token stored in memory only (refresh token is in httpOnly cookie)
    setToken(response.access_token)
    setAccessToken(response.access_token)
    setSessionHint()

    const userData = await getMe(response.access_token)
    setUser(userData)

    // Track session start time
    const startTime = new Date()
    setSessionStartTime(startTime)

    logSessionEvent('session_start', userData.id.toString(), {
      loginMethod: 'magic_link',
      startedAt: startTime.toISOString(),
    })

    startRefreshTimer()
  }

  // eslint-disable-next-line react-hooks/exhaustive-deps
  const register = async (data: RegisterData): Promise<User> => {
    const newUser = await apiRegister(data)
    // NOTE: Cloudflare Turnstile tokens are single-use server-side. In dev
    // (CF_TURNSTILE_SECRET unset) the backend fails open and re-using the
    // token here is harmless; in prod the auto-login will reject the spent
    // token (400 captcha failed) until a follow-up issue wires a second
    // widget or has /register return a session. Threaded for completeness.
    await login(data.email, data.password, data.turnstile_token)
    return newUser
  }

  // eslint-disable-next-line react-hooks/exhaustive-deps
  const logout = async () => {
    const currentUserId = user?.id
    const duration = getSessionDuration()

    // Log logout event before clearing
    logSessionEvent('session_logout', currentUserId?.toString(), {
      sessionDurationMs: duration,
      loggedOutAt: new Date().toISOString(),
    })

    // Try to logout on server (revoke refresh token via httpOnly cookie)
    if (token) {
      try {
        await apiLogout(token)
      } catch {
        // Ignore errors, still clear local state
      }
    }

    clearAuth()
  }

  // eslint-disable-next-line react-hooks/exhaustive-deps
  const updateProfile = async (data: UpdateProfileData) => {
    if (!token) throw new Error('Not authenticated')
    const updatedUser = await updateMe(token, data)
    setUser(updatedUser)
  }

  const handleDismissWarning = useCallback(() => {
    logSessionEvent('session_warning_dismissed', user?.id?.toString())
    setShowTimeoutWarning(false)
  }, [user?.id])

  const contextValue = useMemo(() => ({
    user,
    token,
    isLoading,
    isAuthenticated: !!user,
    sessionExpired,
    sessionStartTime,
    login,
    loginWithMagicLink,
    completeLogin,
    register,
    logout,
    updateProfile,
    refreshUser,
    clearSessionExpired,
    getSessionDuration,
  }), [user, token, isLoading, sessionExpired, sessionStartTime, login, loginWithMagicLink, completeLogin, register, logout, updateProfile, refreshUser, clearSessionExpired, getSessionDuration])

  return (
    <AuthContext.Provider value={contextValue}>
      {children}
      <SessionTimeoutWarning
        show={showTimeoutWarning}
        timeRemaining={timeoutSeconds}
        onExtend={handleExtendSession}
        onDismiss={handleDismissWarning}
      />
    </AuthContext.Provider>
  )
}

 
export function useAuth(): AuthContextType {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

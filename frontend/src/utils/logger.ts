/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
export enum LogLevel {
  DEBUG = 'debug',
  INFO = 'info',
  WARN = 'warn',
  ERROR = 'error',
}

// Lightweight Sentry-like interface so we don't hard-depend on the SDK.
// If @sentry/browser is installed, it will be loaded dynamically.
let _sentry: {
  captureException: (err: unknown, context?: Record<string, unknown>) => void
  captureMessage: (msg: string, level?: string) => void
  addBreadcrumb: (crumb: Record<string, unknown>) => void
} | null = null

export async function initErrorReporting(): Promise<void> {
  const dsn = import.meta.env.VITE_SENTRY_DSN as string | undefined
  if (!dsn) {
    return
  }

  try {
    const Sentry = await import('@sentry/browser')
    Sentry.init({
      dsn,
      environment: import.meta.env.MODE || 'development',
      release: import.meta.env.VITE_APP_VERSION || 'unknown',
      tracesSampleRate: import.meta.env.MODE === 'production' ? 0.1 : 1.0,
    })
    _sentry = {
      captureException: (err, ctx) =>
        Sentry.captureException(err, { extra: ctx as Record<string, unknown> }),
      captureMessage: (msg, level) =>
        Sentry.captureMessage(msg, level as Parameters<typeof Sentry.captureMessage>[1]),
      addBreadcrumb: (crumb) => Sentry.addBreadcrumb(crumb as Parameters<typeof Sentry.addBreadcrumb>[0]),
    }
    console.info('[Logger] Sentry initialized')
  } catch {
    // @sentry/browser not installed -- console-only mode
    console.debug('[Logger] Sentry SDK not available, using console-only logging')
  }
}

// Track error counts for monitoring
let _apiErrorCount = 0
let _componentErrorCount = 0

export function getErrorCounts() {
  return { apiErrors: _apiErrorCount, componentErrors: _componentErrorCount }
}

class Logger {
  private logLevel: LogLevel = LogLevel.INFO

  setLevel(level: LogLevel) {
    this.logLevel = level
  }

  debug(message: string, ...args: unknown[]) {
    if (this.shouldLog(LogLevel.DEBUG)) {
      console.debug(`[DEBUG] ${message}`, ...args)
      _sentry?.addBreadcrumb({ message, level: 'debug', data: { args } })
    }
  }

  info(message: string, ...args: unknown[]) {
    if (this.shouldLog(LogLevel.INFO)) {
      console.info(`[INFO] ${message}`, ...args)
      _sentry?.addBreadcrumb({ message, level: 'info', data: { args } })
    }
  }

  warn(message: string, ...args: unknown[]) {
    if (this.shouldLog(LogLevel.WARN)) {
      console.warn(`[WARN] ${message}`, ...args)
      _sentry?.captureMessage(message, 'warning')
    }
  }

  error(message: string, ...args: unknown[]) {
    if (this.shouldLog(LogLevel.ERROR)) {
      console.error(`[ERROR] ${message}`, ...args)
      const err = args.find((a) => a instanceof Error)
      if (err) {
        _sentry?.captureException(err, { message })
      } else {
        _sentry?.captureMessage(message, 'error')
      }
    }
  }

  apiError(endpoint: string, status: number, message?: string) {
    _apiErrorCount++
    const msg = `API error: ${endpoint} returned ${status}`
    console.error(`[API] ${msg}`, message)
    _sentry?.captureMessage(msg, 'error')
    _sentry?.addBreadcrumb({
      category: 'api',
      message: msg,
      level: 'error',
      data: { endpoint, status, message },
    })
  }

  componentError(componentName: string, error: Error) {
    _componentErrorCount++
    console.error(`[Component] Error in ${componentName}:`, error)
    _sentry?.captureException(error, { component: componentName })
  }

  private shouldLog(level: LogLevel): boolean {
    const levels = [LogLevel.DEBUG, LogLevel.INFO, LogLevel.WARN, LogLevel.ERROR]
    return levels.indexOf(level) >= levels.indexOf(this.logLevel)
  }
}

export const logger = new Logger()

// Set log level from environment
if (import.meta.env.MODE === 'development') {
  logger.setLevel(LogLevel.DEBUG)
}

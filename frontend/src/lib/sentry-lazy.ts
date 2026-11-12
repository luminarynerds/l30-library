/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/// <reference types="vite/client" />
type SentryAPI = {
  init: (opts: Record<string, unknown>) => void
  captureException: (e: unknown, ctx?: unknown) => unknown
  captureMessage: (msg: string, level?: string) => unknown
  addBreadcrumb: (b: Record<string, unknown>) => void
}

type Method = keyof SentryAPI
type QueuedCall = { method: Method; args: unknown[] }

const queue: QueuedCall[] = []
const MAX_QUEUE = 100
let sentry: SentryAPI | null = null
let loading = false
let loadAttempted = false

function flush(): void {
  if (!sentry) return
  while (queue.length) {
    const call = queue.shift()
    if (!call) break
    try {
      // @ts-expect-error variadic call into Sentry surface
      sentry[call.method](...call.args)
    } catch {
      // Swallow — Sentry replay shouldn't ever throw further.
    }
  }
}

function ensureLoaded(): void {
  if (sentry || loading || loadAttempted) return
  if (!import.meta.env.VITE_SENTRY_DSN) {
    loadAttempted = true
    return
  }
  loading = true
  void import('@sentry/browser')
    .then((mod) => {
      sentry = mod as unknown as SentryAPI
      flush()
    })
    .catch(() => {
      // Network/CSP failure — give up. Queue drains silently next call.
      sentry = null
    })
    .finally(() => {
      loading = false
      loadAttempted = true
    })
}

function queueOrCall(method: Method, args: unknown[]): void {
  ensureLoaded()
  if (sentry) {
    try {
      // @ts-expect-error variadic
      sentry[method](...args)
    } catch {
      // Suppress instrumentation failures
    }
    return
  }
  if (!import.meta.env.VITE_SENTRY_DSN) return
  if (queue.length >= MAX_QUEUE) queue.shift()
  queue.push({ method, args })
}

export function init(opts: Record<string, unknown>): void {
  queueOrCall('init', [opts])
}

export function captureException(e: unknown, ctx?: unknown): void {
  queueOrCall('captureException', ctx === undefined ? [e] : [e, ctx])
}

export function captureMessage(msg: string, level?: string): void {
  queueOrCall('captureMessage', level === undefined ? [msg] : [msg, level])
}

export function addBreadcrumb(b: Record<string, unknown>): void {
  queueOrCall('addBreadcrumb', [b])
}

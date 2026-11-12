/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { lazy, type ComponentType } from 'react'

const CHUNK_ERROR_PATTERNS = [
  'Failed to fetch dynamically imported module',
  'Importing a module script failed',
  'Loading chunk',
  'ChunkLoadError',
]

const shouldHandleChunkError = (error: unknown): boolean => {
  const message = error instanceof Error ? error.message : String(error)
  return CHUNK_ERROR_PATTERNS.some((pattern) => message.includes(pattern))
}

/**
 * How recently a stale-chunk reload must have happened for the next chunk
 * error to count as a genuine loop (chunk truly missing) rather than a new
 * deploy to recover from.
 */
export const RELOAD_LOOP_WINDOW_MS = 10_000

/**
 * Decide whether to reload the page in response to a stale-chunk error.
 *
 * Returns true (and records the attempt) unless we reloaded within the last
 * RELOAD_LOOP_WINDOW_MS. That short window means the chunk is genuinely gone
 * and reloading again would loop. A *later* deploy in the same session falls
 * outside the window and recovers. This replaces the old once-per-session
 * boolean flag, which was set on the first recovery and never cleared, so a
 * second deploy in a long-lived tab got no reload and hit the error boundary.
 * See: https://luminary-nerds.sentry.io/issues/L30-LIBRARY-2K
 */
export const shouldReloadAfterChunkError = (
  storage: Pick<Storage, 'getItem' | 'setItem'>,
  storageKey: string,
  now: number = Date.now(),
): boolean => {
  const last = Number(storage.getItem(storageKey) ?? 0)
  if (last && now - last < RELOAD_LOOP_WINDOW_MS) {
    return false
  }
  storage.setItem(storageKey, String(now))
  return true
}

/**
 * Wraps React.lazy imports to recover from stale chunk references after deploys.
 *
 * Behavior:
 * - retries the import once immediately
 * - if it still fails with a known chunk-load error, forces a hard reload
 *   (unless we just reloaded, to avoid an infinite loop)
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const lazyWithRetry = <T extends { default: ComponentType<any> }>(
  importer: () => Promise<T>,
  key: string,
) => {
  const reloadKey = `lazy-retry:${key}`

  return lazy(async () => {
    try {
      return await importer()
    } catch (firstError) {
      // quick retry for transient network hiccups
      try {
        return await importer()
      } catch (secondError) {
        if (
          typeof window !== 'undefined' &&
          shouldHandleChunkError(secondError) &&
          shouldReloadAfterChunkError(window.sessionStorage, reloadKey)
        ) {
          window.location.reload()
          // keep promise pending while reload occurs
          return new Promise<never>(() => undefined)
        }

        throw secondError instanceof Error ? secondError : firstError
      }
    }
  })
}

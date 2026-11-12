/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * usePiiAccessLog
 *
 * Returns a stable callback that records one PII access event. Stable
 * identity matters because callers will often invoke this inside
 * `useQuery` `queryFn` or `useEffect` -- a fresh function every render
 * would re-trigger those effects.
 *
 * Fire-and-forget by design: the returned callback returns void. If you
 * need the server's response (e.g. for tests), import `logPiiAccess`
 * directly from the api module instead.
 */
import { useCallback } from 'react'

import {
  logPiiAccess as logPiiAccessApi,
  type LogPiiAccessPayload,
} from '@/api/domains/services/pii-access-log-api'

export function usePiiAccessLog(): (payload: LogPiiAccessPayload) => void {
  return useCallback((payload: LogPiiAccessPayload) => {
    // Promise is intentionally not awaited and not returned -- the api
    // module already absorbs all errors and reports them via Sentry.
    void logPiiAccessApi(payload)
  }, [])
}

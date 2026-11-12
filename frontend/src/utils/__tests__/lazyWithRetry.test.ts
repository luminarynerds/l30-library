/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect } from 'vitest'
import { shouldReloadAfterChunkError, RELOAD_LOOP_WINDOW_MS } from '../lazyWithRetry'

function fakeStorage(initial: Record<string, string> = {}) {
  const map = new Map<string, string>(Object.entries(initial))
  return {
    getItem: (k: string) => (map.has(k) ? (map.get(k) as string) : null),
    setItem: (k: string, v: string) => { map.set(k, v) },
  }
}

const KEY = '__test_reload_ts__'

describe('shouldReloadAfterChunkError', () => {
  it('reloads and records the timestamp on the first stale-chunk error', () => {
    const s = fakeStorage()
    expect(shouldReloadAfterChunkError(s, KEY, 1_000_000)).toBe(true)
    expect(s.getItem(KEY)).toBe('1000000')
  })

  it('does NOT reload again within the loop window (genuinely missing chunk)', () => {
    const s = fakeStorage()
    shouldReloadAfterChunkError(s, KEY, 1_000_000)
    const soon = 1_000_000 + RELOAD_LOOP_WINDOW_MS - 1
    expect(shouldReloadAfterChunkError(s, KEY, soon)).toBe(false)
  })

  it('reloads again after a later deploy outside the window (regression: 2nd deploy in one session)', () => {
    const s = fakeStorage()
    shouldReloadAfterChunkError(s, KEY, 1_000_000)
    const later = 1_000_000 + RELOAD_LOOP_WINDOW_MS + 1
    expect(shouldReloadAfterChunkError(s, KEY, later)).toBe(true)
    expect(s.getItem(KEY)).toBe(String(later))
  })
})

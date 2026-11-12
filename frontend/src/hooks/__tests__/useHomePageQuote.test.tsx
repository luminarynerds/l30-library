/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useHomePageQuote } from '../useHomePageQuote'

const QUOTES = [
  { id: 1, quote_text: 'A', attribution: null },
  { id: 2, quote_text: 'B', attribution: null },
  { id: 3, quote_text: 'C', attribution: null },
]

let mockQuotes = QUOTES
let mockPreset: string | undefined = undefined
let mockReduceMotion = false

vi.mock('@/hooks/useHomepageQuotes', () => ({
  useHomepageQuotes: () => ({ data: mockQuotes }),
}))

vi.mock('@/features/accessibility', () => ({
  useUnifiedAccessibility: () => ({
    settings: { reduceMotion: mockReduceMotion },
    getCurrentPreset: () => mockPreset,
  }),
}))

describe('useHomePageQuote', () => {
  beforeEach(() => {
    mockQuotes = QUOTES
    mockPreset = undefined
    mockReduceMotion = false
    sessionStorage.clear()
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('returns null when calm preset is active', () => {
    mockPreset = 'calm'
    const { result } = renderHook(() => useHomePageQuote('en'))
    expect(result.current).toBeNull()
  })

  it('returns null when there are no quotes', () => {
    mockQuotes = []
    const { result } = renderHook(() => useHomePageQuote('en'))
    expect(result.current).toBeNull()
  })

  it('returns a quote when not calm and quotes exist', () => {
    const { result } = renderHook(() => useHomePageQuote('en'))
    expect(result.current).not.toBeNull()
    expect(QUOTES).toContainEqual(result.current)
  })

  it('rotates to a new quote every 12 seconds in default mode', () => {
    const { result } = renderHook(() => useHomePageQuote('en'))
    const first = result.current
    act(() => { vi.advanceTimersByTime(12000) })
    const second = result.current
    expect(second).not.toEqual(first)
    act(() => { vi.advanceTimersByTime(12000) })
    const third = result.current
    expect(third).not.toEqual(second)
  })

  it('does not rotate when reduceMotion is set', () => {
    mockReduceMotion = true
    const { result } = renderHook(() => useHomePageQuote('en'))
    const first = result.current
    act(() => { vi.advanceTimersByTime(60000) })
    expect(result.current).toEqual(first)
  })

  it('caches the static-mode pick per day per locale in sessionStorage', () => {
    mockReduceMotion = true
    const today = new Date().toISOString().slice(0, 10)
    const storageKey = `lsc-homepage-quote-en-${today}`
    sessionStorage.setItem(storageKey, '2')
    const { result } = renderHook(() => useHomePageQuote('en'))
    expect(result.current).toEqual(QUOTES[2])
  })
})

/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Tests for the parent-onboarding dashboard prefs hook (Shape A,
 * localStorage-only persistence).
 *
 * Note: src/__tests__/setup.ts replaces window.localStorage with bare
 * `vi.fn()` stubs that don't store anything. We restore real persistence
 * inside this file by installing a Map-backed Storage shim, so round-trip
 * assertions actually verify behavior instead of a stub.
 */
import { describe, it, expect, beforeEach, beforeAll, afterAll } from 'vitest'
import { act, renderHook } from '@testing-library/react'
import {
  STORAGE_KEY,
  useParentOnboardingDashboardPrefs,
} from '../useParentOnboardingDashboardPrefs'

let storage: Map<string, string>
let originalLocalStorage: Storage

beforeAll(() => {
  originalLocalStorage = window.localStorage
  storage = new Map<string, string>()
  const shim: Storage = {
    get length() { return storage.size },
    clear: () => storage.clear(),
    getItem: (key: string) => (storage.has(key) ? storage.get(key)! : null),
    setItem: (key: string, value: string) => { storage.set(key, String(value)) },
    removeItem: (key: string) => { storage.delete(key) },
    key: (index: number) => Array.from(storage.keys())[index] ?? null,
  }
  Object.defineProperty(window, 'localStorage', { value: shim, configurable: true })
})

afterAll(() => {
  Object.defineProperty(window, 'localStorage', { value: originalLocalStorage, configurable: true })
})

beforeEach(() => {
  storage.clear()
})

describe('useParentOnboardingDashboardPrefs', () => {
  it('defaults overdueRiskFilter to "all" when storage is empty', () => {
    const { result } = renderHook(() => useParentOnboardingDashboardPrefs())
    expect(result.current.overdueRiskFilter).toBe('all')
  })

  it('persists the filter to localStorage under the documented key', () => {
    const { result } = renderHook(() => useParentOnboardingDashboardPrefs())
    act(() => result.current.setOverdueRiskFilter('high'))
    expect(result.current.overdueRiskFilter).toBe('high')
    const raw = window.localStorage.getItem(STORAGE_KEY)
    expect(raw).toBeTruthy()
    expect(JSON.parse(raw!)).toEqual({ overdueRiskFilter: 'high' })
  })

  it('reads a persisted value on first mount', () => {
    window.localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ overdueRiskFilter: 'high' }),
    )
    const { result } = renderHook(() => useParentOnboardingDashboardPrefs())
    expect(result.current.overdueRiskFilter).toBe('high')
  })

  it('falls back to default when stored JSON is malformed', () => {
    window.localStorage.setItem(STORAGE_KEY, '{not-json')
    const { result } = renderHook(() => useParentOnboardingDashboardPrefs())
    expect(result.current.overdueRiskFilter).toBe('all')
  })

  it('falls back to default when stored value has an unknown filter value', () => {
    window.localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ overdueRiskFilter: 'definitely-not-a-real-filter' }),
    )
    const { result } = renderHook(() => useParentOnboardingDashboardPrefs())
    expect(result.current.overdueRiskFilter).toBe('all')
  })

  it('falls back to default when stored value is missing the expected field', () => {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify({ other: 'thing' }))
    const { result } = renderHook(() => useParentOnboardingDashboardPrefs())
    expect(result.current.overdueRiskFilter).toBe('all')
  })

  it('keeps state in sync across hook remounts via storage round-trip', () => {
    const first = renderHook(() => useParentOnboardingDashboardPrefs())
    act(() => first.result.current.setOverdueRiskFilter('high'))
    first.unmount()

    const second = renderHook(() => useParentOnboardingDashboardPrefs())
    expect(second.result.current.overdueRiskFilter).toBe('high')
  })
})

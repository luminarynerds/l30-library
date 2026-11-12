/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Persisted UI preferences for the Parent Onboarding dashboard.
 *
 * Shape A (localStorage only).
 * Backend persistence (shape B) was considered but the existing
 * PreferencesContext / `learning/preferences` endpoint takes a typed schema,
 * not an arbitrary JSON blob, so adopting it would require backend changes
 * the design explicitly rules out.
 *
 * Storage shape is validated on read; malformed values fall back to defaults
 * silently (see [[feedback_l30_localstorage_stale_shape]]).
 */
import { useCallback, useState } from 'react'

export type OverdueRiskFilter = 'all' | 'high' | 'medium_and_high'

export interface ParentOnboardingDashboardPrefs {
  overdueRiskFilter: OverdueRiskFilter
}

export const STORAGE_KEY = 'l30:parent-onboarding-dashboard-prefs'

const DEFAULT_PREFS: ParentOnboardingDashboardPrefs = {
  overdueRiskFilter: 'all',
}

const VALID_FILTERS: ReadonlyArray<OverdueRiskFilter> = ['all', 'high', 'medium_and_high']

function isValidFilter(value: unknown): value is OverdueRiskFilter {
  return typeof value === 'string' && (VALID_FILTERS as readonly string[]).includes(value)
}

function readPrefs(): ParentOnboardingDashboardPrefs {
  if (typeof window === 'undefined') return DEFAULT_PREFS
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    if (!raw) return DEFAULT_PREFS
    const parsed: unknown = JSON.parse(raw)
    if (parsed && typeof parsed === 'object' && 'overdueRiskFilter' in parsed) {
      const f = (parsed as { overdueRiskFilter: unknown }).overdueRiskFilter
      if (isValidFilter(f)) return { overdueRiskFilter: f }
    }
    return DEFAULT_PREFS
  } catch {
    return DEFAULT_PREFS
  }
}

function writePrefs(prefs: ParentOnboardingDashboardPrefs): void {
  if (typeof window === 'undefined') return
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs))
  } catch {
    /* storage full or disabled, drop silently */
  }
}

export function useParentOnboardingDashboardPrefs() {
  const [prefs, setPrefs] = useState<ParentOnboardingDashboardPrefs>(() => readPrefs())

  const setOverdueRiskFilter = useCallback((next: OverdueRiskFilter) => {
    setPrefs((current) => {
      const updated = { ...current, overdueRiskFilter: next }
      writePrefs(updated)
      return updated
    })
  }, [])

  return {
    overdueRiskFilter: prefs.overdueRiskFilter,
    setOverdueRiskFilter,
  }
}

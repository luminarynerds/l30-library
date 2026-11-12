/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useMemo, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import type { EventFilters as Filters } from '@/api/api'

interface UseEventsFilterUrlSyncArgs {
  filters: Filters
  setFilters: (next: Filters | ((prev: Filters) => Filters)) => void
  showPastEvents: boolean
  setShowPastEvents: (next: boolean) => void
}

interface UseEventsFilterUrlSyncResult {
  /** Snapshot of how many "real" filter params were present in the URL at
   *  initial mount. Used by the page to decide whether the mobile filter
   *  panel should start collapsed (only when this is 0). */
  initialActiveFilterCount: number
}

export function useEventsFilterUrlSync({
  filters,
  setFilters,
  showPastEvents,
  setShowPastEvents,
}: UseEventsFilterUrlSyncArgs): UseEventsFilterUrlSyncResult {
  const [searchParams, setSearchParams] = useSearchParams()
  const hydratedRef = useRef(false)

  // Snapshot initial active-filter count at first render (NOT in an effect)
  // so the page can compute its mobile-collapse default synchronously, with
  // no collapsed-then-snap-open flash.
  const initialActiveFilterCountRef = useRef<number | null>(null)
  if (initialActiveFilterCountRef.current === null) {
    let n = 0
    if (searchParams.get('category')) n += 1
    if (searchParams.get('tag')) n += 1
    if (searchParams.get('search')) n += 1
    if (searchParams.getAll('audiences').length > 0) n += 1
    if (searchParams.get('when')) n += 1
    if (searchParams.get('drop_in') === '1') n += 1
    if (searchParams.getAll('accessibility').length > 0) n += 1
    if (searchParams.getAll('languages').length > 0) n += 1
    if (searchParams.getAll('branches').length > 0) n += 1
    if (searchParams.get('past') === '1') n += 1
    initialActiveFilterCountRef.current = n
  }

  // One-shot hydration: URL -> filter state on first mount.
  useEffect(() => {
    if (hydratedRef.current) return
    hydratedRef.current = true

    const category = searchParams.get('category')
    const tag = searchParams.get('tag')
    const search = searchParams.get('search')
    const audiences = searchParams.getAll('audiences')
    const when = searchParams.get('when')
    const dropIn = searchParams.get('drop_in')
    const accessibility = searchParams.getAll('accessibility')
    const languages = searchParams.getAll('languages')
    // Branch ids arrive as strings; keep only valid integers.
    const branches = searchParams
      .getAll('branches')
      .map((b) => Number.parseInt(b, 10))
      .filter((b) => Number.isInteger(b) && b > 0)
    const past = searchParams.get('past')

    setFilters((prev) => {
      const next: Filters = { ...prev }
      if (category) next.category = category
      if (tag) next.tag = tag
      if (search) next.search = search
      if (audiences.length > 0 && !prev.audiences?.length) next.audiences = audiences
      // `when` is a closed set; ignore anything else a hand-edited URL carries.
      if ((when === 'today' || when === 'weekend' || when === 'week') && !prev.when) {
        next.when = when
      }
      if (dropIn === '1' && !prev.drop_in) next.drop_in = true
      if (accessibility.length > 0 && !prev.accessibility?.length) {
        next.accessibility = accessibility
      }
      if (languages.length > 0 && !prev.languages?.length) {
        next.languages = languages
      }
      if (branches.length > 0 && !prev.branch_ids?.length) {
        next.branch_ids = branches
      }
      return next
    })

    if (past === '1' && !showPastEvents) {
      setShowPastEvents(true)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Write-back: filter state -> URL whenever it changes (post-hydration).
  // We do this with a dependency on the actual filter values, not on the
  // `filters` object identity, so a no-op re-render does not churn the URL.
  const filtersSig = useMemo(
    () =>
      JSON.stringify({
        category: filters.category ?? null,
        tag: filters.tag ?? null,
        search: filters.search ?? null,
        audiences: filters.audiences ?? null,
        when: filters.when ?? null,
        drop_in: filters.drop_in ?? null,
        accessibility: filters.accessibility ?? null,
        languages: filters.languages ?? null,
        branch_ids: filters.branch_ids ?? null,
        past: showPastEvents ? '1' : null,
      }),
    [
      filters.category,
      filters.tag,
      filters.search,
      filters.audiences,
      filters.when,
      filters.drop_in,
      filters.accessibility,
      filters.languages,
      filters.branch_ids,
      showPastEvents,
    ]
  )

  useEffect(() => {
    if (!hydratedRef.current) return
    const next = new URLSearchParams(searchParams)

    // Replace every filter param idempotently — this hook is the single
    // owner of URL <-> filter sync; the quick chips and panel only set state.
    const setOrDelete = (key: string, value: string | undefined | null) => {
      if (value) next.set(key, value)
      else next.delete(key)
    }
    setOrDelete('category', filters.category)
    setOrDelete('tag', filters.tag)
    setOrDelete('search', filters.search)
    setOrDelete('when', filters.when)
    setOrDelete('drop_in', filters.drop_in ? '1' : null)
    setOrDelete('past', showPastEvents ? '1' : null)

    // Multi-value params; mirror current state with repeated keys.
    next.delete('audiences')
    for (const a of filters.audiences ?? []) next.append('audiences', a)
    next.delete('accessibility')
    for (const a of filters.accessibility ?? []) next.append('accessibility', a)
    next.delete('languages')
    for (const l of filters.languages ?? []) next.append('languages', l)
    next.delete('branches')
    for (const b of filters.branch_ids ?? []) next.append('branches', String(b))

    // Avoid a no-op setSearchParams call (which still triggers a navigation).
    if (next.toString() !== searchParams.toString()) {
      setSearchParams(next, { replace: true })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filtersSig])

  return { initialActiveFilterCount: initialActiveFilterCountRef.current }
}

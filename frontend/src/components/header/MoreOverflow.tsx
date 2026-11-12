/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * MoreOverflow — measure-based "more" overflow for desktop nav groups.
 *
 * Before: Layout.tsx used a CSS-only `xl:hidden` / `hidden xl:flex` split.
 * That worked at the breakpoint Tailwind picked but silently clipped items
 * for any localized label that pushed the row over (parent had
 * `overflow-hidden`). It also forced an arbitrary "lg = collapse all"
 * binary instead of degrading item-by-item.
 *
 * Now: we render every group, measure each child, and move whatever does
 * not fit into a "More" NavDropdown. ResizeObserver drives updates; an old
 * Safari fallback splits at the previous 1280px breakpoint.
 *
 * ND-friendliness: continuous remeasurement on every pixel of resize is
 * disorienting for users with vestibular / attention sensitivities (the
 * row appears to "breathe" as items pop in and out). We snap to Tailwind
 * breakpoint buckets [640, 768, 1024, 1152, 1280, 1536] so reflow only happens
 * when the container crosses a meaningful threshold. We also honor
 * prefers-reduced-motion at the CSS layer (no transitions on the visible
 * row; NavDropdown children already use motion-safe:).
 */
import { useEffect, useLayoutEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { MoreHorizontal } from 'lucide-react'

import NavDropdown from '../NavDropdown'
import type { NavGroup } from './navConfig'

interface MoreOverflowProps {
  items: NavGroup[]
  renderItem: (group: NavGroup) => ReactNode
  moreLabel: string
  isActive: (path: string, exact?: boolean) => boolean
}

const SAFE_RIGHT_PADDING = 8

// Tailwind sm/md/lg/xl/2xl. Below 640 the mobile nav takes over and
// MoreOverflow is not rendered, so 0 is a valid "pre-sm" bucket marker.
const SNAP_POINTS = [640, 768, 1024, 1152, 1280, 1536] as const

function bucketFor(width: number): number {
  let bucket = 0
  for (const point of SNAP_POINTS) {
    if (width >= point) bucket = point
    else break
  }
  return bucket
}

function useMinWidth(query: string): boolean {
  const get = () =>
    typeof window !== 'undefined' && typeof window.matchMedia === 'function'
      ? window.matchMedia(query).matches
      : true
  const [matches, setMatches] = useState<boolean>(get)
  useEffect(() => {
    if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return
    const mq = window.matchMedia(query)
    const handler = (e: MediaQueryListEvent) => setMatches(e.matches)
    if (typeof mq.addEventListener === 'function') {
      mq.addEventListener('change', handler)
      return () => mq.removeEventListener('change', handler)
    }
    mq.addListener(handler)
    return () => mq.removeListener(handler)
  }, [query])
  return matches
}

export default function MoreOverflow({
  items,
  renderItem,
  moreLabel,
  isActive,
}: MoreOverflowProps): React.ReactElement {
  const containerRef = useRef<HTMLDivElement>(null)
  const measureRef = useRef<HTMLDivElement>(null)
  const moreSlotRef = useRef<HTMLDivElement>(null)
  const hasResizeObserver = typeof window !== 'undefined' && typeof window.ResizeObserver !== 'undefined'
  const isXl = useMinWidth('(min-width: 1280px)')

  // visibleCount = number of items rendered inline; the rest go into More.
  const [visibleCount, setVisibleCount] = useState<number>(items.length)

  // Last bucket the fit calculation was run against. Initialized to -1 so the
  // first measure always runs (bucket 0 is a real value: "below sm").
  const lastBucketRef = useRef<number>(-1)

  const measure = () => {
    const container = containerRef.current
    const measureRow = measureRef.current
    if (!container || !measureRow) return
    const available = container.clientWidth - SAFE_RIGHT_PADDING
    // jsdom and unsized containers report clientWidth=0; treat as "render all
    // inline" so tests that assert DOM presence (rather than visibility) still
    // find every group. Real browsers always produce a positive width here.
    if (available <= 0) {
      if (visibleCount !== items.length) setVisibleCount(items.length)
      return
    }
    const moreWidth = moreSlotRef.current?.offsetWidth ?? 0
    const children = Array.from(measureRow.children) as HTMLElement[]

    // First pass: do all items fit without a "More" trigger?
    const total = children.reduce((sum, el) => sum + el.offsetWidth, 0)
    if (total <= available) {
      if (visibleCount !== items.length) setVisibleCount(items.length)
      return
    }

    // Second pass: budget assumes "More" is shown.
    const budget = available - moreWidth
    let used = 0
    let count = 0
    for (const el of children) {
      const w = el.offsetWidth
      if (used + w <= budget) {
        used += w
        count += 1
      } else {
        break
      }
    }
    if (count !== visibleCount) setVisibleCount(count)
  }

  // rAF-debounced measure: coalesces back-to-back ResizeObserver callbacks.
  // Bucket-gated: within the same Tailwind breakpoint bucket, RO callbacks
  // return early before scheduling a measure. This stabilizes the layout
  // against intra-bucket resize jitter (the ND-friendliness mitigation).
  const rafRef = useRef<number | null>(null)
  const scheduleMeasure = () => {
    const container = containerRef.current
    if (container) {
      const width = container.clientWidth
      const bucket = bucketFor(width)
      if (bucket === lastBucketRef.current) return
      lastBucketRef.current = bucket
    }
    if (rafRef.current !== null) return
    rafRef.current = requestAnimationFrame(() => {
      rafRef.current = null
      measure()
    })
  }

  useLayoutEffect(() => {
    if (!hasResizeObserver) return
    // Initial measure: prime the bucket so the first RO callback at the same
    // width is correctly skipped, but always run the fit calculation once.
    const container = containerRef.current
    if (container) lastBucketRef.current = bucketFor(container.clientWidth)
    measure()
    const ro = new ResizeObserver(scheduleMeasure)
    if (container) ro.observe(container)
    return () => {
      ro.disconnect()
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hasResizeObserver, items.length])

  // Defense in depth for `inert`: walk the measurement subtree and force
  // tabIndex=-1 on every focusable descendant. Modern browsers honor `inert`
  // (Chrome 102+, Safari 15.5+, FF 112+), but Lighthouse's `aria-hidden-focus`
  // audit historically still flags descendants unless the focus attribute is
  // set explicitly. Re-runs whenever items change (NavDropdowns re-render).
  useEffect(() => {
    const node = measureRef.current
    if (!node) return
    const focusables = node.querySelectorAll<HTMLElement>(
      'a, button, input, select, textarea, [tabindex]'
    )
    focusables.forEach(el => {
      el.setAttribute('tabindex', '-1')
    })
  }, [items])

  // Fallback when ResizeObserver is unavailable: keep prior breakpoint behavior.
  // At >= xl, render everything inline; below, collapse everything into More.
  const effectiveVisibleCount = hasResizeObserver ? visibleCount : isXl ? items.length : 0

  const inline = items.slice(0, effectiveVisibleCount)
  const overflow = items.slice(effectiveVisibleCount)

  // Aggregate overflow groups' sections into a single mega-menu under "More".
  const overflowSections = useMemo(
    () => overflow.flatMap(g => g.sections),
    [overflow]
  )

  return (
    // No transition on the visible row itself: any item show/hide is an
    // instantaneous swap, never an animation. NavDropdown internals already
    // gate their own motion behind motion-safe:.
    <div ref={containerRef} className="relative flex items-center gap-1 xl:gap-1.5 flex-1 min-w-0">
      {/* Off-screen measurement row: renders every group so we can read widths.
          aria-hidden hides from AT; inert + tabIndex=-1 walk removes descendants
          from the focus order (a11y: aria-hidden-focus, WCAG 4.1.2). */}
      <div
        ref={measureRef}
        aria-hidden="true"
        // @ts-expect-error inert is a valid HTML attribute; not in React 18 types
        inert=""
        className="absolute -top-[9999px] left-0 flex items-center gap-1 xl:gap-1.5 pointer-events-none"
      >
        {items.map(group => (
          <div key={`measure-${group.key}`}>{renderItem(group)}</div>
        ))}
        <div ref={moreSlotRef}>
          <NavDropdown
            label={moreLabel}
            icon={MoreHorizontal}
            sections={[]}
            isActive={isActive}
            align="left"
          />
        </div>
      </div>

      {/* Visible row */}
      {inline.map(group => (
        <span key={group.key}>{renderItem(group)}</span>
      ))}
      {overflow.length > 0 && (
        <NavDropdown
          label={moreLabel}
          icon={MoreHorizontal}
          sections={overflowSections}
          isActive={isActive}
          align="left"
        />
      )}
    </div>
  )
}

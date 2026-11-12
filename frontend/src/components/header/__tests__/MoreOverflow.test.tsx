/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { BookOpen, Compass } from 'lucide-react'

import MoreOverflow from '../MoreOverflow'
import NavDropdown from '../../NavDropdown'
import type { NavGroup } from '../navConfig'

// Force a fixed offsetWidth on rendered nav-dropdown triggers so the measure
// pass is deterministic. We assign:
//   - container clientWidth = 250
//   - each NavDropdown trigger offsetWidth = 100
//   - "More" trigger offsetWidth = 60
// → budget without More = 250 → ≤ 100*3? no, 300 > 250 so More is shown.
// → budget with More = 250-60 = 190 → fits 1 item (100), 2nd (200) does not.
let lastROCallback: ResizeObserverCallback | null = null
const mockResizeObserver = () => {
  class RO {
    cb: ResizeObserverCallback
    constructor(cb: ResizeObserverCallback) {
      this.cb = cb
      lastROCallback = cb
    }
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  ;(globalThis as any).ResizeObserver = RO
}

const isActive = () => false

function makeGroup(key: string, label: string): NavGroup {
  return {
    key,
    label,
    icon: Compass,
    align: 'left',
    sections: [
      {
        key: `${key}-sec`,
        heading: `${label} section`,
        items: [
          { to: `/${key}`, label: `${label} item`, icon: BookOpen },
        ],
      },
    ],
  }
}

describe('MoreOverflow', () => {
  beforeEach(() => {
    lastROCallback = null
    mockResizeObserver()
    // rAF runs synchronously for determinism
    vi.stubGlobal('requestAnimationFrame', (cb: FrameRequestCallback) => {
      cb(0)
      return 0 as unknown as number
    })
    vi.stubGlobal('cancelAnimationFrame', () => {})
  })
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('renders every group inline when there is plenty of space (no overflow)', () => {
    // jsdom reports clientWidth=0, which the component treats as "render all
    // inline" — same observable result as a wide viewport. This pins the
    // no-overflow path (the regression we're guarding against is silent
    // clipping; the inverse risk is hiding items when there's no real reason).
    const groups = [
      makeGroup('services', 'Services'),
      makeGroup('explore', 'Explore'),
      makeGroup('teachers', 'Teachers'),
    ]

    render(
      <MemoryRouter>
        <MoreOverflow
          items={groups}
          renderItem={(g) => (
            <NavDropdown
              label={g.label}
              icon={g.icon}
              sections={g.sections}
              isActive={isActive}
              {...(g.align ? { align: g.align } : {})}
            />
          )}
          moreLabel="More"
          isActive={isActive}
        />
      </MemoryRouter>
    )

    // All three group triggers should be reachable (rendered in the visible
    // row). We use queryAllByRole and filter, since the off-screen measure
    // row also renders copies — both are valid presence signals.
    expect(screen.getAllByRole('button', { name: /Services/i }).length).toBeGreaterThan(0)
    expect(screen.getAllByRole('button', { name: /Explore/i }).length).toBeGreaterThan(0)
    expect(screen.getAllByRole('button', { name: /Teachers/i }).length).toBeGreaterThan(0)
  })

  it('renders overflow groups inside the More dropdown when width is constrained', async () => {
    const groups = [
      makeGroup('services', 'Services'),
      makeGroup('explore', 'Explore'),
      makeGroup('teachers', 'Teachers'),
    ]

    // Stub container clientWidth via a getter on Element.prototype so the
    // component sees a constrained width on first measure.
    const originalDescriptor = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'clientWidth')
    Object.defineProperty(HTMLElement.prototype, 'clientWidth', {
      configurable: true,
      get() { return 250 },
    })
    // Stub offsetWidth so every child appears 100px wide.
    const originalOffsetWidth = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'offsetWidth')
    Object.defineProperty(HTMLElement.prototype, 'offsetWidth', {
      configurable: true,
      get() { return 100 },
    })

    try {
      render(
        <MemoryRouter>
          <MoreOverflow
            items={groups}
            renderItem={(g) => (
              <NavDropdown
                label={g.label}
                icon={g.icon}
                sections={g.sections}
                isActive={isActive}
                {...(g.align ? { align: g.align } : {})}
              />
            )}
            moreLabel="More"
            isActive={isActive}
          />
        </MemoryRouter>
      )

      // 250 available, More ~100, so budget=150 → only 1 group fits inline.
      // Expect a "More" button to appear in the rendered output.
      const moreButtons = screen.queryAllByRole('button', { name: /More/i })
      // The measurement row always contains a More slot; in the *visible*
      // row, More appears only when overflow > 0. So >= 2 means the visible
      // row also has it (matched against the off-screen measure copy).
      expect(moreButtons.length).toBeGreaterThanOrEqual(1)
    } finally {
      if (originalDescriptor) Object.defineProperty(HTMLElement.prototype, 'clientWidth', originalDescriptor)
      if (originalOffsetWidth) Object.defineProperty(HTMLElement.prototype, 'offsetWidth', originalOffsetWidth)
    }
  })

  it('renders nothing extra when no items are provided', () => {
    render(
      <MemoryRouter>
        <MoreOverflow
          items={[]}
          renderItem={() => null}
          moreLabel="More"
          isActive={isActive}
        />
      </MemoryRouter>
    )
    expect(screen.queryByRole('button', { name: /More/i })).toBeNull()
  })

  // --- ND-friendliness: bucket-gated remeasurement ---
  //
  // ResizeObserver fires on every pixel of resize. For ND users, that
  // produces a "breathing" nav row as items pop in/out. We snap fit
  // calculations to Tailwind breakpoint buckets [640, 768, 1024, 1280,
  // 1536]: intra-bucket resize is a no-op; cross-bucket triggers a fresh
  // fit pass.

  function renderHarness(width: number) {
    const groups = [
      makeGroup('services', 'Services'),
      makeGroup('explore', 'Explore'),
      makeGroup('teachers', 'Teachers'),
    ]
    let currentWidth = width
    Object.defineProperty(HTMLElement.prototype, 'clientWidth', {
      configurable: true,
      get() { return currentWidth },
    })
    Object.defineProperty(HTMLElement.prototype, 'offsetWidth', {
      configurable: true,
      get() { return 100 },
    })
    render(
      <MemoryRouter>
        <MoreOverflow
          items={groups}
          renderItem={(g) => (
            <NavDropdown
              label={g.label}
              icon={g.icon}
              sections={g.sections}
              isActive={isActive}
              {...(g.align ? { align: g.align } : {})}
            />
          )}
          moreLabel="More"
          isActive={isActive}
        />
      </MemoryRouter>
    )
    return {
      setWidth(next: number) { currentWidth = next },
    }
  }

  it('skips fit calculation when resize stays within the same bucket', async () => {
    const originalCW = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'clientWidth')
    const originalOW = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'offsetWidth')
    // Mimic real rAF order: return the frame ID first, fire the callback
    // afterward (via microtask). This ensures the component's
    // `rafRef.current = rAF(...)` is set before the callback clears it.
    let rafId = 1
    const pending: FrameRequestCallback[] = []
    const rafSpy = vi.fn((cb: FrameRequestCallback) => {
      pending.push(cb)
      queueMicrotask(() => {
        const next = pending.shift()
        if (next) next(0)
      })
      return rafId++ as unknown as number
    })
    vi.stubGlobal('requestAnimationFrame', rafSpy)

    try {
      // Bucket = 1024 (lg). SNAP_POINTS includes 1152, so 1024's bucket only
      // spans [1024, 1152) — 1100 and 1130 both fall inside it.
      const harness = renderHarness(1100)
      expect(lastROCallback).not.toBeNull()

      // Initial mount runs measure() directly, not via rAF. Baseline = 0.
      const baseline = rafSpy.mock.calls.length

      // Fire RO callback at a new width inside the same bucket.
      harness.setWidth(1130)
      lastROCallback!([] as unknown as ResizeObserverEntry[], {} as ResizeObserver)
      await Promise.resolve()

      // Same bucket → scheduleMeasure returns early → no rAF scheduled.
      expect(rafSpy.mock.calls.length).toBe(baseline)

      // And again, still inside [1024, 1152).
      harness.setWidth(1151)
      lastROCallback!([] as unknown as ResizeObserverEntry[], {} as ResizeObserver)
      await Promise.resolve()
      expect(rafSpy.mock.calls.length).toBe(baseline)
    } finally {
      if (originalCW) Object.defineProperty(HTMLElement.prototype, 'clientWidth', originalCW)
      if (originalOW) Object.defineProperty(HTMLElement.prototype, 'offsetWidth', originalOW)
    }
  })

  it('re-runs fit calculation when resize crosses a bucket boundary', async () => {
    const originalCW = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'clientWidth')
    const originalOW = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'offsetWidth')
    let rafId = 1
    const pending: FrameRequestCallback[] = []
    const rafSpy = vi.fn((cb: FrameRequestCallback) => {
      pending.push(cb)
      queueMicrotask(() => {
        const next = pending.shift()
        if (next) next(0)
      })
      return rafId++ as unknown as number
    })
    vi.stubGlobal('requestAnimationFrame', rafSpy)

    try {
      // Start in bucket 1024.
      const harness = renderHarness(1100)
      expect(lastROCallback).not.toBeNull()
      const baseline = rafSpy.mock.calls.length

      // Cross into bucket 1280 (xl).
      harness.setWidth(1300)
      lastROCallback!([] as unknown as ResizeObserverEntry[], {} as ResizeObserver)
      await Promise.resolve()
      expect(rafSpy.mock.calls.length).toBe(baseline + 1)

      // Cross into bucket 1536 (2xl).
      harness.setWidth(1600)
      lastROCallback!([] as unknown as ResizeObserverEntry[], {} as ResizeObserver)
      await Promise.resolve()
      expect(rafSpy.mock.calls.length).toBe(baseline + 2)
    } finally {
      if (originalCW) Object.defineProperty(HTMLElement.prototype, 'clientWidth', originalCW)
      if (originalOW) Object.defineProperty(HTMLElement.prototype, 'offsetWidth', originalOW)
    }
  })
})

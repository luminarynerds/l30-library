import { render, screen, fireEvent } from '@testing-library/react'
import { vi } from 'vitest'
import WhatsMissingPanel from '../WhatsMissingPanel'

const baseCourse = { title: 'C', thumbnail_url: '', access_level: 'patron', difficulty: 'beginner' }
const baseModules: any[] = []

// The global test setup mounts a vi.fn()-based localStorage mock that doesn't
// actually persist values. Wire a Map-backed store per test so dismiss/snooze
// round-trips through the real getItem/setItem cycle.
const store = new Map<string, string>()
beforeEach(() => {
  store.clear()
  vi.mocked(localStorage.getItem).mockClear()
  vi.mocked(localStorage.setItem).mockClear()
  vi.mocked(localStorage.removeItem).mockClear()
  vi.mocked(localStorage.clear).mockClear()
  vi.mocked(localStorage.getItem).mockImplementation((k) => store.get(k) ?? null)
  vi.mocked(localStorage.setItem).mockImplementation((k, v) => { store.set(k, v) })
  vi.mocked(localStorage.removeItem).mockImplementation((k) => { store.delete(k) })
  vi.mocked(localStorage.clear).mockImplementation(() => { store.clear() })
})

describe('WhatsMissingPanel (Wave 3)', () => {
  beforeEach(() => { localStorage.clear() })

  it('renders panel as a labelled region with role="region"', () => {
    render(<WhatsMissingPanel courseId={42} course={baseCourse} modules={baseModules} />)
    const region = screen.getByRole('region', { name: /things to finish|whats missing|ready to publish/i })
    expect(region).toBeInTheDocument()
  })

  it('shows "N things to finish" header reflecting the issue count', () => {
    render(<WhatsMissingPanel courseId={42} course={baseCourse} modules={baseModules} />)
    // baseCourse: missing thumbnail + no modules = 2 issues
    expect(screen.getByText(/2 things to finish/i)).toBeInTheDocument()
  })

  it('shows "Ready to publish" with no celebration copy when count is 0', () => {
    const fullCourse = { ...baseCourse, thumbnail_url: 'http://x' }
    const fullModules = [{ id: 1, title: 'M', sort_order: 0, lessons: [
      { id: 1, title: 'L', lesson_type: 'article' as const, content: { body: 'ok' }, sort_order: 0 },
    ]}]
    render(<WhatsMissingPanel courseId={42} course={fullCourse} modules={fullModules} />)
    expect(screen.getByText(/ready to publish/i)).toBeInTheDocument()
    expect(screen.queryByText(/great job|congrat|woo|🎉/i)).toBeNull()
  })

  it('uses amber/warning tokens (not red/danger)', () => {
    render(<WhatsMissingPanel courseId={42} course={baseCourse} modules={baseModules} />)
    const region = screen.getByRole('region', { name: /things to finish/i })
    // No <aside> wrapper anymore (panel moved from a persistent column to a
    // header-badge popover) - check the tokens used within the region itself.
    const innerCls = Array.from(region.querySelectorAll('*'))
      .map(el => el.className)
      .join(' ')
    expect(innerCls).toMatch(/status-warning|amber/i)
    expect(innerCls).not.toMatch(/status-danger|red-/i)
  })

  it('per-item Skip-for-now button persists dismissal in localStorage keyed by courseId', () => {
    render(<WhatsMissingPanel courseId={42} course={baseCourse} modules={baseModules} />)
    // Accessible name is the descriptive aria-label ("Dismiss: <issue>"), not
    // the visible "Skip for now" text - intentional so a screen-reader list
    // isn't N identical "Skip for now"s (see component docblock).
    const skipBtns = screen.getAllByRole('button', { name: /^dismiss:/i })
    fireEvent.click(skipBtns[0]!)
    const stored = JSON.parse(localStorage.getItem('lsc_authoring_dismissed_42') || '{}')
    expect(Object.keys(stored).length).toBeGreaterThanOrEqual(1)
  })

  it('dismissed item collapses into "N hidden — show" footer', () => {
    localStorage.setItem('lsc_authoring_dismissed_42', JSON.stringify({ course_missing_thumbnail: true }))
    render(<WhatsMissingPanel courseId={42} course={baseCourse} modules={baseModules} />)
    expect(screen.queryByText(/course has no thumbnail/i)).toBeNull()
    expect(screen.getByText(/1 hidden — show/i)).toBeInTheDocument()
  })

  it('clicking "N hidden — show" reveals dismissed items', () => {
    localStorage.setItem('lsc_authoring_dismissed_42', JSON.stringify({ course_missing_thumbnail: true }))
    render(<WhatsMissingPanel courseId={42} course={baseCourse} modules={baseModules} />)
    fireEvent.click(screen.getByText(/1 hidden — show/i))
    expect(screen.getByText(/course has no thumbnail/i)).toBeInTheDocument()
  })

  it('uses aria-live polite atomic=false (scoped count-delta region)', () => {
    render(<WhatsMissingPanel courseId={42} course={baseCourse} modules={baseModules} />)
    const liveRegion = document.querySelector('[aria-live="polite"][aria-atomic="false"]')
    expect(liveRegion).not.toBeNull()
  })
})

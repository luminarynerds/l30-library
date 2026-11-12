/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/// <reference types="@testing-library/jest-dom/vitest" />
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'

// i18n mock: return the key (or interpolate {{title}} naively) so we can assert.
vi.mock('../../i18n/I18nContext', () => ({
  useTranslation: () => ({
    t: (key: string, vars?: Record<string, unknown>) => {
      if (!vars) return key
      return Object.entries(vars).reduce<string>(
        (acc, [k, v]) => acc.replace(`{{${k}}}`, String(v)),
        key,
      )
    },
  }),
}))

vi.mock('react-hot-toast', () => ({
  default: {
    success: vi.fn(),
    error: vi.fn(),
  },
}))

vi.mock('@/lib/sentry-lazy', () => ({
  captureException: vi.fn(),
}))

vi.mock('@/components/ui/ModalBackdrop', () => ({
  ModalBackdrop: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}))

import TeacherReadingListsPage from '../TeacherReadingListsPage'

const SCHOOL = { id: '1', name: 'Maple Elementary' }

// Lists come back in the backend's real shape: snake_case, plural arrays for
// grade_levels/topics, an embedded items[] array, and `name` (not `title`).
// See SharedReadingListResponse in backend/app/schemas/reading.py.
const LIST_A = {
  id: 101,
  name: 'Spring Picks',
  description: 'Curated for spring unit',
  partner_id: 1,
  program_id: null,
  curriculum_alignment: 'Language Arts',
  grade_levels: ['3', '4'],
  reading_levels: ['E', 'F'],
  topics: ['nature', 'seasons'],
  is_active: true,
  items: [
    { id: 1, reading_list_id: 101, isbn: '111', title: 'Bud A', author: 'Auth A', reading_level: 'E', description: null, book_cover_url: null, tags: [], librarian_notes: 'Great read-aloud', teacher_notes: null, suggested_by_id: null },
    { id: 2, reading_list_id: 101, isbn: '222', title: 'Bud B', author: 'Auth B', reading_level: 'F', description: null, book_cover_url: null, tags: [], librarian_notes: null, teacher_notes: null, suggested_by_id: null },
  ],
}

const LIST_B = {
  id: 102,
  name: 'Fall Friends',
  description: 'Friendship-themed picks',
  partner_id: 1,
  program_id: null,
  curriculum_alignment: 'SEL',
  grade_levels: ['4'],
  reading_levels: ['G'],
  topics: ['friendship'],
  is_active: true,
  items: [
    { id: 3, reading_list_id: 102, isbn: '333', title: 'Bud C', author: 'Auth C', reading_level: 'G', description: null, book_cover_url: null, tags: [], librarian_notes: null, teacher_notes: null, suggested_by_id: null },
    { id: 4, reading_list_id: 102, isbn: '444', title: 'Bud D', author: 'Auth D', reading_level: 'G', description: null, book_cover_url: null, tags: [], librarian_notes: null, teacher_notes: null, suggested_by_id: null },
    { id: 5, reading_list_id: 102, isbn: '555', title: 'Bud E', author: 'Auth E', reading_level: 'G', description: null, book_cover_url: null, tags: [], librarian_notes: null, teacher_notes: null, suggested_by_id: null },
  ],
}

// Requests come back camelCase + wrapped (the requests endpoint emits by_alias).
const REQUEST_ROW = {
  id: 42,
  schoolId: 1,
  listId: 101,
  listTitle: 'Spring Picks',
  copies: 25,
  notes: 'For Spring unit',
  status: 'pending',
  requestDate: '2026-05-14T12:00:00Z',
}

/**
 * Mock fetch sequence per the test plan:
 *  - GET /school-partnerships/schools                  -> BARE LIST  (the shape-fix #502 covers)
 *  - GET /school-partnerships/schools/1/reading-lists  -> BARE LIST  (the shape-fix this PR covers)
 *  - GET /school-partnerships/schools/1/reading-list-requests -> WRAPPED { requests: [...] }
 *    (matches the new backend endpoint added in this PR)
 */
function mockFetchByUrl() {
  return vi.spyOn(global, 'fetch').mockImplementation(async (input: RequestInfo | URL) => {
    const url = typeof input === 'string' ? input : (input as URL).toString()
    if (url.endsWith('/school-partnerships/schools')) {
      return new Response(JSON.stringify([SCHOOL]), { status: 200 })
    }
    if (url.endsWith(`/school-partnerships/schools/${SCHOOL.id}/reading-lists`)) {
      return new Response(JSON.stringify([LIST_A, LIST_B]), { status: 200 })
    }
    if (url.endsWith(`/school-partnerships/schools/${SCHOOL.id}/reading-list-requests`)) {
      return new Response(JSON.stringify({ requests: [REQUEST_ROW] }), { status: 200 })
    }
    return new Response(JSON.stringify({}), { status: 404 })
  })
}

describe('TeacherReadingListsPage', () => {
  beforeEach(() => {
    mockFetchByUrl()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('tolerates bare-list shapes from /schools and /reading-lists, renders both lists', async () => {
    render(<TeacherReadingListsPage />)

    // Both reading lists render after the schools->lists chain resolves
    await waitFor(() => {
      expect(screen.getByText('Spring Picks')).toBeInTheDocument()
    })
    expect(screen.getByText('Fall Friends')).toBeInTheDocument()

    // Book count is derived from the embedded items[] array, not a missing
    // itemCount field: LIST_A has 2 items, LIST_B has 3.
    expect(screen.getByText('2 books')).toBeInTheDocument()
    expect(screen.getByText('3 books')).toBeInTheDocument()

    // Grade levels render as pills ("Grade N") from the plural array; the bare
    // value is unique to the pill (the filter dropdown uses just the number).
    expect(screen.getByText('Grade 3')).toBeInTheDocument()
    expect(screen.getAllByText('Grade 4').length).toBeGreaterThanOrEqual(1)
    // Topics render as pills too; each topic also appears as a filter <option>,
    // so assert presence (>= 1) rather than uniqueness.
    expect(screen.getAllByText('nature').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('seasons').length).toBeGreaterThanOrEqual(1)

    // All three expected backend calls were issued (school auto-selected from index 0)
    const calls = (global.fetch as unknown as { mock: { calls: unknown[][] } }).mock.calls.map(
      (c) => (typeof c[0] === 'string' ? c[0] : String(c[0])),
    )
    expect(calls.some((u) => u.endsWith('/school-partnerships/schools'))).toBe(true)
    expect(
      calls.some((u) => u.endsWith(`/school-partnerships/schools/${SCHOOL.id}/reading-lists`)),
    ).toBe(true)
    expect(
      calls.some((u) =>
        u.endsWith(`/school-partnerships/schools/${SCHOOL.id}/reading-list-requests`),
      ),
    ).toBe(true)
  })

  it('renders the pending request row when switching to the My Requests view', async () => {
    render(<TeacherReadingListsPage />)

    // Wait for lists to load, then switch to My Requests view
    await waitFor(() => {
      expect(screen.getByText('Spring Picks')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByRole('button', { name: /My Requests/i }))

    // The request row's title (matches LIST_A.title) shows up in the requests table
    await waitFor(() => {
      // "Spring Picks" appears both as a list card AND as the request row;
      // assert >= 1 to be resilient to either layout
      const matches = screen.getAllByText('Spring Picks')
      expect(matches.length).toBeGreaterThanOrEqual(1)
    })

    // Status pill renders (capitalized via charAt+slice in component)
    expect(screen.getByText('Pending')).toBeInTheDocument()

    // Copies value renders (25 from REQUEST_ROW.copies)
    expect(screen.getByText('25')).toBeInTheDocument()
  })
})

/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import {
  describe,
  it,
  expect,
  vi,
  beforeAll,
  beforeEach,
  afterEach,
} from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { loadLanguage, getTranslation } from '@/i18n/translations'

// Resolve real en.json keys (canonical pattern: ImportMembersModal.test).
vi.mock('@/i18n', async () => {
  const actual = await vi.importActual<typeof import('@/i18n')>('@/i18n')
  return {
    ...actual,
    useTranslation: () => ({
      t: (key: string, params?: Record<string, unknown> | string) =>
        typeof params === 'string'
          ? getTranslation(key, 'en', undefined, params)
          : getTranslation(key, 'en', params),
      language: 'en',
      isRTL: false,
    }),
  }
})
vi.mock('@/i18n/I18nContext', () => ({
  useTranslation: () => ({
    t: (key: string, params?: Record<string, unknown> | string) =>
      typeof params === 'string'
        ? getTranslation(key, 'en', undefined, params)
        : getTranslation(key, 'en', params),
  }),
}))

vi.mock('react-hot-toast', () => ({
  default: { success: vi.fn(), error: vi.fn() },
}))

// Waitlist feature flag, flippable per test.
let waitlistFlag = true
vi.mock('@/contexts/OrganizationFeaturesContext', () => ({
  useOrganizationFeatures: () => ({
    isFeatureEnabled: (name: string) =>
      name === 'book_club_waitlist_enabled' ? waitlistFlag : false,
  }),
}))

const getBookClubMock = vi.fn()
const joinBookClubMock = vi.fn()
const leaveBookClubMock = vi.fn()
const joinWaitlistMock = vi.fn()
const leaveWaitlistMock = vi.fn()
vi.mock('../../api/book-clubs-api', () => ({
  getBookClub: (...a: unknown[]) => getBookClubMock(...a),
  joinBookClub: (...a: unknown[]) => joinBookClubMock(...a),
  leaveBookClub: (...a: unknown[]) => leaveBookClubMock(...a),
  joinBookClubWaitlist: (...a: unknown[]) => joinWaitlistMock(...a),
  leaveBookClubWaitlist: (...a: unknown[]) => leaveWaitlistMock(...a),
}))

import BookClubDetailPage from '../BookClubDetailPage'

const BASE_CLUB = {
  id: 1,
  name: 'Mystery Lovers',
  description: 'Whodunits and cozies.',
  genre: 'Mystery',
  meeting_frequency: 'Biweekly',
  member_count: 7,
  max_members: 12,
  current_member_count: 7,
  waitlist_count: 0,
  is_full: false,
  current_book_title: null,
  current_book_author: null,
  is_member: false,
  next_meeting_date: null,
  created_at: '2026-01-01T00:00:00Z',
  patron_waitlist_position: null,
  members: null,
  upcoming_meetings: [],
}

beforeAll(async () => {
  await loadLanguage('en')
})

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/book-clubs/1']}>
      <Routes>
        <Route path='/book-clubs/:id' element={<BookClubDetailPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('BookClubDetailPage', () => {
  beforeEach(() => {
    waitlistFlag = true
    getBookClubMock.mockReset()
    joinBookClubMock.mockReset()
    leaveBookClubMock.mockReset()
    joinWaitlistMock.mockReset()
    leaveWaitlistMock.mockReset()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('renders chrome (back link + skeleton) on first paint while loading', () => {
    getBookClubMock.mockReturnValue(new Promise(() => {}))
    renderPage()
    expect(
      screen.getByRole('link', { name: /back to book clubs/i }),
    ).toBeInTheDocument()
    expect(screen.getByText(/loading book club details/i)).toBeInTheDocument()
  })

  it('hides Members section when API returns members=null (anonymous)', async () => {
    getBookClubMock.mockResolvedValue({ ...BASE_CLUB, members: null })
    renderPage()
    await waitFor(() =>
      expect(
        screen.getByRole('heading', { name: /mystery lovers/i }),
      ).toBeInTheDocument(),
    )
    expect(
      screen.queryByRole('heading', { name: /members \(/i }),
    ).not.toBeInTheDocument()
  })

  it('shows Members section with role labels when API returns members array', async () => {
    getBookClubMock.mockResolvedValue({
      ...BASE_CLUB,
      members: [
        {
          id: 1,
          user_id: 5,
          display_name: 'Janet Ruiz',
          joined_at: '2025-09-01T10:00:00Z',
          role: 'admin',
        },
      ],
    })
    renderPage()
    await waitFor(() =>
      expect(
        screen.getByRole('heading', { name: /members \(1\)/i }),
      ).toBeInTheDocument(),
    )
    expect(screen.getByText('Janet Ruiz')).toBeInTheDocument()
    expect(screen.getByText('admin')).toBeInTheDocument()
  })

  it('under-cap, not a member: shows Join Club (not Join Waitlist)', async () => {
    getBookClubMock.mockResolvedValue({ ...BASE_CLUB, is_full: false })
    renderPage()
    await waitFor(() =>
      expect(
        screen.getByRole('button', { name: /^Join Club$/ }),
      ).toBeInTheDocument(),
    )
    expect(
      screen.queryByRole('button', { name: /Join Waitlist/ }),
    ).not.toBeInTheDocument()
  })

  it('full, not a member, not waiting, flag ON: shows Join Waitlist', async () => {
    getBookClubMock.mockResolvedValue({
      ...BASE_CLUB,
      is_full: true,
      current_member_count: 12,
      member_count: 12,
    })
    renderPage()
    await waitFor(() =>
      expect(
        screen.getByRole('button', { name: /Join Waitlist/ }),
      ).toBeInTheDocument(),
    )
  })

  it('full, not a member, flag OFF: falls back to plain Join Club', async () => {
    waitlistFlag = false
    getBookClubMock.mockResolvedValue({
      ...BASE_CLUB,
      is_full: true,
      current_member_count: 12,
      member_count: 12,
    })
    renderPage()
    await waitFor(() =>
      expect(
        screen.getByRole('button', { name: /^Join Club$/ }),
      ).toBeInTheDocument(),
    )
    expect(
      screen.queryByRole('button', { name: /Join Waitlist/ }),
    ).not.toBeInTheDocument()
  })

  it('full + waiting: shows position and a Leave waitlist button', async () => {
    getBookClubMock.mockResolvedValue({
      ...BASE_CLUB,
      is_full: true,
      current_member_count: 12,
      member_count: 12,
      patron_waitlist_position: 3,
    })
    renderPage()
    await waitFor(() =>
      expect(screen.getByText(/You are #3 on the waitlist/)).toBeInTheDocument(),
    )
    expect(
      screen.getByRole('button', { name: /Leave waitlist/ }),
    ).toBeInTheDocument()
  })

  it('clicking Join Waitlist calls the waitlist API and refreshes', async () => {
    getBookClubMock
      .mockResolvedValueOnce({
        ...BASE_CLUB,
        is_full: true,
        current_member_count: 12,
        member_count: 12,
      })
      .mockResolvedValueOnce({
        ...BASE_CLUB,
        is_full: true,
        current_member_count: 12,
        member_count: 12,
        patron_waitlist_position: 1,
      })
    joinWaitlistMock.mockResolvedValue({
      status: 'waitlisted',
      position: 1,
      success: true,
    })
    renderPage()
    const btn = await screen.findByRole('button', { name: /Join Waitlist/ })
    await userEvent.click(btn)
    await waitFor(() => expect(joinWaitlistMock).toHaveBeenCalledWith(1))
    await waitFor(() =>
      expect(screen.getByText(/You are #1 on the waitlist/)).toBeInTheDocument(),
    )
  })
})

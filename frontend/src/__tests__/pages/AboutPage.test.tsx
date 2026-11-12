/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '../utils/test-utils'
import AboutPage from '@/pages/AboutPage'
import * as bookChallengesApi from '@/api/book-challenges-api'
import * as branchApi from '@/api/branch-api'
import * as communityApi from '@/api/domains/services/community-api'

vi.mock('@/api/book-challenges-api')
vi.mock('@/api/branch-api')
vi.mock('@/api/domains/services/community-api', async () => {
  const actual = await vi.importActual<typeof communityApi>(
    '@/api/domains/services/community-api'
  )
  return {
    ...actual,
    getStaffBios: vi.fn(),
  }
})

const mockStats: bookChallengesApi.BookChallengeStats = {
  total_challenges: 5,
  pending_challenges: 1,
  resolved_this_year: 4,
  outcomes: {
    retained: 4,
    removed: 1,
    restricted: 0,
  },
  reasons: {
    LGBTQ_CONTENT: 2,
    SEXUAL_CONTENT: 1,
    LANGUAGE: 2,
  },
  available_years: [],
}

const mockBranches: branchApi.Branch[] = [
  {
    id: 1,
    name: 'Main Library',
    code: 'MAIN',
    address: '123 Main St',
    city: 'Springfield',
    state: 'IL',
    zip_code: '62701',
    phone: '555-0100',
    email: null,
    hours: null,
    is_active: true,
    is_bookmobile: false,
    created_at: new Date().toISOString(),
  } as unknown as branchApi.Branch,
  {
    id: 2,
    name: 'Eastside Branch',
    code: 'EAST',
    address: '456 East Rd',
    city: 'Springfield',
    state: 'IL',
    zip_code: '62702',
    phone: '555-0200',
    email: null,
    hours: null,
    is_active: true,
    is_bookmobile: false,
    created_at: new Date().toISOString(),
  } as unknown as branchApi.Branch,
]

const mockStaff = [
  {
    id: 1,
    staff_name: 'Alice Example',
    role: 'Director',
    bio: 'Runs the place.',
    photo_url: null,
    email: null,
    sort_order: 0,
  },
  {
    id: 2,
    staff_name: 'Bob Example',
    role: 'Librarian',
    bio: 'Helps patrons.',
    photo_url: null,
    email: null,
    sort_order: 1,
  },
]

describe('AboutPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(bookChallengesApi.getPublicStats).mockResolvedValue(mockStats)
    vi.mocked(branchApi.listBranches).mockResolvedValue(mockBranches)
    vi.mocked(communityApi.getStaffBios).mockResolvedValue(
      mockStaff as unknown as communityApi.StaffBio[]
    )
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('should render the page with main sections', async () => {
    render(<AboutPage />)

    // Section headings present in the current AboutPage layout (post-rewrite)
    await waitFor(() => {
      expect(screen.getAllByText(/How We Got Here/i).length).toBeGreaterThan(0)
    })
    expect(screen.getAllByText(/Meet the Staff/i).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/Our Locations/i).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/Transparency Report/i).length).toBeGreaterThan(0)
  })

  it('should render without crashing during initial load', () => {
    vi.mocked(bookChallengesApi.getPublicStats).mockImplementation(
      () => new Promise(() => {})
    )
    render(<AboutPage />)

    // Page shell always renders (StandardPageLayout title)
    expect(screen.getAllByText(/How We Got Here/i).length).toBeGreaterThan(0)
  })

  it('should load and display challenge statistics', async () => {
    render(<AboutPage />)

    await waitFor(() => {
      // total_challenges (5) displayed in transparency report
      expect(screen.getByText('5')).toBeInTheDocument()
    })
    // retained (4) and removed (1)
    expect(screen.getByText('4')).toBeInTheDocument()
    expect(screen.getByText('1')).toBeInTheDocument()
  })

  it('should fall back to placeholder values on stats error', async () => {
    vi.mocked(bookChallengesApi.getPublicStats).mockRejectedValue(
      new Error('fail')
    )

    render(<AboutPage />)

    // On error the component falls back to '---' placeholders
    await waitFor(() => {
      expect(screen.getAllByText('---').length).toBeGreaterThan(0)
    })
  })

  it('should call getPublicStats on mount', async () => {
    render(<AboutPage />)

    await waitFor(() => {
      expect(bookChallengesApi.getPublicStats).toHaveBeenCalledTimes(1)
    })
  })

  it('should handle missing outcome data gracefully', async () => {
    const statsWithMissingOutcomes: bookChallengesApi.BookChallengeStats = {
      total_challenges: 3,
      pending_challenges: 0,
      resolved_this_year: 3,
      outcomes: {},
      reasons: {},
      available_years: [],
    }

    vi.mocked(bookChallengesApi.getPublicStats).mockResolvedValue(
      statsWithMissingOutcomes
    )
    render(<AboutPage />)

    await waitFor(() => {
      expect(screen.getByText('3')).toBeInTheDocument()
    })
    // Missing outcomes should render as 0s
    const zeros = screen.getAllByText('0')
    expect(zeros.length).toBeGreaterThan(0)
  })

  it('should render staff members section with staff from API', async () => {
    render(<AboutPage />)

    // AboutLibraryContent abbreviates staff last names to an initial for
    // privacy (formatDisplayName, #270): "Alice Example" -> "Alice E.".
    await waitFor(() => {
      expect(screen.getByText('Alice E.')).toBeInTheDocument()
    })
    expect(screen.getByText('Bob E.')).toBeInTheDocument()
  })

  it('should display library locations from API', async () => {
    render(<AboutPage />)

    await waitFor(() => {
      expect(screen.getByText('Main Library')).toBeInTheDocument()
    })
    expect(screen.getByText('Eastside Branch')).toBeInTheDocument()
  })

  it('should display roadmap/timeline years', async () => {
    render(<AboutPage />)

    // The "Coming Up" roadmap (about-roadmap section) uses season markers,
    // not quarter labels: Summer/Fall/Winter 2026, then 2027.
    await waitFor(() => {
      expect(screen.getAllByText(/Summer 2026/i).length).toBeGreaterThan(0)
    })
    expect(screen.getAllByText(/2027/i).length).toBeGreaterThan(0)
  })
})

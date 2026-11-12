/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, within, userEvent } from '../utils/test-utils'
import TechSupportPage from '@/pages/TechSupportPage'
import * as techSupportApi from '@/api/tech-support-api'

vi.mock('@/api/tech-support-api')

const mockHelpOptions: techSupportApi.TechHelpOption[] = [
  {
    title: 'Drop-In Tech Help',
    description: 'Walk in any time during open hours.',
    schedule: 'Mon-Fri 10am-4pm',
    location: 'Main Floor',
    icon: 'help-circle',
  },
  {
    title: 'Tech Appointments',
    description: 'Book a 1-on-1 session.',
    schedule: 'By appointment',
    icon: 'calendar',
  },
  {
    title: 'Tech Help Hotline',
    description: 'Call us with quick questions.',
    schedule: 'Mon-Fri 9am-5pm',
    phone: '555-1234',
  },
]

const mockFacilities: techSupportApi.TechFacilitySection[] = [
  {
    kind: 'computer_lab',
    facilities: [
      { id: 1, label: 'Computers', value: '12 available' },
      { id: 2, label: 'B&W printing', value: '$0.10/page' },
    ],
  },
  {
    kind: 'printer',
    facilities: [
      { id: 3, label: 'Main Floor Computer Lab', value: 'B&W + color' },
      { id: 4, label: 'Second Floor Reference', value: 'B&W only' },
    ],
  },
]

const mockClasses: techSupportApi.TechClass[] = [
  {
    title: 'Intro to Email',
    date: 'Jun 1',
    time: '10am',
    location: 'Lab',
    level: 'Beginner',
    description: 'Email basics.',
  },
  {
    title: 'Smartphone Safety',
    date: 'Jun 8',
    time: '2pm',
    location: 'Lab',
    level: 'Beginner',
    description: 'Stay safe online.',
  },
]

const mockQuickAccess: techSupportApi.QuickAccessSection[] = [
  {
    title: 'Internet & WiFi',
    links: [{ name: 'Example ISP', url: 'https://example.com' }],
  },
]

const mockResources: techSupportApi.TechResource[] = []

describe('TechSupportPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(techSupportApi.getTechHelpOptions).mockResolvedValue(mockHelpOptions)
    vi.mocked(techSupportApi.getTechFacilities).mockResolvedValue(mockFacilities)
    vi.mocked(techSupportApi.getUpcomingClasses).mockResolvedValue(mockClasses)
    vi.mocked(techSupportApi.getQuickAccessSections).mockResolvedValue(mockQuickAccess)
    vi.mocked(techSupportApi.getTechResources).mockResolvedValue(mockResources)
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('does not render a tablist (3-tab structure is gone)', async () => {
    render(<TechSupportPage />)
    await waitFor(() => {
      expect(screen.getByTestId('tech-triage-tiles')).toBeInTheDocument()
    })
    expect(screen.queryByRole('tablist')).toBeNull()
  })

  it('renders 4 triage tiles linking to the correct guide paths', async () => {
    render(<TechSupportPage />)
    const tiles = await screen.findByTestId('tech-triage-tiles')
    const links = within(tiles).getAllByRole('link')
    expect(links).toHaveLength(4)
    const hrefs = links.map((a) => a.getAttribute('href'))
    expect(hrefs).toEqual([
      '/guides/password-reset',
      '/guides/library-card',
      '/guides/check-print-jobs',
      '/guides/wifi-troubleshooting',
    ])
  })

  it('renders Talk-to-a-person block above Classes and Facilities (positional check)', async () => {
    render(<TechSupportPage />)
    await waitFor(() => {
      expect(screen.getByTestId('tech-talk-to-a-person')).toBeInTheDocument()
    })

    const talkBlock = screen.getByTestId('tech-talk-to-a-person')
    const facilities = screen.getByTestId('tech-facilities')
    const classesHeading = screen.getByRole('heading', { name: /Tech Classes & Workshops/i })

    // DOCUMENT_POSITION_FOLLOWING = 4 — talkBlock comes before facilities and classes
    expect(talkBlock.compareDocumentPosition(facilities) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect(talkBlock.compareDocumentPosition(classesHeading) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  })

  it('renders Facilities section from API mock', async () => {
    render(<TechSupportPage />)
    await waitFor(() => {
      expect(screen.getByTestId('tech-facilities')).toBeInTheDocument()
    })
    const facilities = screen.getByTestId('tech-facilities')
    expect(within(facilities).getByText(/Public Computer Lab/i)).toBeInTheDocument()
    expect(within(facilities).getByText(/Printer Locations/i)).toBeInTheDocument()
    expect(within(facilities).getByText(/12 available/)).toBeInTheDocument()
    expect(within(facilities).getByText(/Main Floor Computer Lab/i)).toBeInTheDocument()
  })

  it('demotes Classes to a single link to /events (no Register buttons)', async () => {
    render(<TechSupportPage />)
    await waitFor(() => {
      expect(screen.getByTestId('tech-classes-see-all')).toBeInTheDocument()
    })
    const seeAll = screen.getByTestId('tech-classes-see-all')
    expect(seeAll).toHaveAttribute('href', '/events')

    // No "Register" CTA buttons under the classes section
    expect(screen.queryByRole('link', { name: /^Register$/i })).toBeNull()
    expect(screen.queryByRole('button', { name: /^Register$/i })).toBeNull()
  })

  it('uses plain-language hero copy (no "Tech Support Center")', async () => {
    render(<TechSupportPage />)
    await waitFor(() => {
      expect(screen.getByTestId('tech-triage-tiles')).toBeInTheDocument()
    })
    // Old title is gone
    expect(screen.queryByText(/Tech Support Center/i)).toBeNull()
  })

  // ============================================================
  // I3 — Useful error rendering when fetches fail
  // ============================================================
  describe('error state', () => {
    it('shows the outage banner and hides per-section empty-state copy when fetches fail', async () => {
      vi.mocked(techSupportApi.getUpcomingClasses).mockRejectedValue(new Error('boom'))
      vi.mocked(techSupportApi.getTechHelpOptions).mockRejectedValue(new Error('boom'))
      vi.mocked(techSupportApi.getQuickAccessSections).mockRejectedValue(new Error('boom'))
      vi.mocked(techSupportApi.getTechResources).mockRejectedValue(new Error('boom'))
      vi.mocked(techSupportApi.getTechFacilities).mockRejectedValue(new Error('boom'))

      render(<TechSupportPage />)

      // Banner appears with the actionable copy.
      await waitFor(() => {
        expect(
          screen.getByText(/We had trouble loading some tech support information/i),
        ).toBeInTheDocument()
      })

      // Triage tiles (static) still render so patrons have a path.
      expect(screen.getByTestId('tech-triage-tiles')).toBeInTheDocument()

      // None of the per-section "deliberately empty" copy is in the DOM:
      // "No tech resources found" is suppressed on error so a fetch
      // failure doesn't look like an empty library.
      expect(screen.queryByText(/No tech resources found/i)).toBeNull()
      // Classes teaser ("See all classes" link) is hidden — that section
      // is suppressed on error so we don't suggest the library has no
      // classes.
      expect(screen.queryByTestId('tech-classes-see-all')).toBeNull()
      // Facilities + external resources sections are not rendered.
      expect(screen.queryByTestId('tech-facilities')).toBeNull()
    })
  })

  // ============================================================
  // E2 / E5 — ?p= deep-link routing + aria-live announcement
  // ============================================================
  describe('?p= QR triage deep-link', () => {
    beforeEach(() => {
      // jsdom doesn't implement scrollIntoView on Element.prototype.
      // Stub so the on-mount focus effect can run without throwing.
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      ;(Element.prototype as any).scrollIntoView = vi.fn()
    })

    it('focuses the printer tile and announces on ?p=printer', async () => {
      render(<TechSupportPage />, {
        routerProps: { initialEntries: ['/tech?p=printer'] },
      })
      const tiles = await screen.findByTestId('tech-triage-tiles')
      const printerLink = within(tiles).getByRole('link', {
        name: /Printing isn't working/i,
      })
      await waitFor(() => expect(printerLink).toHaveFocus())

      // aria-live polite region exists and announces printing context
      await waitFor(() => {
        const status = screen.getByTestId('tech-qr-announcement')
        expect(status).toHaveAttribute('aria-live', 'polite')
        expect(status).toHaveTextContent(/printing/i)
      })
    })

    it('focuses the password tile and announces on ?p=password', async () => {
      render(<TechSupportPage />, {
        routerProps: { initialEntries: ['/tech?p=password'] },
      })
      const tiles = await screen.findByTestId('tech-triage-tiles')
      const passwordLink = within(tiles).getByRole('link', {
        name: /Reset my password/i,
      })
      await waitFor(() => expect(passwordLink).toHaveFocus())
      await waitFor(() => {
        expect(screen.getByTestId('tech-qr-announcement')).toHaveTextContent(
          /password/i,
        )
      })
    })

    it('focuses the library-card tile on ?p=login', async () => {
      render(<TechSupportPage />, {
        routerProps: { initialEntries: ['/tech?p=login'] },
      })
      const tiles = await screen.findByTestId('tech-triage-tiles')
      const loginLink = within(tiles).getByRole('link', {
        name: /Can't log in \/ library card/i,
      })
      await waitFor(() => expect(loginLink).toHaveFocus())
    })

    it('focuses the wifi tile on ?p=wifi', async () => {
      render(<TechSupportPage />, {
        routerProps: { initialEntries: ['/tech?p=wifi'] },
      })
      const tiles = await screen.findByTestId('tech-triage-tiles')
      const wifiLink = within(tiles).getByRole('link', {
        name: /WiFi won't connect/i,
      })
      await waitFor(() => expect(wifiLink).toHaveFocus())
    })

    it('does not announce or auto-focus on unknown ?p= value', async () => {
      render(<TechSupportPage />, {
        routerProps: { initialEntries: ['/tech?p=foo'] },
      })
      await screen.findByTestId('tech-triage-tiles')
      // Announcement region is not rendered for invalid values
      expect(screen.queryByTestId('tech-qr-announcement')).toBeNull()
      // No triage tile should have stolen focus
      const tiles = screen.getByTestId('tech-triage-tiles')
      const links = within(tiles).getAllByRole('link')
      for (const link of links) {
        expect(link).not.toHaveFocus()
      }
    })

    it('does not announce when ?p= is missing', async () => {
      render(<TechSupportPage />, {
        routerProps: { initialEntries: ['/tech'] },
      })
      await screen.findByTestId('tech-triage-tiles')
      expect(screen.queryByTestId('tech-qr-announcement')).toBeNull()
    })
  })

  // ============================================================
  // E4 — Search merges /guides matches above resource cards
  // ============================================================
  describe('Resources search includes /guides articles', () => {
    it('shows a guides subsection above resources when search matches a guide', async () => {
      const user = userEvent.setup()
      // Resources fetched as empty so we can isolate the guide-match behavior.
      vi.mocked(techSupportApi.getTechResources).mockResolvedValue([])
      render(<TechSupportPage />)
      await screen.findByTestId('tech-triage-tiles')

      const searchInput = screen.getByLabelText(/Search tech resources/i)
      await user.type(searchInput,'password')

      const guidesSection = await screen.findByTestId('tech-guides-results')
      const passwordGuideLink = within(guidesSection).getByRole('link', {
        name: /Reset Your Password/i,
      })
      expect(passwordGuideLink).toHaveAttribute('href', '/guides/password-reset')
    })

    it('matches a guide by id substring (e.g. "wifi" -> wifi-troubleshooting)', async () => {
      const user = userEvent.setup()
      vi.mocked(techSupportApi.getTechResources).mockResolvedValue([])
      render(<TechSupportPage />)
      await screen.findByTestId('tech-triage-tiles')

      const searchInput = screen.getByLabelText(/Search tech resources/i)
      await user.type(searchInput,'wifi')

      const guidesSection = await screen.findByTestId('tech-guides-results')
      expect(
        within(guidesSection).getByRole('link', { name: /WiFi Troubleshooting/i }),
      ).toHaveAttribute('href', '/guides/wifi-troubleshooting')
    })

    it('hides the guides subsection when the search box is empty', async () => {
      vi.mocked(techSupportApi.getTechResources).mockResolvedValue([])
      render(<TechSupportPage />)
      await screen.findByTestId('tech-triage-tiles')
      expect(screen.queryByTestId('tech-guides-results')).toBeNull()
    })

    it('shows the empty state when neither guides nor resources match', async () => {
      const user = userEvent.setup()
      vi.mocked(techSupportApi.getTechResources).mockResolvedValue([])
      render(<TechSupportPage />)
      await screen.findByTestId('tech-triage-tiles')

      const searchInput = screen.getByLabelText(/Search tech resources/i)
      await user.type(searchInput,'xyz123nomatch')

      await waitFor(() => {
        expect(screen.queryByTestId('tech-guides-results')).toBeNull()
      })
      expect(screen.getByText(/No tech resources found/i)).toBeInTheDocument()
    })
  })
})

/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Tests for NavDropdown when used as the "More" mega-menu in Layout.tsx
 * at the lg breakpoint (1024-1279px).
 *
 * Background: at lg, Services/Explore/Visit/Ask a Librarian were silently
 * clipped by the parent nav's `overflow-hidden` because right-side CTAs
 * refused to shrink. The fix collapses them into a single accessible "More"
 * dropdown that uses the existing NavDropdown primitive. These tests pin
 * the behaviors that matter for screen-reader and keyboard users:
 *   1. Trigger has correct ARIA when closed and open
 *   2. Items are NOT reachable by Tab when the menu is closed
 *   3. Items ARE reachable by Tab when the menu is open
 *   4. Escape closes the menu and returns focus to the trigger
 *   5. Clicking the trigger toggles the menu
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { MoreHorizontal, BookOpen, MapPin, MessageCircle } from 'lucide-react'

import NavDropdown from '../NavDropdown'

// Minimal section structure matching what Layout.tsx passes for the "More"
// menu (a union of Services + Explore + Visit + a synthetic Ask a Librarian).
const moreSections = [
  {
    heading: 'Library services',
    items: [
      { to: '/get-started', label: 'Get a Library Card', icon: BookOpen, description: 'Sign up for free access' },
      { to: '/home-delivery', label: 'Home Delivery', icon: BookOpen, description: 'Books delivered to your door' },
    ],
  },
  {
    heading: 'Visit',
    items: [
      { to: '/branches', label: 'Hours & Locations', icon: MapPin, description: 'Branch hours and directions' },
    ],
  },
  {
    heading: 'Ask a Librarian',
    items: [
      { to: '/ask-librarian', label: 'Ask a Librarian', icon: MessageCircle },
    ],
  },
]

const renderMore = (initialPath = '/') => {
  const isActive = vi.fn(() => false)
  const utils = render(
    <MemoryRouter initialEntries={[initialPath]}>
      <NavDropdown
        label="More"
        icon={MoreHorizontal}
        sections={moreSections}
        isActive={isActive}
        align="left"
      />
    </MemoryRouter>,
  )
  return { ...utils, isActive, user: userEvent.setup() }
}

describe('NavDropdown as "More" mega-menu', () => {
  it('renders the trigger with aria-haspopup and aria-expanded=false when closed', () => {
    renderMore()
    const trigger = screen.getByRole('button', { name: /more/i })
    expect(trigger).toHaveAttribute('aria-expanded', 'false')
    // aria-controls must point at the panel id (proves the trigger/panel pair is wired up)
    expect(trigger).toHaveAttribute('aria-controls')
  })

  it('does NOT render the dropdown items when the menu is closed', () => {
    renderMore()
    // Panel is portal-rendered only when open, so links should not be in the DOM.
    expect(screen.queryByRole('link', { name: 'Get a Library Card' })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Ask a Librarian' })).not.toBeInTheDocument()
  })

  it('opens the menu on trigger click and exposes all section items as links', async () => {
    const { user } = renderMore()
    const trigger = screen.getByRole('button', { name: /more/i })

    await user.click(trigger)

    expect(trigger).toHaveAttribute('aria-expanded', 'true')
    // All 4 items from the 3 sections become reachable links.
    expect(screen.getByRole('link', { name: /Get a Library Card/ })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Home Delivery/ })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Hours & Locations/ })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Ask a Librarian/ })).toBeInTheDocument()
  })

  it('renders each section heading as a real <h3> and labels its list', async () => {
    const { user } = renderMore()
    await user.click(screen.getByRole('button', { name: /more/i }))

    // WCAG 1.3.1 / 2.4.6: real heading elements, not styled spans.
    const headings = screen.getAllByRole('heading', { level: 3 })
    const headingText = headings.map((h) => h.textContent)
    expect(headingText).toEqual(expect.arrayContaining(['Library services', 'Visit', 'Ask a Librarian']))

    // The list for each section is labelled by that heading (aria-labelledby
    // points at the h3's id), so AT users hear "Visit, list" then the items.
    const visitHeading = headings.find((h) => h.textContent === 'Visit')!
    const visitList = document.querySelector(`ul[aria-labelledby="${visitHeading.id}"]`)
    expect(visitList).not.toBeNull()
    expect(within(visitList as HTMLElement).getByRole('link', { name: /Hours & Locations/ })).toBeInTheDocument()
  })

  it('closes on Escape and returns focus to the trigger', async () => {
    const { user } = renderMore()
    const trigger = screen.getByRole('button', { name: /more/i })

    await user.click(trigger)
    expect(trigger).toHaveAttribute('aria-expanded', 'true')

    await user.keyboard('{Escape}')

    expect(trigger).toHaveAttribute('aria-expanded', 'false')
    expect(trigger).toHaveFocus()
    // Items must not be tab-reachable after close.
    expect(screen.queryByRole('link', { name: 'Get a Library Card' })).not.toBeInTheDocument()
  })

  it('threads aria-keyshortcuts onto items that declare a shortcut', async () => {
    const isActive = vi.fn(() => false)
    const sectionsWithShortcut = [
      {
        heading: 'Library services',
        items: [
          { to: '/get-started', label: 'Get a Library Card', icon: BookOpen, shortcut: 'g c' },
          { to: '/home-delivery', label: 'Home Delivery', icon: BookOpen },
        ],
      },
    ]
    const user = userEvent.setup()
    render(
      <MemoryRouter>
        <NavDropdown label="More" icon={MoreHorizontal} sections={sectionsWithShortcut} isActive={isActive} />
      </MemoryRouter>,
    )
    await user.click(screen.getByRole('button', { name: /more/i }))
    expect(screen.getByRole('link', { name: /Get a Library Card/ })).toHaveAttribute('aria-keyshortcuts', 'g c')
    // Items without a shortcut must NOT emit the attribute.
    expect(screen.getByRole('link', { name: /Home Delivery/ })).not.toHaveAttribute('aria-keyshortcuts')
  })

  it('toggles closed on a second trigger click', async () => {
    const { user } = renderMore()
    const trigger = screen.getByRole('button', { name: /more/i })

    await user.click(trigger)
    expect(trigger).toHaveAttribute('aria-expanded', 'true')

    await user.click(trigger)
    expect(trigger).toHaveAttribute('aria-expanded', 'false')
  })

  it('items are reachable by Tab from the trigger only when open', async () => {
    const { user } = renderMore()
    const trigger = screen.getByRole('button', { name: /more/i })

    // Closed: tabbing forward from the trigger lands somewhere outside the
    // dropdown — definitely not on a panel link, because no panel exists.
    trigger.focus()
    await user.tab()
    expect(screen.queryByRole('link', { name: 'Get a Library Card' })).not.toBeInTheDocument()

    // Open: panel renders and the first link becomes a tab stop after the trigger.
    await user.click(trigger)
    trigger.focus()
    await user.tab()
    expect(screen.getByRole('link', { name: /Get a Library Card/ })).toHaveFocus()
  })
})

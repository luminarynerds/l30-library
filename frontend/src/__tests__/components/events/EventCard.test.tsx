/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Tests for EventCard Component
 *
 * Tests event display, interactions, and accessibility
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import EventCard from '../../../components/events/EventCard'
import { createMockEvent } from '../../helpers/testHelpers'

describe('EventCard', () => {
  const mockEvent = createMockEvent({
    title: 'Book Club Meeting',
    description: 'Monthly book club discussion',
    start_time: '2026-02-15T18:00:00Z',
    end_time: '2026-02-15T20:00:00Z',
    location: 'Main Library',
    audience: 'adults',
    category: 'book-club',
    max_attendees: 30,
    registration_required: true,
    registration_count: 15,
    spots_remaining: 15,
  })
  const mockOnRegister = vi.fn()
  const mockOnClick = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  // ========== RENDERING TESTS ==========

  describe('Rendering', () => {
    it('renders event card with title', () => {
      render(<EventCard event={mockEvent} onRegister={mockOnRegister} onClick={mockOnClick} />)
      expect(screen.getByText('Book Club Meeting')).toBeInTheDocument()
    })

    it('displays event description', () => {
      render(<EventCard event={mockEvent} onRegister={mockOnRegister} onClick={mockOnClick} />)
      expect(screen.getByText('Monthly book club discussion')).toBeInTheDocument()
    })

    it('shows event date and time', () => {
      render(<EventCard event={mockEvent} onRegister={mockOnRegister} onClick={mockOnClick} />)
      // Date badge renders the month (abbreviated) and day-of-month separately
      expect(screen.getByText(/^(Feb|February)$/)).toBeInTheDocument()
      expect(screen.getByText('15')).toBeInTheDocument()
    })

    it('displays event location', () => {
      render(<EventCard event={mockEvent} onRegister={mockOnRegister} onClick={mockOnClick} />)
      expect(screen.getByText('Main Library')).toBeInTheDocument()
    })

    it('displays event audience', () => {
      render(<EventCard event={mockEvent} onRegister={mockOnRegister} onClick={mockOnClick} />)
      expect(screen.getByText('adults')).toBeInTheDocument()
    })

    it('shows capacity information', () => {
      render(<EventCard event={mockEvent} onRegister={mockOnRegister} onClick={mockOnClick} />)
      expect(screen.getByText('15 of 30 spots available')).toBeInTheDocument()
    })

    it('renders the event category chip', () => {
      render(<EventCard event={mockEvent} onRegister={mockOnRegister} onClick={mockOnClick} />)
      expect(screen.getByText('book-club')).toBeInTheDocument()
    })

    it('shows registration count when there are registrants', () => {
      render(<EventCard event={mockEvent} onRegister={mockOnRegister} onClick={mockOnClick} />)
      expect(screen.getByText('15 registered')).toBeInTheDocument()
    })

    it('omits capacity info entirely for events with no attendee cap', () => {
      const uncapped = createMockEvent({ max_attendees: null })
      render(<EventCard event={uncapped} onRegister={mockOnRegister} onClick={mockOnClick} />)
      expect(screen.queryByText(/spots available/i)).not.toBeInTheDocument()
    })
  })

  // ========== STATUS INDICATORS TESTS ==========

  describe('Status Indicators', () => {
    it('shows a waitlist-framed message when capacity is reached', () => {
      const soldOut = createMockEvent({ registration_count: 30, max_attendees: 30, spots_remaining: 0 })
      render(<EventCard event={soldOut} onRegister={mockOnRegister} onClick={mockOnClick} />)
      expect(screen.getByText(/full \(you can join the waitlist\)/i)).toBeInTheDocument()
    })

    it('shows remaining spots when capacity is nearly reached', () => {
      const almostFull = createMockEvent({ registration_count: 27, max_attendees: 30, spots_remaining: 3 })
      render(<EventCard event={almostFull} onRegister={mockOnRegister} onClick={mockOnClick} />)
      expect(screen.getByText('3 of 30 spots available')).toBeInTheDocument()
    })

    it('shows a "you\'re registered" indicator when the patron is already registered', () => {
      render(<EventCard event={mockEvent} onRegister={mockOnRegister} onClick={mockOnClick} isRegistered />)
      expect(screen.getByText("You're registered")).toBeInTheDocument()
    })
  })

  // ========== INTERACTION TESTS ==========

  describe('User Interactions', () => {
    it('has a register button when registration is required and the patron is not yet registered', () => {
      render(<EventCard event={mockEvent} onRegister={mockOnRegister} onClick={mockOnClick} />)
      const registerButton = screen.getByRole('button', { name: /^register$/i })
      expect(registerButton).toBeInTheDocument()
    })

    it('handles register button click without triggering the card onClick', async () => {
      const user = userEvent.setup()
      const onRegister = vi.fn()
      render(<EventCard event={mockEvent} onRegister={onRegister} onClick={mockOnClick} />)

      const registerButton = screen.getByRole('button', { name: /^register$/i })
      await user.click(registerButton)

      expect(onRegister).toHaveBeenCalledWith(mockEvent)
      expect(mockOnClick).not.toHaveBeenCalled()
    })

    it('relabels the register button to "Waitlist" (not disabled) when the event is full', async () => {
      const user = userEvent.setup()
      const onRegister = vi.fn()
      const fullEvent = createMockEvent({ registration_count: 30, max_attendees: 30, spots_remaining: 0 })
      render(<EventCard event={fullEvent} onRegister={onRegister} onClick={mockOnClick} />)

      const waitlistButton = screen.getByRole('button', { name: /^waitlist$/i })
      expect(waitlistButton).not.toBeDisabled()

      await user.click(waitlistButton)
      expect(onRegister).toHaveBeenCalledWith(fullEvent)
    })

    it('hides the register button once the patron is registered', () => {
      render(<EventCard event={mockEvent} onRegister={mockOnRegister} onClick={mockOnClick} isRegistered />)
      expect(screen.queryByRole('button', { name: /^register$/i })).not.toBeInTheDocument()
    })

    it('shows a save (bookmark) button when registration is not blocking it', () => {
      render(
        <EventCard
          event={mockEvent}
          onRegister={mockOnRegister}
          onClick={mockOnClick}
          isRegistered
          onToggleBookmark={vi.fn()}
        />
      )
      const saveButton = screen.getByRole('button', { name: /save book club meeting for later/i })
      expect(saveButton).toBeInTheDocument()
    })

    it('hides the bookmark button while an unregistered patron still needs to register (avoids button overlap)', () => {
      render(
        <EventCard
          event={mockEvent}
          onRegister={mockOnRegister}
          onClick={mockOnClick}
          onToggleBookmark={vi.fn()}
        />
      )
      expect(screen.queryByRole('button', { name: /save|remove/i })).not.toBeInTheDocument()
    })

    it('handles save button click without triggering the card onClick', async () => {
      const user = userEvent.setup()
      const onToggleBookmark = vi.fn()
      render(
        <EventCard
          event={mockEvent}
          onRegister={mockOnRegister}
          onClick={mockOnClick}
          isRegistered
          onToggleBookmark={onToggleBookmark}
        />
      )

      const saveButton = screen.getByRole('button', { name: /save book club meeting for later/i })
      await user.click(saveButton)

      expect(onToggleBookmark).toHaveBeenCalledWith(mockEvent.id)
      expect(mockOnClick).not.toHaveBeenCalled()
    })

    it('flips the bookmark button label and pressed state once bookmarked', () => {
      render(
        <EventCard
          event={mockEvent}
          onRegister={mockOnRegister}
          onClick={mockOnClick}
          isRegistered
          isBookmarked
          onToggleBookmark={vi.fn()}
        />
      )
      const removeButton = screen.getByRole('button', { name: /remove book club meeting from saved events/i })
      expect(removeButton).toHaveAttribute('aria-pressed', 'true')
    })

    it('opens event details when the card is clicked', async () => {
      const user = userEvent.setup()
      const onClick = vi.fn()
      render(<EventCard event={mockEvent} onRegister={mockOnRegister} onClick={onClick} />)

      const card = screen.getByRole('button', { name: /view details for book club meeting/i })
      await user.click(card)

      expect(onClick).toHaveBeenCalled()
    })
  })

  // ========== ERROR HANDLING TESTS ==========

  describe('Error Handling', () => {
    it('handles a missing description gracefully', () => {
      const noDescEvent = createMockEvent({ description: null })
      render(<EventCard event={noDescEvent} onRegister={mockOnRegister} onClick={mockOnClick} />)

      expect(screen.getByRole('button', { name: /view details for/i })).toBeInTheDocument()
    })

    it('handles a missing location gracefully', () => {
      const noLocationEvent = createMockEvent({ location: null })
      render(<EventCard event={noLocationEvent} onRegister={mockOnRegister} onClick={mockOnClick} />)

      expect(screen.getByRole('button', { name: /view details for/i })).toBeInTheDocument()
    })

    it('handles zero registrations without showing a registered count', () => {
      const noRegistrationsEvent = createMockEvent({ registration_count: 0 })
      render(<EventCard event={noRegistrationsEvent} onRegister={mockOnRegister} onClick={mockOnClick} />)

      expect(screen.queryByText(/registered$/)).not.toBeInTheDocument()
    })
  })

  // ========== ACCESSIBILITY TESTS ==========

  describe('Accessibility (WCAG AA)', () => {
    it('exposes the whole card as a keyboard-operable button with a descriptive name', () => {
      render(<EventCard event={mockEvent} onRegister={mockOnRegister} onClick={mockOnClick} />)
      const card = screen.getByRole('button', { name: 'View details for Book Club Meeting' })
      expect(card).toHaveAttribute('tabIndex', '0')
    })

    it('register and save buttons have descriptive accessible names', () => {
      render(
        <EventCard
          event={mockEvent}
          onRegister={mockOnRegister}
          onClick={mockOnClick}
          isRegistered
          onToggleBookmark={vi.fn()}
        />
      )

      expect(screen.getByRole('button', { name: /save book club meeting for later/i })).toBeInTheDocument()
    })

    it('bookmark icon is decorative (aria-hidden) since the button already has an accessible name', () => {
      const { container } = render(
        <EventCard
          event={mockEvent}
          onRegister={mockOnRegister}
          onClick={mockOnClick}
          isRegistered
          onToggleBookmark={vi.fn()}
        />
      )
      const icon = container.querySelector('svg')
      expect(icon).toHaveAttribute('aria-hidden', 'true')
    })

    it('is keyboard navigable: Enter and Space on the card both invoke onClick', async () => {
      const user = userEvent.setup()
      const onClick = vi.fn()
      render(<EventCard event={mockEvent} onRegister={mockOnRegister} onClick={onClick} />)

      const card = screen.getByRole('button', { name: /view details for/i })
      card.focus()
      expect(card).toHaveFocus()

      await user.keyboard('{Enter}')
      expect(onClick).toHaveBeenCalledTimes(1)

      await user.keyboard(' ')
      expect(onClick).toHaveBeenCalledTimes(2)
    })
  })

  // ========== INTEGRATION TESTS ==========

  describe('Integration', () => {
    it('displays complete event information', () => {
      render(<EventCard event={mockEvent} onRegister={mockOnRegister} onClick={mockOnClick} />)

      expect(screen.getByText('Book Club Meeting')).toBeInTheDocument()
      expect(screen.getByText('Monthly book club discussion')).toBeInTheDocument()
      expect(screen.getByText('Main Library')).toBeInTheDocument()
      expect(screen.getByText('book-club')).toBeInTheDocument()
      expect(screen.getByText('15 of 30 spots available')).toBeInTheDocument()
    })

    it('reflects capacity updates on rerender', () => {
      const { rerender } = render(<EventCard event={mockEvent} onRegister={mockOnRegister} onClick={mockOnClick} />)

      expect(screen.getByText('15 of 30 spots available')).toBeInTheDocument()

      const updatedEvent = createMockEvent({ registration_count: 20, max_attendees: 30, spots_remaining: 10 })
      rerender(<EventCard event={updatedEvent} onRegister={mockOnRegister} onClick={mockOnClick} />)

      expect(screen.getByText('10 of 30 spots available')).toBeInTheDocument()
    })

    it('reflects full-event status changes on rerender', () => {
      const { rerender } = render(<EventCard event={mockEvent} onRegister={mockOnRegister} onClick={mockOnClick} />)

      expect(screen.getByRole('button', { name: /^register$/i })).toBeInTheDocument()

      const fullEvent = createMockEvent({ registration_count: 30, max_attendees: 30, spots_remaining: 0 })
      rerender(<EventCard event={fullEvent} onRegister={mockOnRegister} onClick={mockOnClick} />)

      expect(screen.getByRole('button', { name: /^waitlist$/i })).toBeInTheDocument()
    })
  })
})

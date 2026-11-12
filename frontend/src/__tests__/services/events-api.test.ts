/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Events API Service Tests
 *
 * Tests for events API functions including:
 * - Fetching events and tags
 * - Event CRUD operations
 * - Event registration
 * - Event reviews
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import * as apiClient from '@/lib/api-client'
import {
  getEventTags,
  getEvents,
  getRelatedEvents,
  registerForEvent,
  cancelRegistration,
  createEvent,
  updateEvent,
  deleteEvent,
  submitEventReview,
  getEventReviews,
  getEventReviewSummary,
} from '@/api/events-api'

// Mock the api-client module
vi.mock('@/lib/api-client', () => ({
  fetchApi: vi.fn(),
  isApiError: vi.fn(),
}))

describe('Events API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  // ==================== Get Event Tags Tests ====================

  describe('getEventTags', () => {
    it('should return list of tags', async () => {
      const mockTags = ['Programming', 'Storytime', 'Book Club', 'Workshop']
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockTags)

      const result = await getEventTags()

      expect(result).toEqual(mockTags)
      expect(apiClient.fetchApi).toHaveBeenCalledWith('/events/tags')
    })

    it('should return empty array on error', async () => {
      vi.mocked(apiClient.fetchApi).mockRejectedValue(new Error('Server error'))

      const result = await getEventTags()

      expect(result).toEqual([])
    })
  })

  // ==================== Get Events Tests ====================

  describe('getEvents', () => {
    it('should return events with default filters', async () => {
      const mockResponse = {
        items: [
          {
            id: 1,
            title: 'Story Time',
            description: 'Weekly story time for kids',
            start_time: '2024-01-15T10:00:00Z',
            end_time: '2024-01-15T11:00:00Z',
            location: 'Children\'s Room',
            is_virtual: false,
            audience: 'Children',
            category: 'Programs',
            registration_required: true,
            registration_count: 15,
            spots_remaining: 5,
          },
        ],
        total: 1,
        page: 1,
        per_page: 20,
      }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockResponse)

      const result = await getEvents()

      expect(result).toEqual({
        data: mockResponse.items,
        pagination: {
          page: 1,
          per_page: 20,
          total: 1,
          total_pages: 1,
          has_next: false,
          has_previous: false,
        },
      })
      expect(apiClient.fetchApi).toHaveBeenCalledWith(expect.stringContaining('upcoming=true'))
    })

    it('should support category filter', async () => {
      vi.mocked(apiClient.fetchApi).mockResolvedValue({ items: [], total: 0, page: 1, per_page: 20 })

      await getEvents({ category: 'Programs' })

      expect(apiClient.fetchApi).toHaveBeenCalledWith(expect.stringContaining('category=Programs'))
    })

    it('should support multi-select audiences filter (OR semantics)', async () => {
      vi.mocked(apiClient.fetchApi).mockResolvedValue({ items: [], total: 0, page: 1, per_page: 20 })

      await getEvents({ audiences: ['Adults', 'Teens'] })

      const call = vi.mocked(apiClient.fetchApi).mock.calls[0]![0] as string
      expect(call).toContain('audiences=Adults')
      expect(call).toContain('audiences=Teens')
    })

    it('should omit audiences param when array is empty', async () => {
      vi.mocked(apiClient.fetchApi).mockResolvedValue({ items: [], total: 0, page: 1, per_page: 20 })

      await getEvents({ audiences: [] })

      const call = vi.mocked(apiClient.fetchApi).mock.calls[0]![0] as string
      expect(call).not.toContain('audiences=')
    })

    it('should support tag filter', async () => {
      vi.mocked(apiClient.fetchApi).mockResolvedValue({ items: [], total: 0, page: 1, per_page: 20 })

      await getEvents({ tag: 'Workshop' })

      expect(apiClient.fetchApi).toHaveBeenCalledWith(expect.stringContaining('tag=Workshop'))
    })

    it('should support featured_only filter', async () => {
      vi.mocked(apiClient.fetchApi).mockResolvedValue({ items: [], total: 0, page: 1, per_page: 20 })

      await getEvents({ featured_only: true })

      expect(apiClient.fetchApi).toHaveBeenCalledWith(expect.stringContaining('featured_only=true'))
    })

    it('should support series_id filter', async () => {
      vi.mocked(apiClient.fetchApi).mockResolvedValue({ items: [], total: 0, page: 1, per_page: 20 })

      await getEvents({ series_id: 'summer-reading-2024' })

      expect(apiClient.fetchApi).toHaveBeenCalledWith(expect.stringContaining('series_id=summer-reading-2024'))
    })

    it('should support pagination', async () => {
      vi.mocked(apiClient.fetchApi).mockResolvedValue({ items: [], total: 0, page: 2, per_page: 10 })

      await getEvents({ page: 2, per_page: 10 })

      expect(apiClient.fetchApi).toHaveBeenCalledWith(expect.stringContaining('page=2'))
      // Backend reads `page_size`, not `per_page`; sending per_page silently capped results at the default 20.
      expect(apiClient.fetchApi).toHaveBeenCalledWith(expect.stringContaining('page_size=10'))
    })

    it('should clamp per_page to the API max page size of 100', async () => {
      vi.mocked(apiClient.fetchApi).mockResolvedValue({ items: [], total: 0, page: 1, per_page: 100 })

      await getEvents({ per_page: 500 })

      expect(apiClient.fetchApi).toHaveBeenCalledWith(expect.stringContaining('page_size=100'))
      expect(apiClient.fetchApi).not.toHaveBeenCalledWith(expect.stringContaining('page_size=500'))
    })

    it('should allow overriding upcoming filter', async () => {
      vi.mocked(apiClient.fetchApi).mockResolvedValue({ items: [], total: 0, page: 1, per_page: 20 })

      await getEvents({ upcoming: false })

      expect(apiClient.fetchApi).toHaveBeenCalledWith(expect.stringContaining('upcoming=false'))
    })

    it('should throw error when fetch fails', async () => {
      vi.mocked(apiClient.fetchApi).mockRejectedValue(new Error('Server error'))

      await expect(getEvents()).rejects.toThrow('Failed to fetch events')
    })
  })

  // ==================== Get Related Events Tests ====================

  describe('getRelatedEvents', () => {
    it('should return related events', async () => {
      const mockResponse = {
        items: [
          { id: 2, title: 'Related Event 1' },
          { id: 3, title: 'Related Event 2' },
        ],
        source_event_id: 1,
      }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockResponse)

      const result = await getRelatedEvents(1)

      expect(result).toEqual(mockResponse)
      expect(apiClient.fetchApi).toHaveBeenCalledWith('/events/1/related?limit=3')
    })

    it('should support custom limit', async () => {
      vi.mocked(apiClient.fetchApi).mockResolvedValue({ items: [], source_event_id: 1 })

      await getRelatedEvents(1, 5)

      expect(apiClient.fetchApi).toHaveBeenCalledWith('/events/1/related?limit=5')
    })

    it('should return empty array on error', async () => {
      vi.mocked(apiClient.fetchApi).mockRejectedValue(new Error('Server error'))

      const result = await getRelatedEvents(999)

      expect(result).toEqual({ items: [], source_event_id: 999 })
    })
  })

  // ==================== Event Registration Tests ====================

  describe('registerForEvent', () => {
    it('should successfully register for event', async () => {
      const mockRegistration = {
        id: 1,
        event_id: 1,
        patron_name: 'John Doe',
        patron_email: 'john@example.com',
        patron_phone: '555-1234',
        registered_at: '2024-01-10T14:00:00Z',
        status: 'confirmed',
        reminder_requested: true,
        waitlist_position: null,
      }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockRegistration)

      const registrationData = {
        patron_name: 'John Doe',
        patron_email: 'john@example.com',
        patron_phone: '555-1234',
        reminder_requested: true,
      }
      const result = await registerForEvent(1, registrationData)

      expect(result).toEqual(mockRegistration)
      expect(apiClient.fetchApi).toHaveBeenCalledWith('/events/1/register', {
        method: 'POST',
        body: registrationData,
      })
    })

    it('should handle waitlist registration', async () => {
      const mockRegistration = {
        id: 2,
        event_id: 1,
        patron_name: 'Jane Smith',
        patron_email: 'jane@example.com',
        registered_at: '2024-01-10T15:00:00Z',
        status: 'waitlisted',
        reminder_requested: false,
        waitlist_position: 3,
      }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockRegistration)

      const result = await registerForEvent(1, {
        patron_name: 'Jane Smith',
        patron_email: 'jane@example.com',
      })

      expect(result.status).toBe('waitlisted')
      expect(result.waitlist_position).toBe(3)
    })

    it('should throw error when event is full', async () => {
      const apiError = { status: 400, detail: 'Event is at full capacity' }
      vi.mocked(apiClient.fetchApi).mockRejectedValue(apiError)
      vi.mocked(apiClient.isApiError).mockReturnValue(true)

      await expect(
        registerForEvent(1, { patron_name: 'John', patron_email: 'john@test.com' })
      ).rejects.toThrow('Event is at full capacity')
    })

    it('should throw error for duplicate registration', async () => {
      const apiError = { status: 409, detail: 'Already registered for this event' }
      vi.mocked(apiClient.fetchApi).mockRejectedValue(apiError)
      vi.mocked(apiClient.isApiError).mockReturnValue(true)

      await expect(
        registerForEvent(1, { patron_name: 'John', patron_email: 'john@test.com' })
      ).rejects.toThrow('Already registered for this event')
    })

    it('should throw "Registration failed" when no detail', async () => {
      const apiError = { status: 500 }
      vi.mocked(apiClient.fetchApi).mockRejectedValue(apiError)
      vi.mocked(apiClient.isApiError).mockReturnValue(true)

      await expect(
        registerForEvent(1, { patron_name: 'John', patron_email: 'john@test.com' })
      ).rejects.toThrow('Registration failed')
    })

    it('should re-throw non-API errors', async () => {
      vi.mocked(apiClient.fetchApi).mockRejectedValue(new Error('Network error'))
      vi.mocked(apiClient.isApiError).mockReturnValue(false)

      await expect(
        registerForEvent(1, { patron_name: 'John', patron_email: 'john@test.com' })
      ).rejects.toThrow('Network error')
    })
  })

  describe('cancelRegistration', () => {
    it('should successfully cancel registration', async () => {
      vi.mocked(apiClient.fetchApi).mockResolvedValue(undefined)

      await expect(cancelRegistration(1, 123, 'john@example.com')).resolves.toBeUndefined()

      // patron_email travels in the request body, not the URL query string,
      // so it doesn't end up in server access logs / browser history.
      expect(apiClient.fetchApi).toHaveBeenCalledWith(
        '/events/1/register/123',
        {
          method: 'DELETE',
          body: JSON.stringify({ patron_email: 'john@example.com' }),
          headers: { 'Content-Type': 'application/json' },
          skipJsonParse: true,
        }
      )
    })

    it('should send email in the request body, not the URL', async () => {
      vi.mocked(apiClient.fetchApi).mockResolvedValue(undefined)

      await cancelRegistration(1, 123, 'test+user@example.com')

      expect(apiClient.fetchApi).toHaveBeenCalledWith(
        expect.not.stringContaining('test+user@example.com'),
        expect.objectContaining({
          body: JSON.stringify({ patron_email: 'test+user@example.com' }),
        })
      )
    })

    it('should throw error when cancellation fails', async () => {
      vi.mocked(apiClient.fetchApi).mockRejectedValue(new Error('Not found'))

      await expect(cancelRegistration(1, 999, 'john@example.com')).rejects.toThrow(
        'Failed to cancel registration'
      )
    })
  })

  // ==================== Event CRUD Tests ====================

  describe('createEvent', () => {
    it('should successfully create event', async () => {
      const mockEvent = {
        id: 1,
        title: 'New Workshop',
        description: 'Learn something new',
        start_time: '2024-02-01T14:00:00Z',
        end_time: '2024-02-01T16:00:00Z',
        location: 'Meeting Room A',
        registration_required: true,
        max_attendees: 20,
      }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockEvent)

      const eventData = {
        title: 'New Workshop',
        description: 'Learn something new',
        start_time: '2024-02-01T14:00:00Z',
        end_time: '2024-02-01T16:00:00Z',
        location: 'Meeting Room A',
        registration_required: true,
        max_attendees: 20,
      }
      const result = await createEvent('auth-token', eventData)

      expect(result).toEqual(mockEvent)
      expect(apiClient.fetchApi).toHaveBeenCalledWith('/events', {
        method: 'POST',
        token: 'auth-token',
        body: eventData,
      })
    })

    it('should convert max_attendees to number', async () => {
      vi.mocked(apiClient.fetchApi).mockResolvedValue({ id: 1 })

      await createEvent('token', {
        title: 'Event',
        start_time: '2024-02-01T14:00:00Z',
        registration_required: false,
        max_attendees: '25' as unknown as number,
      })

      expect(apiClient.fetchApi).toHaveBeenCalledWith('/events', {
        method: 'POST',
        token: 'token',
        body: expect.objectContaining({ max_attendees: 25 }),
      })
    })

    it('should handle null max_attendees', async () => {
      vi.mocked(apiClient.fetchApi).mockResolvedValue({ id: 1 })

      await createEvent('token', {
        title: 'Event',
        start_time: '2024-02-01T14:00:00Z',
        registration_required: false,
        max_attendees: null,
      })

      expect(apiClient.fetchApi).toHaveBeenCalledWith('/events', {
        method: 'POST',
        token: 'token',
        body: expect.objectContaining({ max_attendees: null }),
      })
    })

    it('should throw error on validation failure', async () => {
      const apiError = { status: 422, detail: 'Start time must be in the future' }
      vi.mocked(apiClient.fetchApi).mockRejectedValue(apiError)
      vi.mocked(apiClient.isApiError).mockReturnValue(true)

      await expect(
        createEvent('token', {
          title: 'Event',
          start_time: '2020-01-01T14:00:00Z',
          registration_required: false,
        })
      ).rejects.toThrow('Start time must be in the future')
    })

    it('should throw "Failed to create event" when no detail', async () => {
      const apiError = { status: 500 }
      vi.mocked(apiClient.fetchApi).mockRejectedValue(apiError)
      vi.mocked(apiClient.isApiError).mockReturnValue(true)

      await expect(
        createEvent('token', {
          title: 'Event',
          start_time: '2024-02-01T14:00:00Z',
          registration_required: false,
        })
      ).rejects.toThrow('Failed to create event')
    })
  })

  describe('updateEvent', () => {
    it('should successfully update event', async () => {
      const mockEvent = {
        id: 1,
        title: 'Updated Workshop',
        description: 'Updated description',
        start_time: '2024-02-01T14:00:00Z',
        registration_required: true,
      }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockEvent)

      const result = await updateEvent('auth-token', 1, {
        title: 'Updated Workshop',
        description: 'Updated description',
        start_time: '2024-02-01T14:00:00Z',
        registration_required: true,
      })

      expect(result).toEqual(mockEvent)
      expect(apiClient.fetchApi).toHaveBeenCalledWith('/events/1', {
        method: 'PUT',
        token: 'auth-token',
        body: expect.objectContaining({ title: 'Updated Workshop' }),
      })
    })

    it('should throw error on failure', async () => {
      const apiError = { status: 404, detail: 'Event not found' }
      vi.mocked(apiClient.fetchApi).mockRejectedValue(apiError)
      vi.mocked(apiClient.isApiError).mockReturnValue(true)

      await expect(
        updateEvent('token', 999, {
          title: 'Event',
          start_time: '2024-02-01T14:00:00Z',
          registration_required: false,
        })
      ).rejects.toThrow('Event not found')
    })
  })

  describe('deleteEvent', () => {
    it('should successfully delete event', async () => {
      vi.mocked(apiClient.fetchApi).mockResolvedValue(undefined)

      await expect(deleteEvent('auth-token', 1)).resolves.toBeUndefined()

      expect(apiClient.fetchApi).toHaveBeenCalledWith('/events/1', {
        method: 'DELETE',
        token: 'auth-token',
        skipJsonParse: true,
      })
    })

    it('should throw error when event has registrations', async () => {
      const apiError = { status: 400, detail: 'Cannot delete event with active registrations' }
      vi.mocked(apiClient.fetchApi).mockRejectedValue(apiError)
      vi.mocked(apiClient.isApiError).mockReturnValue(true)

      await expect(deleteEvent('token', 1)).rejects.toThrow(
        'Cannot delete event with active registrations'
      )
    })

    it('should throw "Failed to delete event" when no detail', async () => {
      const apiError = { status: 500 }
      vi.mocked(apiClient.fetchApi).mockRejectedValue(apiError)
      vi.mocked(apiClient.isApiError).mockReturnValue(true)

      await expect(deleteEvent('token', 1)).rejects.toThrow('Failed to delete event')
    })
  })

  // ==================== Event Reviews Tests ====================

  describe('submitEventReview', () => {
    it('should successfully submit review', async () => {
      const mockReview = {
        id: 1,
        event_id: 1,
        patron_email: 'john@example.com',
        rating: 5,
        comment: 'Great event!',
        created_at: '2024-01-15T18:00:00Z',
      }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockReview)

      const reviewData = {
        patron_email: 'john@example.com',
        rating: 5,
        comment: 'Great event!',
      }
      const result = await submitEventReview(1, reviewData)

      expect(result).toEqual(mockReview)
      expect(apiClient.fetchApi).toHaveBeenCalledWith('/events/1/reviews', {
        method: 'POST',
        body: reviewData,
      })
    })

    it('should throw error for invalid rating', async () => {
      const apiError = { status: 422, detail: 'Rating must be between 1 and 5' }
      vi.mocked(apiClient.fetchApi).mockRejectedValue(apiError)
      vi.mocked(apiClient.isApiError).mockReturnValue(true)

      await expect(
        submitEventReview(1, { patron_email: 'john@test.com', rating: 10 })
      ).rejects.toThrow('Rating must be between 1 and 5')
    })

    it('should throw error for non-attendee', async () => {
      const apiError = { status: 403, detail: 'Only event attendees can leave reviews' }
      vi.mocked(apiClient.fetchApi).mockRejectedValue(apiError)
      vi.mocked(apiClient.isApiError).mockReturnValue(true)

      await expect(
        submitEventReview(1, { patron_email: 'nonattendee@test.com', rating: 4 })
      ).rejects.toThrow('Only event attendees can leave reviews')
    })

    it('should throw "Failed to submit review" when no detail', async () => {
      const apiError = { status: 500 }
      vi.mocked(apiClient.fetchApi).mockRejectedValue(apiError)
      vi.mocked(apiClient.isApiError).mockReturnValue(true)

      await expect(
        submitEventReview(1, { patron_email: 'john@test.com', rating: 5 })
      ).rejects.toThrow('Failed to submit review')
    })
  })

  describe('getEventReviews', () => {
    it('should return reviews with pagination', async () => {
      const mockReviews = [
        { id: 1, event_id: 1, patron_email: 'user1@test.com', rating: 5, comment: 'Great!' },
        { id: 2, event_id: 1, patron_email: 'user2@test.com', rating: 4, comment: 'Good' },
      ]
      vi.mocked(apiClient.fetchApi).mockResolvedValue({
        data: mockReviews,
        pagination: { page: 1, per_page: 20, total: 2, total_pages: 1, has_next: false, has_previous: false },
      })

      const result = await getEventReviews(1)

      expect(result).toEqual(mockReviews)
      expect(apiClient.fetchApi).toHaveBeenCalledWith('/events/1/reviews?page=1&page_size=20')
    })

    it('should support custom pagination', async () => {
      vi.mocked(apiClient.fetchApi).mockResolvedValue({
        data: [],
        pagination: { page: 2, per_page: 10, total: 0, total_pages: 0, has_next: false, has_previous: false },
      })

      await getEventReviews(1, 2, 10)

      expect(apiClient.fetchApi).toHaveBeenCalledWith('/events/1/reviews?page=2&page_size=10')
    })

    it('should throw error when fetch fails', async () => {
      vi.mocked(apiClient.fetchApi).mockRejectedValue(new Error('Server error'))

      await expect(getEventReviews(1)).rejects.toThrow('Failed to fetch reviews')
    })
  })

  describe('getEventReviewSummary', () => {
    it('should return review summary', async () => {
      const mockSummary = {
        event_id: 1,
        average_rating: 4.5,
        total_reviews: 25,
        rating_distribution: { 1: 1, 2: 2, 3: 3, 4: 8, 5: 11 },
      }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockSummary)

      const result = await getEventReviewSummary(1)

      expect(result).toEqual(mockSummary)
      expect(apiClient.fetchApi).toHaveBeenCalledWith('/events/1/reviews/summary')
    })

    it('should handle event with no reviews', async () => {
      const mockSummary = {
        event_id: 1,
        average_rating: null,
        total_reviews: 0,
        rating_distribution: {},
      }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockSummary)

      const result = await getEventReviewSummary(1)

      expect(result.average_rating).toBeNull()
      expect(result.total_reviews).toBe(0)
    })

    it('should throw error when fetch fails', async () => {
      vi.mocked(apiClient.fetchApi).mockRejectedValue(new Error('Server error'))

      await expect(getEventReviewSummary(1)).rejects.toThrow('Failed to fetch review summary')
    })
  })
})

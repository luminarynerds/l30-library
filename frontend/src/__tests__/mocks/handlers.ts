/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { http, HttpResponse, PathParams } from 'msw'
import { API_BASE } from '@/api/types'

/**
 * MSW Request Handlers for API Mocking
 * Intercepts API calls during tests and provides mock responses
 */

// Mock data for staff statistics
const mockStatistics = {
  total_checkouts_today: 142,
  total_checkouts_this_month: 3847,
  new_registrations_today: 8,
  new_registrations_this_month: 234,
  items_in_transit: 23,
  items_checked_out: 5643,
  holds_queue_size: 187,
  overdue_items: 42,
  patrons_with_fines: 156,
  total_fine_amount: 2847.50,
  items_expiring_holds: 12,
  duplicate_patrons_detected: 3,
}

// Mock data for at-risk patrons
const mockAtRiskPatrons = {
  patrons: [
    {
      id: 1,
      name: 'John Smith',
      email: 'john@example.com',
      fine_amount: 45.50,
      overdue_items: 3,
      days_overdue: 15,
      risk_level: 'high',
      reason: 'Multiple overdue items and unpaid fines',
    },
    {
      id: 2,
      name: 'Jane Doe',
      email: 'jane@example.com',
      fine_amount: 12.00,
      overdue_items: 1,
      days_overdue: 8,
      risk_level: 'medium',
      reason: 'Single overdue item',
    },
    {
      id: 3,
      name: 'Bob Johnson',
      email: 'bob@example.com',
      fine_amount: 5.00,
      overdue_items: 1,
      days_overdue: 2,
      risk_level: 'low',
      reason: 'Recently overdue but responding',
    },
  ],
}

// Mock events
const mockEvents = {
  events: [
    {
      id: 1,
      title: 'Book Club Meeting',
      description: 'Monthly book club discussion',
      date: '2026-02-15T18:00:00Z',
      location: 'Main Library',
      image: '/images/book-club.jpg',
    },
    {
      id: 2,
      title: 'Children\'s Story Time',
      description: 'Stories for children ages 3-7',
      date: '2026-02-10T14:00:00Z',
      location: 'Children\'s Room',
      image: '/images/story-time.jpg',
    },
  ],
}

// Mock reviews
const mockReviews = {
  reviews: [
    {
      id: 1,
      book_title: 'The Great Gatsby',
      author: 'F. Scott Fitzgerald',
      rating: 4.5,
      content: 'A masterpiece of American literature',
      patron_name: 'John Smith',
      created_at: '2026-01-15T10:00:00Z',
      status: 'pending_response',
    },
  ],
}

// Mock flagged content
const mockFlaggedContent = {
  items: [
    {
      id: 1,
      type: 'review',
      content: 'Inappropriate content here',
      reason: 'Contains offensive language',
      flagged_at: '2026-02-01T12:00:00Z',
      severity: 'medium',
    },
  ],
}

/**
 * Define all API handlers
 */
export const handlers = [
  // Staff Statistics
  http.get(`${API_BASE}/staff/statistics/dashboard`, () => {
    return HttpResponse.json(mockStatistics)
  }),

  // At-risk Patrons
  http.get(`${API_BASE}/reports/at-risk-patrons`, () => {
    return HttpResponse.json(mockAtRiskPatrons)
  }),

  // Bulk Operations
  http.post(`${API_BASE}/patrons/bulk/send-notice`, async ({ request }) => {
    const body = await request.json() as { patron_ids?: number[] }
    return HttpResponse.json({
      success: true,
      processed: body.patron_ids?.length || 0,
      failed: 0,
      errors: [],
    })
  }),

  http.post(`${API_BASE}/fines/bulk/waive`, async ({ request }) => {
    const body = await request.json() as { patron_ids?: number[] }
    const patronCount = body.patron_ids?.length || 0
    return HttpResponse.json({
      success: true,
      processed: patronCount,
      failed: 0,
      total_waived: 123.45,
      errors: [],
    })
  }),

  // Events
  http.get(`${API_BASE}/events`, () => {
    return HttpResponse.json(mockEvents)
  }),

  http.get(`${API_BASE}/events/:id`, ({ params }: { params: PathParams }) => {
    const event = mockEvents.events.find(e => e.id === parseInt(String(params.id)))
    if (!event) {
      return HttpResponse.json({ error: 'Event not found' }, { status: 404 })
    }
    return HttpResponse.json(event)
  }),

  http.post(`${API_BASE}/events/:id/register`, async ({ params }: { params: PathParams }) => {
    return HttpResponse.json({
      success: true,
      event_id: parseInt(String(params.id)),
      registered: true,
    })
  }),

  // Reviews
  http.get(`${API_BASE}/reviews`, () => {
    return HttpResponse.json(mockReviews)
  }),

  http.post(`${API_BASE}/reviews/:id/respond`, async ({ request }) => {
    const body = await request.json() as { response: string }
    return HttpResponse.json({
      success: true,
      review_id: parseInt(String(request.url.split('/')[4])),
      response: body.response,
      status: 'responded',
    })
  }),

  // Content Moderation
  http.get(`${API_BASE}/moderation/flagged-content`, () => {
    return HttpResponse.json(mockFlaggedContent)
  }),

  http.post(`${API_BASE}/moderation/flagged-content/:id/action`, async ({ request }) => {
    const body = await request.json() as { action: string }
    return HttpResponse.json({
      success: true,
      action: body.action,
      content_id: parseInt(String(request.url.split('/')[4])),
    })
  }),

  // Monthly Summary
  http.get(`${API_BASE}/reports/monthly-summary`, () => {
    return HttpResponse.json({
      total_checkouts: 3847,
      new_registrations: 234,
      items_in_transit: 23,
    })
  }),

  // Daily Statistics
  http.get(`${API_BASE}/statistics/daily`, () => {
    return HttpResponse.json({
      date: new Date().toISOString(),
      checkouts: 142,
      registrations: 8,
      holds_created: 15,
    })
  }),
]
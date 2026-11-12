/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { render, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'

vi.mock('@/i18n', () => ({
  getCurrentLocale: () => 'en-US',
  useTranslation: () => ({ t: (key: string) => key }),
}))

vi.mock('@/lib/sentry-lazy', () => ({
  captureException: vi.fn(),
}))

// The meeting JSON-LD organizer now reads library name/domain from branding;
// mock the hook so the page renders without a BrandingProvider.
vi.mock('@/contexts/BrandingContext', () => ({
  useBranding: () => ({
    library_name: 'Test Library',
    phone: '555-123-4567',
    contact_email: 'hello@testlibrary.example',
    domain: 'testlibrary.example',
  }),
}))

const mockGet = vi.fn()
const mockPost = vi.fn()
vi.mock('../../api/api', () => ({
  default: {
    get: (...args: unknown[]) => mockGet(...args),
    post: (...args: unknown[]) => mockPost(...args),
  },
}))

vi.mock('../../components/board/MeetingRecordingPlayer', () => ({
  default: () => null,
}))

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return { ...actual, useParams: () => ({ meetingId: '42' }) }
})

import MeetingDetailPage from './MeetingDetailPage'

const baseMeeting = {
  id: 42,
  meeting_type: 'regular',
  title: 'Regular Board Meeting',
  description: 'Monthly board meeting',
  scheduled_date: '2026-06-15T18:00:00Z',
  start_time: '2026-06-15T18:00:00Z',
  end_time: '2026-06-15T20:00:00Z',
  location: '123 Main St',
  is_virtual: false,
  is_cancelled: false,
}

const renderPage = () =>
  render(
    <MemoryRouter initialEntries={['/board/meetings/42']}>
      <MeetingDetailPage />
    </MemoryRouter>,
  )

describe('MeetingDetailPage JSON-LD', () => {
  beforeEach(() => {
    mockGet.mockReset()
    mockPost.mockReset()
    // Default: auth check fails (unauthenticated path keeps tests lean).
    mockGet.mockImplementation((url: string) => {
      if (url.endsWith('/auth/me')) return Promise.reject(new Error('unauth'))
      if (url.endsWith('/board/meetings/42')) return Promise.resolve(baseMeeting)
      return Promise.reject(new Error('unexpected ' + url))
    })
  })

  afterEach(() => {
    document.head
      .querySelectorAll('script[type="application/ld+json"]')
      .forEach((n) => n.remove())
  })

  it('injects Schema.org Event JSON-LD after meeting loads', async () => {
    renderPage()

    await waitFor(() => {
      const node = document.head.querySelector('script[type="application/ld+json"]')
      expect(node).not.toBeNull()
    })

    const node = document.head.querySelector('script[type="application/ld+json"]')!
    const data = JSON.parse(node.textContent || '{}')
    expect(data['@context']).toBe('https://schema.org')
    expect(data['@type']).toBe('Event')
    expect(data.name).toBe('Regular Board Meeting')
    expect(data.startDate).toBe('2026-06-15T18:00:00Z')
    expect(data.endDate).toBe('2026-06-15T20:00:00Z')
    expect(data.eventStatus).toBe('https://schema.org/EventScheduled')
    expect(data.eventAttendanceMode).toBe('https://schema.org/OfflineEventAttendanceMode')
    expect(data.location).toEqual({
      '@type': 'Place',
      name: '123 Main St',
      address: '123 Main St',
    })
    expect(data.organizer['@type']).toBe('GovernmentOrganization')
  })

  it('emits VirtualLocation + EventCancelled status for cancelled virtual meeting and omits null fields', async () => {
    mockGet.mockImplementation((url: string) => {
      if (url.endsWith('/auth/me')) return Promise.reject(new Error('unauth'))
      if (url.endsWith('/board/meetings/42'))
        return Promise.resolve({
          ...baseMeeting,
          is_virtual: true,
          is_cancelled: true,
          virtual_meeting_url: 'https://meet.example/abc',
          location: undefined,
          description: undefined,
          end_time: undefined,
        })
      return Promise.reject(new Error('unexpected ' + url))
    })

    renderPage()

    await waitFor(() => {
      expect(document.head.querySelector('script[type="application/ld+json"]')).not.toBeNull()
    })

    const node = document.head.querySelector('script[type="application/ld+json"]')!
    const data = JSON.parse(node.textContent || '{}')
    expect(data.eventStatus).toBe('https://schema.org/EventCancelled')
    expect(data.eventAttendanceMode).toBe('https://schema.org/OnlineEventAttendanceMode')
    expect(data.location).toEqual({
      '@type': 'VirtualLocation',
      url: 'https://meet.example/abc',
    })
    expect('description' in data).toBe(false)
    expect(data.endDate).toBe('2026-06-15T18:00:00Z')
  })
})

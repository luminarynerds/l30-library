/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { Branding } from '../../contexts/BrandingContext'

const mockPut = vi.fn()
const mockRefetch = vi.fn()
const mockToastSuccess = vi.fn()
const mockToastError = vi.fn()

vi.mock('react-hot-toast', () => ({
  default: {
    success: (...args: unknown[]) => mockToastSuccess(...args),
    error: (...args: unknown[]) => mockToastError(...args),
  },
}))

vi.mock('@/lib/api-client', () => ({
  default: { put: (...args: unknown[]) => mockPut(...args) },
}))

vi.mock('../../components/shells/AdminShell', () => ({
  AdminShell: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}))

const sampleBranding: Branding = {
  library_name: 'Test Library',
  library_short_name: 'TL',
  domain: 'test.example',
  contact_email: 'old@test.example',
  privacy_email: '',
  indie_email: '',
  giving_email: '',
  events_email: '',
  print_email: '',
  makerspace_email: '',
  phone: '555-0100',
  address_line1: '1 Main St',
  address_line2: '',
  city: 'Testville',
  state: 'OH',
  zip_code: '00000',
  primary_color: '#8B5E5E',
  accent_color: '#D49898',
  logo_url: '',
  hero_image_url: '',
  display_font: '',
  body_font: '',
  secondary_color: '',
  surface_color: '',
  ink_color: '',
  nav_style: '',
  card_prefix: 'TL',
  product_name: '',
  product_tagline: '',
  hero_title: '',
  hero_subtitle: '',
  tagline: '',
  is_demo: false,
  bluesky_url: '',
  mastodon_url: '',
  seasonal_callout_active: false,
}

vi.mock('../../contexts/BrandingContext', () => ({
  useBrandingContext: () => ({
    branding: sampleBranding,
    loading: false,
    setupComplete: true,
    hasAdmin: true,
    refetch: mockRefetch,
  }),
}))

import AdminBrandingPage from '../AdminBrandingPage'

describe('AdminBrandingPage', () => {
  beforeEach(() => {
    mockPut.mockReset()
    mockRefetch.mockReset()
    mockToastSuccess.mockReset()
    mockToastError.mockReset()
    mockPut.mockResolvedValue({ status: 'ok' })
    mockRefetch.mockResolvedValue(undefined)
  })

  it('populates fields from BrandingContext', () => {
    render(<AdminBrandingPage />)
    expect(screen.getByDisplayValue('Test Library')).toBeInTheDocument()
    expect(screen.getByDisplayValue('old@test.example')).toBeInTheDocument()
    expect(screen.getByDisplayValue('1 Main St')).toBeInTheDocument()
  })

  it('saves edited values via PUT /branding and refetches context', async () => {
    const user = userEvent.setup()
    render(<AdminBrandingPage />)

    const contact = screen.getByDisplayValue('old@test.example')
    await user.clear(contact)
    await user.type(contact, 'new@test.example')

    await user.click(screen.getByRole('button', { name: /save changes/i }))

    await waitFor(() => expect(mockPut).toHaveBeenCalledTimes(1))
    const [url, payload] = mockPut.mock.calls[0]!
    expect(url).toBe('/branding')
    expect(payload.contact_email).toBe('new@test.example')
    expect(payload.library_name).toBe('Test Library')
    expect(mockRefetch).toHaveBeenCalledTimes(1)
    expect(mockToastSuccess).toHaveBeenCalledWith('Branding updated')
  })

  it('shows an error toast when PUT fails', async () => {
    mockPut.mockRejectedValueOnce(new Error('boom'))
    const user = userEvent.setup()
    render(<AdminBrandingPage />)

    await user.click(screen.getByRole('button', { name: /save changes/i }))

    await waitFor(() => expect(mockToastError).toHaveBeenCalledWith('boom'))
    expect(mockRefetch).not.toHaveBeenCalled()
  })

  it('saves hide_director_note when "Hide the section" is chosen', async () => {
    const user = userEvent.setup()
    render(<AdminBrandingPage />)

    await user.click(screen.getByRole('radio', { name: /hide the section/i }))
    await user.click(screen.getByRole('button', { name: /save changes/i }))

    await waitFor(() => expect(mockPut).toHaveBeenCalledTimes(1))
    const [, payload] = mockPut.mock.calls[0]!
    expect(payload.about_story).toEqual({ intro: [], timeline: [], hide_director_note: true })
  })

  it('saves a custom director note with paragraphs and signature', async () => {
    const user = userEvent.setup()
    render(<AdminBrandingPage />)

    await user.click(screen.getByRole('radio', { name: /write our own/i }))
    await user.type(screen.getByLabelText(/note text/i), 'First paragraph.\n\nSecond paragraph.')
    await user.type(screen.getByLabelText(/signature/i), 'Jane Doe, Director')
    await user.click(screen.getByRole('button', { name: /save changes/i }))

    await waitFor(() => expect(mockPut).toHaveBeenCalledTimes(1))
    const [, payload] = mockPut.mock.calls[0]!
    expect(payload.about_story.director_note).toEqual({
      paragraphs: ['First paragraph.', 'Second paragraph.'],
      signature: 'Jane Doe, Director',
    })
    expect(payload.about_story.hide_director_note).toBeUndefined()
  })
})

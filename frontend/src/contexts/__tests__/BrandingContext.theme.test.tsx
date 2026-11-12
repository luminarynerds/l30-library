/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Tests for BrandingContext's runtime full-palette + display-font theming
 * (Task 11). Verifies that a tenant's surface/secondary/display-font branding
 * fields translate into CSS custom properties on <html>, and that an unset
 * theme removes those properties so the hardcoded tailwind fallbacks apply.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, waitFor } from '@testing-library/react'
import { BrandingProvider, useBranding } from '../BrandingContext'

vi.mock('@/lib/api-client', () => ({
  fetchApi: vi.fn(),
}))

import { fetchApi } from '@/lib/api-client'
const mockFetchApi = fetchApi as unknown as ReturnType<typeof vi.fn>

function Consumer() {
  const branding = useBranding()
  return <div data-testid="library-name">{branding.library_name}</div>
}

describe('BrandingContext theming', () => {
  beforeEach(() => {
    mockFetchApi.mockReset()
    document.documentElement.style.removeProperty('--brand-surface-rgb')
    document.documentElement.style.removeProperty('--brand-secondary-rgb')
    document.documentElement.style.removeProperty('--brand-ink-rgb')
    document.documentElement.style.removeProperty('--display')
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('sets --brand-surface-rgb, --brand-secondary-rgb, and --display from branding fields', async () => {
    mockFetchApi.mockImplementation((url: string) => {
      if (url.startsWith('/branding/setup-status')) {
        return Promise.resolve({ setup_complete: true, has_admin: true })
      }
      return Promise.resolve({
        library_name: 'Orange Public Library',
        surface_color: '#F2ECDF',
        secondary_color: '#0F1F3D',
        ink_color: '#26221C',
        display_font: 'Cormorant Garamond',
      })
    })

    render(
      <BrandingProvider>
        <Consumer />
      </BrandingProvider>
    )

    await waitFor(() => {
      expect(document.documentElement.style.getPropertyValue('--brand-surface-rgb')).toBe('242 236 223')
    })
    expect(document.documentElement.style.getPropertyValue('--brand-secondary-rgb')).toBe('15 31 61')
    expect(document.documentElement.style.getPropertyValue('--display')).toBe(
      "'Cormorant Garamond', 'DM Serif Display', Georgia, serif"
    )
  })

  it('does not set theme vars when branding fields are unset (fallback stays live)', async () => {
    mockFetchApi.mockImplementation((url: string) => {
      if (url.startsWith('/branding/setup-status')) {
        return Promise.resolve({ setup_complete: true, has_admin: true })
      }
      return Promise.resolve({
        library_name: 'Library',
        surface_color: '',
        secondary_color: '',
        ink_color: '',
        display_font: '',
      })
    })

    render(
      <BrandingProvider>
        <Consumer />
      </BrandingProvider>
    )

    await waitFor(() => {
      expect(mockFetchApi).toHaveBeenCalled()
    })

    expect(document.documentElement.style.getPropertyValue('--brand-surface-rgb')).toBe('')
    expect(document.documentElement.style.getPropertyValue('--brand-secondary-rgb')).toBe('')
    expect(document.documentElement.style.getPropertyValue('--display')).toBe('')
  })
})
